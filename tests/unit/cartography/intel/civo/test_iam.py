from unittest import mock

import pytest
import requests

import cartography.intel.civo.iam
from tests.data.civo.iam import PERMISSIONS_RESPONSE
from tests.data.civo.iam import ROLES_RESPONSE
from tests.data.civo.iam import TEAM_MEMBERS_RESPONSE
from tests.data.civo.iam import TEAMS_RESPONSE
from tests.data.civo.iam import TEST_CUSTOM_ROLE_ID
from tests.data.civo.iam import TEST_ROLE_ID
from tests.data.civo.iam import TEST_ROLE_OWNER_ACCOUNT_ID
from tests.data.civo.iam import TEST_TEAM_ID
from tests.data.civo.iam import TEST_TEAM_MEMBER_ID

TEST_ACCOUNT_ID_A = "test-account-a"
TEST_ACCOUNT_ID_B = "test-account-b"


def _make_response(payload):
    resp = mock.MagicMock(spec=requests.Response)
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_transform_teams() -> None:
    teams = cartography.intel.civo.iam.transform_teams(TEAMS_RESPONSE)

    assert teams == [
        {
            "id": TEST_TEAM_ID,
            "name": "Owners",
            "created_at": "2026-08-30T22:36:55Z",
        },
    ]


def test_transform_team_members_drops_api_key() -> None:
    # Act
    members = cartography.intel.civo.iam.transform_team_members(
        TEAM_MEMBERS_RESPONSE, TEST_ACCOUNT_ID_A
    )

    # Assert: the fixture's api_key (a fake sentinel value, shaped like
    # what was confirmed live on a real account before being scrubbed -
    # see tests/data/civo/iam.py) never reaches the transformed row.
    row = members[0]
    assert row["id"] == TEST_TEAM_MEMBER_ID
    assert row["team_id"] == TEST_TEAM_ID
    assert "api_key" not in row


def test_transform_team_members_splits_permission_codes_and_role_refs() -> None:
    # permission_codes/role_refs are <account_id>/<value> composite refs
    # now, not the bare code/id Civo returns - see transform_roles/
    # transform_permissions for why (avoids two accounts' identically-named
    # permissions/roles colliding onto one Neo4j node).
    members = cartography.intel.civo.iam.transform_team_members(
        TEAM_MEMBERS_RESPONSE, TEST_ACCOUNT_ID_A
    )

    row = members[0]
    assert row["permission_codes"] == [f"{TEST_ACCOUNT_ID_A}/*.*"]
    assert row["role_refs"] == [f"{TEST_ACCOUNT_ID_A}/{TEST_ROLE_ID}"]


def test_transform_team_members_empty_permissions_and_roles() -> None:
    member = {**TEAM_MEMBERS_RESPONSE[0], "permissions": "", "roles": ""}

    members = cartography.intel.civo.iam.transform_team_members(
        [member], TEST_ACCOUNT_ID_A
    )

    assert members[0]["permission_codes"] == []
    assert members[0]["role_refs"] == []


def test_transform_team_members_rejects_empty_id() -> None:
    member = {**TEAM_MEMBERS_RESPONSE[0], "id": ""}
    with pytest.raises(ValueError, match="missing required non-empty team member id"):
        cartography.intel.civo.iam.transform_team_members([member], TEST_ACCOUNT_ID_A)


def test_transform_roles_splits_permission_codes() -> None:
    # Act
    roles = cartography.intel.civo.iam.transform_roles(
        ROLES_RESPONSE, TEST_ACCOUNT_ID_A
    )

    # Assert: id is <account_id>/<role id>, not the bare role id - the real
    # id is kept separately as role_id.
    row = roles[0]
    assert row["id"] == f"{TEST_ACCOUNT_ID_A}/{TEST_ROLE_ID}"
    assert row["role_id"] == TEST_ROLE_ID
    assert row["permissions"] == "organisation.owner,billing.*,team.*"
    assert row["permission_codes"] == [
        f"{TEST_ACCOUNT_ID_A}/organisation.owner",
        f"{TEST_ACCOUNT_ID_A}/billing.*",
        f"{TEST_ACCOUNT_ID_A}/team.*",
    ]
    assert row["built_in"] is True
    assert row["role_type"] == "builtin"
    # A built-in role owns neither an account nor an organisation.
    assert row["owner_account_id"] is None
    assert row["owner_organisation_id"] is None


def test_transform_roles_same_role_different_accounts_get_different_ids() -> None:
    # Confirmed live that built-in role ids (e.g. "Super administrator")
    # are identical strings across every Civo account - the composite id
    # must still keep them as separate nodes per account.
    role = ROLES_RESPONSE[0]

    roles_a = cartography.intel.civo.iam.transform_roles([role], TEST_ACCOUNT_ID_A)
    roles_b = cartography.intel.civo.iam.transform_roles([role], TEST_ACCOUNT_ID_B)

    assert roles_a[0]["id"] != roles_b[0]["id"]
    assert roles_a[0]["role_id"] == roles_b[0]["role_id"] == TEST_ROLE_ID


def test_transform_roles_keeps_custom_role_owner_account_id() -> None:
    # Mirrors a real custom role created live via POST /v2/roles with
    # account_id set explicitly.
    role = next(r for r in ROLES_RESPONSE if r["id"] == TEST_CUSTOM_ROLE_ID)

    roles = cartography.intel.civo.iam.transform_roles([role], TEST_ACCOUNT_ID_A)

    assert roles[0]["owner_account_id"] == TEST_ROLE_OWNER_ACCOUNT_ID
    assert roles[0]["owner_organisation_id"] is None


def test_transform_roles_custom_role_type() -> None:
    role = {**ROLES_RESPONSE[0], "built_in": False}

    roles = cartography.intel.civo.iam.transform_roles([role], TEST_ACCOUNT_ID_A)

    assert roles[0]["role_type"] == "custom"


def test_transform_roles_rejects_empty_id() -> None:
    role = {**ROLES_RESPONSE[0], "id": ""}
    with pytest.raises(ValueError, match="missing required non-empty role id"):
        cartography.intel.civo.iam.transform_roles([role], TEST_ACCOUNT_ID_A)


def test_transform_permissions_includes_catalog_only() -> None:
    permissions = cartography.intel.civo.iam.transform_permissions(
        PERMISSIONS_RESPONSE, [], [], TEST_ACCOUNT_ID_A
    )

    assert permissions == [
        {
            "id": f"{TEST_ACCOUNT_ID_A}/*.*",
            "code": "*.*",
            "name": "Owner",
            "description": "Can perform any action",
        },
    ]


def test_transform_permissions_rejects_empty_code() -> None:
    permission = {**PERMISSIONS_RESPONSE[0], "code": ""}
    with pytest.raises(ValueError, match="missing required non-empty permission code"):
        cartography.intel.civo.iam.transform_permissions(
            [permission], [], [], TEST_ACCOUNT_ID_A
        )


def test_transform_permissions_derives_nodes_from_roles_and_members() -> None:
    # Act: PERMISSIONS_RESPONSE only has "*.*" - none of ROLES_RESPONSE's
    # entries ("organisation.owner", "billing.*", "team.*",
    # "billing.read", "team.read") are in the catalog at all, confirmed live.
    roles = cartography.intel.civo.iam.transform_roles(
        ROLES_RESPONSE, TEST_ACCOUNT_ID_A
    )
    members = cartography.intel.civo.iam.transform_team_members(
        TEAM_MEMBERS_RESPONSE, TEST_ACCOUNT_ID_A
    )

    permissions = cartography.intel.civo.iam.transform_permissions(
        PERMISSIONS_RESPONSE, roles, members, TEST_ACCOUNT_ID_A
    )

    by_code = {p["code"]: p for p in permissions}
    assert set(by_code) == {
        "*.*",
        "organisation.owner",
        "billing.*",
        "team.*",
        "billing.read",
        "team.read",
    }
    # Every id is scoped to the account, including derived entries.
    assert by_code["billing.*"]["id"] == f"{TEST_ACCOUNT_ID_A}/billing.*"
    # The catalog entry keeps its real name/description.
    assert by_code["*.*"]["name"] == "Owner"
    # Derived (non-catalog) entries have no name/description - Civo's API
    # doesn't describe them anywhere.
    assert by_code["billing.*"]["name"] is None
    assert by_code["billing.*"]["description"] is None


def test_transform_permissions_catalog_entry_not_overwritten_by_derived() -> None:
    # A role/member permission that happens to match a real catalog code
    # must keep the catalog's name/description, not a bare derived stub.
    role = {**ROLES_RESPONSE[0], "permissions": "*.*"}
    roles = cartography.intel.civo.iam.transform_roles([role], TEST_ACCOUNT_ID_A)

    permissions = cartography.intel.civo.iam.transform_permissions(
        PERMISSIONS_RESPONSE, roles, [], TEST_ACCOUNT_ID_A
    )

    assert permissions == [
        {
            "id": f"{TEST_ACCOUNT_ID_A}/*.*",
            "code": "*.*",
            "name": "Owner",
            "description": "Can perform any action",
        },
    ]


def test_transform_permissions_same_code_different_accounts_get_different_ids() -> None:
    # High-severity finding this addresses: two accounts observing the same
    # permission code (e.g. "billing.*") must not collide onto one Neo4j
    # node - one account's cleanup deleting that node would take out the
    # other account's relationships to it too.
    permissions_a = cartography.intel.civo.iam.transform_permissions(
        PERMISSIONS_RESPONSE, [], [], TEST_ACCOUNT_ID_A
    )
    permissions_b = cartography.intel.civo.iam.transform_permissions(
        PERMISSIONS_RESPONSE, [], [], TEST_ACCOUNT_ID_B
    )

    assert permissions_a[0]["id"] != permissions_b[0]["id"]
    assert permissions_a[0]["code"] == permissions_b[0]["code"] == "*.*"


def test_get_team_members_fans_out_per_team() -> None:
    # Team members are listed per-team (GET /v2/teams/{id}/members), not
    # globally - confirm get_team_members() queries each team's own path.
    session = mock.MagicMock(spec=requests.Session)
    session.get.side_effect = [_make_response(TEAM_MEMBERS_RESPONSE)]

    results = cartography.intel.civo.iam.get_team_members(
        session, "https://api.civo.com", TEAMS_RESPONSE
    )

    assert results == TEAM_MEMBERS_RESPONSE
    assert session.get.call_args.args[0] == (
        f"https://api.civo.com/v2/teams/{TEST_TEAM_ID}/members"
    )
