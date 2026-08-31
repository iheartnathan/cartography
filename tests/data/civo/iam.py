from typing import Any

TEST_TEAM_ID = "70c998c0-697b-4e39-8dca-9cf4eb8fd53b"
TEST_TEAM_MEMBER_ID = "9e9e2e16-5a27-4f70-b31c-6a1cd176c4f3"
TEST_ROLE_ID = "35b3f5ee-6fdd-46b3-9e29-caa3d2e2b111"
TEST_CUSTOM_ROLE_ID = "699b8ec2-bc9a-4188-9a48-1450c615608e"
TEST_USER_ID = "eb08afb9-60fa-459a-a664-0563a29b3a58"
TEST_ROLE_OWNER_ACCOUNT_ID = "ba425368-a44e-49ce-8e18-acf50753a805"

TEAMS_RESPONSE: list[dict[str, Any]] = [
    {
        "id": TEST_TEAM_ID,
        "name": "Owners",
        "account_id": "ba425368-a44e-49ce-8e18-acf50753a805",
        "created_at": "2026-08-30T22:36:55Z",
        "updated_at": "2026-08-30T22:36:55Z",
    },
]

# Real (live-confirmed) response shape: includes the member's live API key
# in plaintext (scrubbed to a fake sentinel below) - must never reach the
# graph. The real account's member had an empty `roles` - populated here
# with TEST_ROLE_ID to exercise HAS_ASSIGNED_ROLE, matching a real
# assignment made and read back live (a throwaway team + member created
# and deleted for that check confirmed `roles` holds role IDs, not
# names).
TEAM_MEMBERS_RESPONSE: list[dict[str, Any]] = [
    {
        "id": TEST_TEAM_MEMBER_ID,
        "permissions": "*.*",
        "roles": TEST_ROLE_ID,
        "api_key": "FAKE00000000000000000000000000000000000000000",
        "team_id": TEST_TEAM_ID,
        "user_id": TEST_USER_ID,
        "created_at": "2026-08-30T22:36:55Z",
        "updated_at": "2026-08-30T22:36:55Z",
    },
]

# Second entry (TEST_CUSTOM_ROLE_ID) mirrors a real custom role created and
# deleted live via POST /v2/roles with account_id set explicitly - confirms
# a custom role can be genuinely account-owned (organisation_id empty,
# account_id populated), unlike the built-in above (both empty).
ROLES_RESPONSE: list[dict[str, Any]] = [
    {
        "id": TEST_ROLE_ID,
        "name": "Company administrator",
        "permissions": "organisation.owner,billing.*,team.*",
        "organisation_id": "",
        "account_id": "",
        "built_in": True,
        "created_at": "2021-11-09T16:07:01Z",
        "updated_at": "2021-11-09T16:07:01Z",
    },
    {
        "id": TEST_CUSTOM_ROLE_ID,
        "name": "cartography-livetest-role",
        "permissions": "billing.read,team.read",
        "organisation_id": "",
        "account_id": TEST_ROLE_OWNER_ACCOUNT_ID,
        "built_in": False,
        "created_at": "2026-08-31T10:44:18Z",
        "updated_at": "2026-08-31T10:44:18Z",
    },
]

PERMISSIONS_RESPONSE: list[dict[str, Any]] = [
    {
        "code": "*.*",
        "name": "Owner",
        "description": "Can perform any action",
    },
]
