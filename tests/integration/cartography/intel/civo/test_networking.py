from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.firewalls
import cartography.intel.civo.networks
import cartography.intel.civo.sshkeys
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


def test_civo_networking_cleanup_is_account_scoped(neo4j_session):
    account_id = "networking-cleanup-account"
    other_account_id = "networking-cleanup-other-account"
    stale_network_id = "networking-cleanup-stale-network"
    stale_subnet_id = "networking-cleanup-stale-subnet"
    stale_firewall_id = "networking-cleanup-stale-firewall"
    stale_rule_id = "networking-cleanup-stale-rule"
    other_network_id = "networking-cleanup-other-network"
    other_subnet_id = "networking-cleanup-other-subnet"
    other_firewall_id = "networking-cleanup-other-firewall"
    other_rule_id = "networking-cleanup-other-rule"

    # Arrange: each account owns a complete network/firewall hierarchy from a
    # previous sync. Only the first account is refreshed below.
    cartography.intel.civo.account.load_accounts(
        neo4j_session,
        [{"id": account_id}, {"id": other_account_id}],
        TEST_UPDATE_TAG,
    )
    for scoped_account_id, network_id, subnet_id, firewall_id, rule_id in (
        (
            account_id,
            stale_network_id,
            stale_subnet_id,
            stale_firewall_id,
            stale_rule_id,
        ),
        (
            other_account_id,
            other_network_id,
            other_subnet_id,
            other_firewall_id,
            other_rule_id,
        ),
    ):
        cartography.intel.civo.networks.load_networks(
            neo4j_session,
            [{"id": network_id}],
            scoped_account_id,
            TEST_UPDATE_TAG,
        )
        cartography.intel.civo.networks.load_subnets(
            neo4j_session,
            [{"id": subnet_id, "network_id": network_id}],
            scoped_account_id,
            TEST_UPDATE_TAG,
        )
        cartography.intel.civo.firewalls.load_firewalls(
            neo4j_session,
            [{"id": firewall_id, "network_id": network_id}],
            scoped_account_id,
            TEST_UPDATE_TAG,
        )
        cartography.intel.civo.firewalls.load_rules(
            neo4j_session,
            [{"id": rule_id, "firewall_id": firewall_id}],
            scoped_account_id,
            TEST_UPDATE_TAG,
        )

    # Act: a later complete sync for the first account observes none of its
    # old resources. Cleanup must not cross the RESOURCE ownership boundary.
    cleanup_parameters = {
        "ACCOUNT_ID": account_id,
        "UPDATE_TAG": TEST_UPDATE_TAG + 1,
    }
    cartography.intel.civo.firewalls.cleanup(neo4j_session, cleanup_parameters)
    cartography.intel.civo.networks.cleanup(neo4j_session, cleanup_parameters)

    # Assert: all four stale node types were removed for the active account,
    # while the other account's equally stale hierarchy remains intact.
    for removed_id, retained_id in (
        (stale_network_id, other_network_id),
        (stale_subnet_id, other_subnet_id),
        (stale_firewall_id, other_firewall_id),
        (stale_rule_id, other_rule_id),
    ):
        ids = {
            record["id"]
            for record in neo4j_session.run(
                "MATCH (n) WHERE n.id IN $ids RETURN n.id AS id",
                ids=[removed_id, retained_id],
            )
        }
        assert removed_id not in ids
        assert retained_id in ids

    # Avoid leaving the deliberately retained account hierarchy in the shared
    # integration database used by subsequent tests.
    neo4j_session.run(
        """
        MATCH (account:CivoAccount {id: $account_id})-[:RESOURCE]->(resource)
        DETACH DELETE resource
        """,
        account_id=other_account_id,
    )
    neo4j_session.run(
        "MATCH (account:CivoAccount) WHERE account.id IN $ids DETACH DELETE account",
        ids=[account_id, other_account_id],
    )
