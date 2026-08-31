from unittest.mock import patch

import requests

import cartography.intel.civo.account
import cartography.intel.civo.iam
from cartography.graph.job import GraphJob
from cartography.models.civo.iam import CivoPermissionSchema
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.iam import PERMISSIONS_RESPONSE
from tests.data.civo.iam import ROLES_RESPONSE
from tests.data.civo.iam import TEAM_MEMBERS_RESPONSE
from tests.data.civo.iam import TEAMS_RESPONSE
from tests.data.civo.iam import TEST_CUSTOM_ROLE_ID
from tests.data.civo.iam import TEST_ROLE_ID
from tests.data.civo.iam import TEST_ROLE_OWNER_ACCOUNT_ID
from tests.data.civo.iam import TEST_TEAM_ID
from tests.data.civo.iam import TEST_TEAM_MEMBER_ID
from tests.integration.util import check_nodes
from tests.integration.util import check_rels

TEST_UPDATE_TAG = 123456789
TEST_BASE_URL = "https://api.fake-civo.com"
TEST_ACCOUNT_ID = QUOTA_RESPONSE["id"]
TEST_REGION_CODE = "lon1"


def _common_job_parameters() -> dict:
    return {
        "UPDATE_TAG": TEST_UPDATE_TAG,
        "BASE_URL": TEST_BASE_URL,
        "REGIONS": [
            {
                "code": TEST_REGION_CODE,
                "features": {
                    "iaas": True,
                    "kubernetes": True,
                    "object_store": True,
                    "loadbalancer": True,
                    "gpu": True,
                    "dbaas": True,
                    "volume": True,
                    "paas": True,
                    "public_ip_node_pools": True,
                },
            },
        ],
    }


@patch.object(
    cartography.intel.civo.iam,
    "get_permissions",
    return_value=PERMISSIONS_RESPONSE,
)
@patch.object(
    cartography.intel.civo.iam,
    "get_roles",
    return_value=ROLES_RESPONSE,
)
@patch.object(
    cartography.intel.civo.iam,
    "get_team_members",
    return_value=TEAM_MEMBERS_RESPONSE,
)
@patch.object(
    cartography.intel.civo.iam,
    "get_teams",
    return_value=TEAMS_RESPONSE,
)
@patch.object(
    cartography.intel.civo.account,
    "get",
    return_value=QUOTA_RESPONSE,
)
def test_civo_iam_sync(
    mock_account_get,
    mock_teams_get,
    mock_members_get,
    mock_roles_get,
    mock_permissions_get,
    neo4j_session,
):
    """
    Civo IAM resources (teams/members/roles/permissions) - not ingested at
    all previously, and GET /v2/teams/{id}/members returns each member's
    live API key in plaintext (confirmed against a real account), so this
    also proves that never reaches the graph.
    """
    # Arrange
    api_session = requests.Session()
    common_job_parameters = _common_job_parameters()
    account = cartography.intel.civo.account.sync(
        neo4j_session, api_session, common_job_parameters
    )
    common_job_parameters["ACCOUNT_ID"] = account["id"]

    # Act
    cartography.intel.civo.iam.sync(neo4j_session, api_session, common_job_parameters)

    # Assert: CivoTeam + CivoTeamMember, correctly linked, with the ontology
    # UserGroup label populated.
    assert check_nodes(neo4j_session, "CivoTeam", ["id", "name", "_ont_name"]) == {
        (TEST_TEAM_ID, "Owners", "Owners")
    }
    assert check_rels(
        neo4j_session, "CivoTeam", "id", "CivoTeamMember", "id", "HAS_MEMBER"
    ) == {(TEST_TEAM_ID, TEST_TEAM_MEMBER_ID)}
    member_props = neo4j_session.run(
        "MATCH (n:CivoTeamMember {id: $id}) RETURN properties(n) AS props",
        id=TEST_TEAM_MEMBER_ID,
    ).single()["props"]
    assert "api_key" not in member_props
    assert member_props["permissions"] == "*.*"

    # Assert: CivoRole loaded with the ontology PermissionRole label
    # populated - the built-in role owns neither an account nor an
    # organisation, the custom one is account-owned (mirrors a real role
    # created live via POST /v2/roles) - and CivoPermission loaded both as
    # a global catalog entry ("*.*", with a real name) and as derived,
    # pattern-only entries for every pattern ROLES_RESPONSE references that
    # the tiny live catalog doesn't enumerate at all. Both node ids are
    # <account_id>/<real id> composites, not the bare Civo id (see
    # test_civo_iam_two_accounts_do_not_collide_on_cleanup for why).
    role_id_a = f"{TEST_ACCOUNT_ID}/{TEST_ROLE_ID}"
    custom_role_id_a = f"{TEST_ACCOUNT_ID}/{TEST_CUSTOM_ROLE_ID}"
    assert check_nodes(
        neo4j_session,
        "CivoRole",
        [
            "id",
            "role_id",
            "name",
            "_ont_type",
            "owner_account_id",
            "owner_organisation_id",
        ],
    ) == {
        (role_id_a, TEST_ROLE_ID, "Company administrator", "builtin", None, None),
        (
            custom_role_id_a,
            TEST_CUSTOM_ROLE_ID,
            "cartography-livetest-role",
            "custom",
            TEST_ROLE_OWNER_ACCOUNT_ID,
            None,
        ),
    }

    def _perm_id(code: str) -> str:
        return f"{TEST_ACCOUNT_ID}/{code}"

    assert check_nodes(neo4j_session, "CivoPermission", ["id", "code", "name"]) == {
        (_perm_id("*.*"), "*.*", "Owner"),
        (_perm_id("organisation.owner"), "organisation.owner", None),
        (_perm_id("billing.*"), "billing.*", None),
        (_perm_id("team.*"), "team.*", None),
        (_perm_id("billing.read"), "billing.read", None),
        (_perm_id("team.read"), "team.read", None),
    }
    # CivoPermission is account-scoped (RESOURCE from CivoAccount) so
    # derived entries actually get cleaned up when their owning role/member
    # is gone - not left as permanent orphans.
    assert check_rels(
        neo4j_session, "CivoAccount", "id", "CivoPermission", "id", "RESOURCE"
    ) == {
        (TEST_ACCOUNT_ID, _perm_id(code))
        for code in (
            "*.*",
            "organisation.owner",
            "billing.*",
            "team.*",
            "billing.read",
            "team.read",
        )
    }

    # Assert: GRANTS resolves for every one of both roles' permission
    # entries now, including the wildcards - not just the one that happens
    # to be in the small live catalog.
    assert check_rels(
        neo4j_session, "CivoRole", "id", "CivoPermission", "id", "GRANTS"
    ) == {
        (role_id_a, _perm_id("organisation.owner")),
        (role_id_a, _perm_id("billing.*")),
        (role_id_a, _perm_id("team.*")),
        (custom_role_id_a, _perm_id("billing.read")),
        (custom_role_id_a, _perm_id("team.read")),
    }

    # Assert: the member's direct permission resolves to
    # HAS_DIRECT_PERMISSION, and its role_refs resolves to HAS_ASSIGNED_ROLE
    # by id (TEAM_MEMBERS_RESPONSE sets roles=TEST_ROLE_ID) - confirmed live
    # (a real role assignment, read back) that `roles` holds role IDs, not
    # names. Named HAS_ASSIGNED_ROLE/HAS_DIRECT_PERMISSION, not the more
    # common HAS_ROLE/HAS_PERMISSION, since CivoTeamMember isn't a
    # UserAccount.
    assert check_rels(
        neo4j_session,
        "CivoTeamMember",
        "id",
        "CivoPermission",
        "id",
        "HAS_DIRECT_PERMISSION",
    ) == {(TEST_TEAM_MEMBER_ID, _perm_id("*.*"))}
    assert check_rels(
        neo4j_session, "CivoTeamMember", "id", "CivoRole", "id", "HAS_ASSIGNED_ROLE"
    ) == {(TEST_TEAM_MEMBER_ID, role_id_a)}


def test_civo_iam_two_accounts_do_not_collide_on_cleanup(neo4j_session):
    """
    High-severity regression test (see CivoPermissionSchema): two different
    Civo accounts that both observe the same permission code ("*.*") must
    not collide onto one Neo4j node. Before the composite id fix, account
    A's cleanup - considering "*.*" stale once A no longer references it -
    would DETACH DELETE the single shared node outright, destroying
    account B's still-valid relationship to it too.
    """
    account_a = "test-two-account-cleanup-a"
    account_b = "test-two-account-cleanup-b"
    update_tag = TEST_UPDATE_TAG

    # Arrange: a real CivoAccount node for each (RESOURCE's target matcher
    # needs one to resolve against), then both accounts load the same
    # catalog entry.
    cartography.intel.civo.account.load_accounts(
        neo4j_session, [{"id": account_a}, {"id": account_b}], update_tag
    )
    permissions_a = cartography.intel.civo.iam.transform_permissions(
        PERMISSIONS_RESPONSE, [], [], account_a
    )
    permissions_b = cartography.intel.civo.iam.transform_permissions(
        PERMISSIONS_RESPONSE, [], [], account_b
    )
    cartography.intel.civo.iam.load_permissions(
        neo4j_session, permissions_a, account_a, update_tag
    )
    cartography.intel.civo.iam.load_permissions(
        neo4j_session, permissions_b, account_b, update_tag
    )

    # Assert: each account has its own node for the same code. Uses `>=`
    # (superset), not `==`: other tests in this module-scoped session leave
    # their own CivoPermission nodes behind (their cleanup was never run),
    # so the live set legitimately contains more than just this test's two.
    assert check_nodes(neo4j_session, "CivoPermission", ["id", "code"]) >= {
        (f"{account_a}/*.*", "*.*"),
        (f"{account_b}/*.*", "*.*"),
    }

    # Act: account A's next sync no longer observes "*.*" at all, and only
    # account A's cleanup runs (mirrors start_civo_ingestion's Phase 3,
    # scoped to whichever account is currently syncing).
    cartography.intel.civo.iam.load_permissions(
        neo4j_session, [], account_a, update_tag + 1
    )
    GraphJob.from_node_schema(
        CivoPermissionSchema(), {"UPDATE_TAG": update_tag + 1, "ACCOUNT_ID": account_a}
    ).run(neo4j_session)

    # Assert: account A's node is gone, but account B's separate node -
    # same code, different composite id - survives completely untouched
    # (and no other test's nodes were touched by A's scoped cleanup).
    remaining = check_nodes(neo4j_session, "CivoPermission", ["id", "code"])
    assert (f"{account_a}/*.*", "*.*") not in remaining
    assert (f"{account_b}/*.*", "*.*") in remaining

    # Cleanup: neither throwaway account (nor account B's surviving
    # CivoPermission node - DETACH DELETE on CivoAccount only removes the
    # RESOURCE edge, not the node it pointed to) has a counterpart in any
    # other test's fixtures (CivoAccount's own cleanup is a no-op - see
    # start_civo_ingestion's Phase 3 comment), so they'd otherwise persist
    # in the shared test database and pollute later tests' exact-set node
    # assertions (e.g. test_start_civo_ingestion's CivoAccount/CivoPermission
    # checks).
    neo4j_session.run(
        "MATCH (n:CivoAccount) WHERE n.id IN $ids DETACH DELETE n",
        ids=[account_a, account_b],
    )
    neo4j_session.run(
        "MATCH (n:CivoPermission) WHERE n.id IN $ids DETACH DELETE n",
        ids=[f"{account_a}/*.*", f"{account_b}/*.*"],
    )
