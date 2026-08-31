from unittest.mock import patch

import requests

import cartography.intel.civo.account
import cartography.intel.civo.sshkeys
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.sshkeys import SSH_KEYS_RESPONSE
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
        # Only one region in tests: every regional get() is mocked directly
        # (get()/get_stores()/etc.), so the fan-out helpers themselves aren't
        # exercised here - see test_civo.py (unit) for that. One entry, with
        # every feature flag on, is enough to prove the region-scoped call
        # chain is wired correctly regardless of which feature a module
        # filters on.
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
    cartography.intel.civo.sshkeys,
    "get",
    return_value=SSH_KEYS_RESPONSE,
)
@patch.object(
    cartography.intel.civo.account,
    "get",
    return_value=QUOTA_RESPONSE,
)
def test_civo_account_and_sshkeys_sync(
    mock_account_get, mock_sshkeys_get, neo4j_session
):
    # Arrange
    api_session = requests.Session()
    common_job_parameters = _common_job_parameters()

    # Act: sync the account (tenant) first, then the account-scoped ssh keys,
    # mirroring cartography.intel.civo.start_civo_ingestion's phase order.
    account = cartography.intel.civo.account.sync(
        neo4j_session,
        api_session,
        common_job_parameters,
    )
    common_job_parameters["ACCOUNT_ID"] = account["id"]
    cartography.intel.civo.sshkeys.sync(
        neo4j_session,
        api_session,
        common_job_parameters,
    )

    # Assert: CivoAccount loaded correctly.
    assert check_nodes(
        neo4j_session,
        "CivoAccount",
        ["id", "default_user_id", "default_user_email_address"],
    ) == {
        (
            QUOTA_RESPONSE["id"],
            QUOTA_RESPONSE["default_user_id"],
            QUOTA_RESPONSE["default_user_email_address"],
        ),
    }

    # Assert: all SSH keys across both pages loaded, with fingerprints intact.
    assert check_nodes(
        neo4j_session,
        "CivoSSHKey",
        ["id", "name", "fingerprint"],
    ) == {(key["id"], key["name"], key["fingerprint"]) for key in SSH_KEYS_RESPONSE}

    # Assert: every SSH key is scoped to the account.
    assert check_rels(
        neo4j_session,
        "CivoSSHKey",
        "id",
        "CivoAccount",
        "id",
        "RESOURCE",
        rel_direction_right=False,
    ) == {(key["id"], TEST_ACCOUNT_ID) for key in SSH_KEYS_RESPONSE}


@patch.object(
    cartography.intel.civo.sshkeys,
    "get",
)
@patch.object(
    cartography.intel.civo.account,
    "get",
    return_value=QUOTA_RESPONSE,
)
def test_civo_sshkey_cleanup_removes_stale_keys(
    mock_account_get, mock_sshkeys_get, neo4j_session
):
    # Arrange: one full sync with two keys.
    api_session = requests.Session()
    common_job_parameters = _common_job_parameters()
    mock_sshkeys_get.return_value = SSH_KEYS_RESPONSE
    account = cartography.intel.civo.account.sync(
        neo4j_session,
        api_session,
        common_job_parameters,
    )
    common_job_parameters["ACCOUNT_ID"] = account["id"]
    cartography.intel.civo.sshkeys.sync(
        neo4j_session,
        api_session,
        common_job_parameters,
    )
    # sync() no longer runs cleanup() itself (see start_civo_ingestion's
    # Phase 3 comment) - the real entrypoint runs it once at the very end,
    # so tests that want to exercise it call it explicitly.
    cartography.intel.civo.sshkeys.cleanup(neo4j_session, common_job_parameters)

    # Act: re-sync with one key removed upstream, under a new update tag.
    mock_sshkeys_get.return_value = SSH_KEYS_RESPONSE[:1]
    common_job_parameters["UPDATE_TAG"] = TEST_UPDATE_TAG + 1
    cartography.intel.civo.sshkeys.sync(
        neo4j_session,
        api_session,
        common_job_parameters,
    )
    cartography.intel.civo.sshkeys.cleanup(neo4j_session, common_job_parameters)

    # Assert: only the still-present key remains.
    assert check_nodes(neo4j_session, "CivoSSHKey", ["id"]) == {
        (SSH_KEYS_RESPONSE[0]["id"],),
    }
