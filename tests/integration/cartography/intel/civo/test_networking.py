from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.firewalls
import cartography.intel.civo.networks
import cartography.intel.civo.sshkeys
from cartography.config import Config
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.firewalls import FIREWALL_RULES_RESPONSE
from tests.data.civo.firewalls import FIREWALLS_RESPONSE
from tests.data.civo.firewalls import TEST_FIREWALL_ID
from tests.data.civo.firewalls import TEST_FIREWALL_RULE_ID
from tests.data.civo.networks import NETWORKS_RESPONSE
from tests.data.civo.networks import SUBNETS_RESPONSE
from tests.data.civo.networks import TEST_NETWORK_ID
from tests.data.civo.networks import TEST_SUBNET_ID
from tests.integration.util import check_nodes
from tests.integration.util import check_rels

TEST_UPDATE_TAG = 123456789
TEST_BASE_URL = "https://api.fake-civo.com"
TEST_ACCOUNT_ID = QUOTA_RESPONSE["id"]
TEST_REGION_CODE = "lon1"

# firewalls.get()/networks.get() return (item, region_code) pairs, not a bare
# list, since the region a firewall/network came from is needed again to
# fetch its rules/subnets from that same region.
FIREWALLS_BY_REGION = [(f, TEST_REGION_CODE) for f in FIREWALLS_RESPONSE]
NETWORKS_BY_REGION = [(n, TEST_REGION_CODE) for n in NETWORKS_RESPONSE]


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
    cartography.intel.civo.firewalls,
    "get_rules",
    return_value=cartography.intel.civo.firewalls.transform_rules(
        FIREWALL_RULES_RESPONSE, TEST_FIREWALL_ID
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
        SUBNETS_RESPONSE, TEST_NETWORK_ID
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
def test_civo_network_firewall_graph(
    mock_account_get,
    mock_networks_get,
    mock_subnets_get,
    mock_firewalls_get,
    mock_rules_get,
    neo4j_session,
):
    # Arrange
    api_session = requests.Session()
    common_job_parameters = _common_job_parameters()

    # Act: same phase order as start_civo_ingestion - networks before
    # firewalls, since firewalls reference networks by id.
    account = cartography.intel.civo.account.sync(
        neo4j_session, api_session, common_job_parameters
    )
    common_job_parameters["ACCOUNT_ID"] = account["id"]
    cartography.intel.civo.networks.sync(
        neo4j_session, api_session, common_job_parameters
    )
    cartography.intel.civo.firewalls.sync(
        neo4j_session, api_session, common_job_parameters
    )

    # Assert: CivoNetwork + CivoSubnet, with ontology _ont_cidr populated.
    assert check_nodes(
        neo4j_session, "CivoNetwork", ["id", "label", "cidr", "_ont_cidr"]
    ) == {
        (TEST_NETWORK_ID, "production-vpc", "192.168.1.0/24", "192.168.1.0/24"),
    }
    assert check_rels(
        neo4j_session, "CivoNetwork", "id", "CivoSubnet", "id", "HAS_SUBNET"
    ) == {(TEST_NETWORK_ID, TEST_SUBNET_ID)}

    # Assert: CivoFirewall + CivoFirewallRule, correctly linked.
    assert check_nodes(neo4j_session, "CivoFirewall", ["id", "name"]) == {
        (TEST_FIREWALL_ID, "web-firewall"),
    }
    assert check_rels(
        neo4j_session, "CivoFirewall", "id", "CivoFirewallRule", "id", "HAS_RULE"
    ) == {(TEST_FIREWALL_ID, TEST_FIREWALL_RULE_ID)}
    assert check_rels(
        neo4j_session, "CivoFirewall", "id", "CivoNetwork", "id", "PART_OF_NETWORK"
    ) == {(TEST_FIREWALL_ID, TEST_NETWORK_ID)}


@patch.object(
    cartography.intel.civo,
    "get_regions",
    return_value=[
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
)
@patch.object(
    cartography.intel.civo.firewalls,
    "get_rules",
    return_value=cartography.intel.civo.firewalls.transform_rules(
        FIREWALL_RULES_RESPONSE, TEST_FIREWALL_ID
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
        SUBNETS_RESPONSE, TEST_NETWORK_ID
    ),
)
@patch.object(
    cartography.intel.civo.networks,
    "get",
    return_value=NETWORKS_BY_REGION,
)
@patch.object(
    cartography.intel.civo.sshkeys,
    "get",
    return_value=[],
)
@patch.object(
    cartography.intel.civo.account,
    "get",
    return_value=QUOTA_RESPONSE,
)
def test_start_civo_ingestion_wires_networking_resources(
    mock_account_get,
    mock_sshkeys_get,
    mock_networks_get,
    mock_subnets_get,
    mock_firewalls_get,
    mock_rules_get,
    mock_get_regions,
    neo4j_session,
):
    """
    Exercises the real entrypoint end-to-end for this PR's own resources,
    unlike the tests above which call each module's sync()/cleanup()
    directly. Catches wiring bugs a per-domain test can't: a missing
    entrypoint import, a forgotten sync() call, or a merge-conflict
    resolution that silently drops this PR's resources from __init__.py.
    """
    # Arrange
    config = Config(
        neo4j_uri="bolt://fake-neo4j:7687",
        update_tag=TEST_UPDATE_TAG,
        civo_api_key="fake-key",
        civo_base_url=TEST_BASE_URL,
    )

    # Act
    cartography.intel.civo.start_civo_ingestion(neo4j_session, config)

    # Assert: this PR's resources both loaded and linked to their account,
    # proving the entrypoint actually wires this PR's sync() calls.
    assert check_nodes(neo4j_session, "CivoNetwork", ["id"]) == {(TEST_NETWORK_ID,)}
    assert check_nodes(neo4j_session, "CivoFirewall", ["id"]) == {(TEST_FIREWALL_ID,)}
    assert check_rels(
        neo4j_session, "CivoAccount", "id", "CivoNetwork", "id", "RESOURCE"
    ) == {(TEST_ACCOUNT_ID, TEST_NETWORK_ID)}

    # Cleanup: this test's nodes would otherwise persist in the shared
    # module-scoped test database and pollute other tests' exact-set
    # assertions.
    neo4j_session.run(
        "MATCH (n:CivoAccount) WHERE n.id = $id DETACH DELETE n", id=TEST_ACCOUNT_ID
    )
    neo4j_session.run(
        "MATCH (n) WHERE n:CivoNetwork OR n:CivoSubnet OR n:CivoFirewall OR n:CivoFirewallRule DETACH DELETE n"
    )
