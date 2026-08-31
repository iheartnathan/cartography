import logging
from typing import Any

import neo4j
import requests

from cartography.client.core.tx import load
from cartography.graph.job import GraphJob
from cartography.intel.civo.util import get_json_array
from cartography.intel.civo.util import require_non_empty
from cartography.models.civo.iam import CivoPermissionSchema
from cartography.models.civo.iam import CivoRoleSchema
from cartography.models.civo.iam import CivoTeamMemberSchema
from cartography.models.civo.iam import CivoTeamSchema
from cartography.util import timeit

logger = logging.getLogger(__name__)


@timeit
def sync(
    neo4j_session: neo4j.Session,
    api_session: requests.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    account_id = common_job_parameters["ACCOUNT_ID"]
    base_url = common_job_parameters["BASE_URL"]
    teams = get_teams(api_session, base_url)
    transformed_teams = transform_teams(teams)
    members = get_team_members(api_session, base_url, teams)
    transformed_members = transform_team_members(members, account_id)
    roles = get_roles(api_session, base_url)
    transformed_roles = transform_roles(roles, account_id)
    permissions = get_permissions(api_session, base_url)
    # GET /v2/permissions is a small, mostly-wildcard-free catalog (e.g. just
    # "*.*", confirmed live) - most real role/member permission entries are
    # patterns like "billing.*" that never appear in it, so GRANTS/
    # HAS_PERMISSION would resolve for almost nothing if CivoPermission only
    # ever held catalog entries. Derive a node for every distinct pattern
    # actually observed on a role or member too, so every GRANTS/
    # HAS_PERMISSION edge has something real to resolve against.
    transformed_permissions = transform_permissions(
        permissions, transformed_roles, transformed_members, account_id
    )

    # Order matters: permissions and roles must exist before team members
    # load, since CivoTeamMemberToPermissionRel/CivoTeamMemberToRoleRel
    # matchers only resolve once their targets are already in the graph.
    load_permissions(
        neo4j_session,
        transformed_permissions,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )
    load_teams(
        neo4j_session,
        transformed_teams,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )
    load_roles(
        neo4j_session,
        transformed_roles,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )
    load_team_members(
        neo4j_session,
        transformed_members,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )


@timeit
def get_teams(api_session: requests.Session, base_url: str) -> list[dict[str, Any]]:
    return get_json_array(api_session, f"{base_url}/v2/teams")


@timeit
def get_team_members(
    api_session: requests.Session,
    base_url: str,
    teams: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Team members are listed per-team (GET /v2/teams/{id}/members), not
    globally.
    """
    all_members: list[dict[str, Any]] = []
    for team in teams:
        team_id = team.get("id")
        if not team_id:
            continue
        all_members.extend(
            get_json_array(api_session, f"{base_url}/v2/teams/{team_id}/members")
        )
    return all_members


@timeit
def get_roles(api_session: requests.Session, base_url: str) -> list[dict[str, Any]]:
    return get_json_array(api_session, f"{base_url}/v2/roles")


@timeit
def get_permissions(
    api_session: requests.Session, base_url: str
) -> list[dict[str, Any]]:
    return get_json_array(api_session, f"{base_url}/v2/permissions")


def transform_teams(teams: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for team in teams:
        team_id = require_non_empty(team.get("id"), "team id")
        result.append(
            {
                "id": team_id,
                "name": team.get("name"),
                "created_at": team.get("created_at"),
            }
        )
    return result


def transform_team_members(
    members: list[dict[str, Any]], account_id: str
) -> list[dict[str, Any]]:
    """
    Drops api_key before any row is built - GET /v2/teams/{id}/members
    returns each member's live API key in plaintext (confirmed against a
    real account); it must never reach the transformed row.

    `role_refs`/`permission_codes` are `<account_id>/<value>` composite
    refs, not the bare role id / permission code Civo returns - see
    `transform_roles`/`transform_permissions` for why: `CivoRole` and
    `CivoPermission` are both identified by a composite id scoped to the
    account that observed them, to avoid two different accounts' data
    colliding onto the same node (confirmed live that Civo's built-in
    roles, and permission codes like `billing.*`, are literally identical
    strings across every account).

    Confirmed live (assigned a real role to a test member and read the
    response back) that `roles` holds role IDs, not names.
    """
    result = []
    for member in members:
        member_id = require_non_empty(member.get("id"), "team member id")
        permissions = member.get("permissions") or ""
        roles = member.get("roles") or ""
        result.append(
            {
                "id": member_id,
                "team_id": member.get("team_id"),
                "user_id": member.get("user_id"),
                "permissions": permissions,
                "permission_codes": [
                    f"{account_id}/{code}" for code in permissions.split(",") if code
                ],
                "roles": roles,
                "role_refs": [f"{account_id}/{ref}" for ref in roles.split(",") if ref],
                "created_at": member.get("created_at"),
            }
        )
    return result


def transform_roles(
    roles: list[dict[str, Any]], account_id: str
) -> list[dict[str, Any]]:
    """
    `id` is `<account_id>/<role id>`, not the bare role id Civo assigns -
    confirmed live that built-in roles (e.g. "Super administrator") return
    the exact same id across every account, so a bare id would merge two
    different accounts' roles onto one Neo4j node. If account A's sync
    later considers that shared node stale, its scoped cleanup query
    (`MATCH (n)<-[:RESOURCE]-(:CivoAccount{id: A}) WHERE stale DETACH
    DELETE n`) deletes the node - and every relationship account B still
    holds to it - outright; it has no way to know B still needs it. The
    composite id sidesteps this entirely: each account gets its own node,
    so one account's cleanup can never delete a node another account owns.
    The real, bare role id is kept as its own `role_id` property.

    Also keeps `organisation_id`/`account_id` from the raw response
    (renamed `owner_*` to avoid colliding with this node's own
    `account_id`, which is the tenant this row was fetched under, not
    necessarily the role's real owner) - confirmed live via `POST
    /v2/roles` that a custom role can be owned by either, and civogo
    documents roles as being "for use within an organisation".
    """
    result = []
    for role in roles:
        role_id = require_non_empty(role.get("id"), "role id")
        permissions = role.get("permissions") or ""
        built_in = role.get("built_in")
        result.append(
            {
                "id": f"{account_id}/{role_id}",
                "role_id": role_id,
                "name": role.get("name"),
                "permissions": permissions,
                "built_in": built_in,
                # A string twin of built_in, purely for the ontology's
                # `type` field (builtin/custom) - Cypher's "mapping" special
                # handling compares against string literals, which never
                # matches a real Neo4j boolean property.
                "role_type": "builtin" if built_in else "custom",
                "permission_codes": [
                    f"{account_id}/{code}" for code in permissions.split(",") if code
                ],
                "owner_account_id": role.get("account_id") or None,
                "owner_organisation_id": role.get("organisation_id") or None,
                "created_at": role.get("created_at"),
            }
        )
    return result


def transform_permissions(
    permissions: list[dict[str, Any]],
    transformed_roles: list[dict[str, Any]],
    transformed_members: list[dict[str, Any]],
    account_id: str,
) -> list[dict[str, Any]]:
    """
    Builds one CivoPermission row per distinct code/pattern observed on
    this account, combining GET /v2/permissions' catalog (which has real
    name/description) with every pattern actually referenced by one of
    this account's roles or members (which doesn't - most are wildcards
    like "billing.*" that the catalog doesn't enumerate at all). Catalog
    entries are collected first so a pattern that happens to appear in
    both keeps its real name/description rather than being overwritten by
    a bare derived entry.

    `id` is `<account_id>/<code>`, not the bare code - see `transform_roles`
    for why (identical reasoning: confirmed live that permission codes are
    literally the same string across every account, so a bare-code id
    would let one account's cleanup delete a node another account still
    references). The bare code is kept as its own `code` property.
    `transformed_roles`/`transformed_members` are expected to already
    carry composite (`<account_id>/<code>`) refs in `permission_codes`
    (see `transform_roles`/`transform_team_members`), matching the ids
    built here.
    """
    by_code: dict[str, dict[str, Any]] = {}
    for permission in permissions:
        code = require_non_empty(permission.get("code"), "permission code")
        by_code[code] = {
            "id": f"{account_id}/{code}",
            "code": code,
            "name": permission.get("name"),
            "description": permission.get("description"),
        }
    prefix = f"{account_id}/"
    for role in transformed_roles:
        for ref in role.get("permission_codes") or []:
            code = ref[len(prefix) :] if ref.startswith(prefix) else ref
            by_code.setdefault(
                code,
                {
                    "id": f"{account_id}/{code}",
                    "code": code,
                    "name": None,
                    "description": None,
                },
            )
    for member in transformed_members:
        for ref in member.get("permission_codes") or []:
            code = ref[len(prefix) :] if ref.startswith(prefix) else ref
            by_code.setdefault(
                code,
                {
                    "id": f"{account_id}/{code}",
                    "code": code,
                    "name": None,
                    "description": None,
                },
            )
    return list(by_code.values())


@timeit
def load_teams(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoTeamSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def load_team_members(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoTeamMemberSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def load_roles(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoRoleSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def load_permissions(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoPermissionSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def cleanup(
    neo4j_session: neo4j.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    # Team members reference both permissions and roles, so clean up first -
    # same "child before parent" ordering as everywhere else in this module.
    GraphJob.from_node_schema(CivoTeamMemberSchema(), common_job_parameters).run(
        neo4j_session,
    )
    GraphJob.from_node_schema(CivoTeamSchema(), common_job_parameters).run(
        neo4j_session,
    )
    GraphJob.from_node_schema(CivoRoleSchema(), common_job_parameters).run(
        neo4j_session,
    )
    GraphJob.from_node_schema(CivoPermissionSchema(), common_job_parameters).run(
        neo4j_session,
    )
