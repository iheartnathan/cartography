from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.firewalls
import cartography.intel.civo.instances
import cartography.intel.civo.networks
import cartography.intel.civo.sshkeys
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.firewalls import FIREWALL_RULES_RESPONSE
from tests.data.civo.firewalls import FIREWALLS_RESPONSE
from tests.data.civo.firewalls import TEST_FIREWALL_ID
from tests.data.civo.instances import INSTANCES_RESPONSE
from tests.data.civo.instances import TEST_INSTANCE_ID
from tests.data.civo.networks import NETWORKS_RESPONSE
from tests.data.civo.networks import SUBNETS_RESPONSE
from tests.data.civo.networks import TEST_NETWORK_ID
from tests.data.civo.sshkeys import SSH_KEYS_RESPONSE
from tests.integration.util import check_nodes
from tests.integration.util import check_rels

TEST_UPDATE_TAG = 123456789
TEST_BASE_URL = "https://api.fake-civo.com"
TEST_ACCOUNT_ID = QUOTA_RESPONSE["id"]
TEST_REGION_CODE = "lon1"
FIREWALLS_BY_REGION = [(firewall, TEST_REGION_CODE) for firewall in FIREWALLS_RESPONSE]
NETWORKS_BY_REGION = [(network, TEST_REGION_CODE) for network in NETWORKS_RESPONSE]


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
    cartography.intel.civo.sshkeys,
    "get",
    return_value=SSH_KEYS_RESPONSE,
)
@patch.object(
    cartography.intel.civo.instances,
    "get",
    return_value=INSTANCES_RESPONSE,
)
@patch.object(
    cartography.intel.civo.firewalls,
    "get_rules",
    return_value=cartography.intel.civo.firewalls.transform_rules(
        FIREWALL_RULES_RESPONSE,
        TEST_FIREWALL_ID,
    ),
)
@patch.object(
    cartography.intel.civo.firewalls,
    "get",
    return_value=FIREWALLS_BY_REGION,
)
@patch.object(
    cartography.intel.civo.networks,
    "get_subnets",
    return_value=cartography.intel.civo.networks.transform_subnets(
        SUBNETS_RESPONSE,
        TEST_NETWORK_ID,
    ),
)
@patch.object(
    cartography.intel.civo.networks,
    "get",
    return_value=NETWORKS_BY_REGION,
)
@patch.object(
    cartography.intel.civo.account,
    "get",
    return_value=QUOTA_RESPONSE,
)
def test_civo_instance_graph(
    mock_account_get,
    mock_networks_get,
    mock_subnets_get,
    mock_firewalls_get,
    mock_rules_get,
    mock_instances_get,
    mock_sshkeys_get,
    neo4j_session,
):
    """
    Verify instance properties and secret exclusions together with the
    network and firewall relationships owned by the Compute layer.
    """
    # Arrange
    api_session = requests.Session()
    common_job_parameters = _common_job_parameters()

    # Act
    account = cartography.intel.civo.account.sync(
        neo4j_session, api_session, common_job_parameters
    )
    common_job_parameters["ACCOUNT_ID"] = account["id"]
    cartography.intel.civo.sshkeys.sync(
        neo4j_session,
        api_session,
        common_job_parameters,
    )
    cartography.intel.civo.networks.sync(
        neo4j_session,
        api_session,
        common_job_parameters,
    )
    cartography.intel.civo.firewalls.sync(
        neo4j_session,
        api_session,
        common_job_parameters,
    )
    cartography.intel.civo.instances.sync(
        neo4j_session, api_session, common_job_parameters
    )

    # Assert: CivoInstance loaded with none of its secret fields, and with
    # the ontology _ont_state field populated.
    instance_props = check_nodes(
        neo4j_session,
        "CivoInstance",
        ["id", "hostname", "status", "_ont_state"],
    )
    assert instance_props == {
        (TEST_INSTANCE_ID, "web-1", "ACTIVE", "running"),
    }

    # Assert: no secret ever reached the graph - check every property on the
    # loaded CivoInstance node, not just the ones we expect.
    all_instance_props = neo4j_session.run(
        "MATCH (n:CivoInstance {id: $id}) RETURN properties(n) AS props",
        id=TEST_INSTANCE_ID,
    ).single()["props"]
    # Assert: image provenance is source_type/source_id, not template_id -
    # Civo's real instance responses don't carry template_id at all.
    assert all_instance_props["source_type"] == "diskimage"
    assert all_instance_props["source_id"] == "811a8dfb-8202-49ad-b1ef-1e6320b20497"
    assert "template_id" not in all_instance_props
    for secret_field in (
        "initial_password",
        "rescue_password",
        "civostatsd_token",
        "civostatsd_stats",
        "script",
        "ssh_key",
    ):
        assert secret_field not in all_instance_props

    assert check_rels(
        neo4j_session,
        "CivoInstance",
        "id",
        "CivoNetwork",
        "id",
        "PART_OF_NETWORK",
    ) == {(TEST_INSTANCE_ID, TEST_NETWORK_ID)}
    assert check_rels(
        neo4j_session,
        "CivoInstance",
        "id",
        "CivoFirewall",
        "id",
        "PROTECTED_BY",
    ) == {(TEST_INSTANCE_ID, TEST_FIREWALL_ID)}
    assert check_rels(
        neo4j_session,
        "CivoInstance",
        "id",
        "CivoSSHKey",
        "id",
        "HAS_SSH_KEY",
    ) == {(TEST_INSTANCE_ID, INSTANCES_RESPONSE[0]["ssh_key_id"])}


def test_civo_instance_cleanup_is_account_scoped(neo4j_session):
    account_id = "compute-cleanup-account"
    other_account_id = "compute-cleanup-other-account"
    stale_instance_id = "compute-cleanup-stale-instance"
    other_instance_id = "compute-cleanup-other-instance"

    # Arrange: both accounts have an instance left by a previous complete
    # sync. The second account deliberately remains on the old update tag.
    cartography.intel.civo.account.load_accounts(
        neo4j_session,
        [{"id": account_id}, {"id": other_account_id}],
        TEST_UPDATE_TAG,
    )
    cartography.intel.civo.instances.load_instances(
        neo4j_session,
        [{"id": stale_instance_id}],
        account_id,
        TEST_UPDATE_TAG,
    )
    cartography.intel.civo.instances.load_instances(
        neo4j_session,
        [{"id": other_instance_id}],
        other_account_id,
        TEST_UPDATE_TAG,
    )

    # Act: a later complete sync for only the first account no longer observes
    # its instance, so its account-scoped cleanup should remove that node.
    cartography.intel.civo.instances.cleanup(
        neo4j_session,
        {"ACCOUNT_ID": account_id, "UPDATE_TAG": TEST_UPDATE_TAG + 1},
    )

    # Assert: the active account's stale instance is gone; another account's
    # equally stale instance is outside this cleanup scope and survives.
    remaining_ids = {
        record["id"]
        for record in neo4j_session.run(
            "MATCH (instance:CivoInstance) WHERE instance.id IN $ids "
            "RETURN instance.id AS id",
            ids=[stale_instance_id, other_instance_id],
        )
    }
    assert stale_instance_id not in remaining_ids
    assert other_instance_id in remaining_ids

    # Avoid leaking the deliberately retained account and instance into other
    # tests that share this integration database.
    neo4j_session.run(
        "MATCH (instance:CivoInstance {id: $id}) DETACH DELETE instance",
        id=other_instance_id,
    )
    neo4j_session.run(
        "MATCH (account:CivoAccount) WHERE account.id IN $ids DETACH DELETE account",
        ids=[account_id, other_account_id],
    )
