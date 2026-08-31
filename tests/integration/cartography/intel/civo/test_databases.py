from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.databases
import cartography.intel.civo.firewalls
import cartography.intel.civo.networks
import cartography.intel.civo.sshkeys
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.databases import DATABASES_PAGE
from tests.data.civo.databases import TEST_DATABASE_ID
from tests.data.civo.firewalls import FIREWALL_RULES_RESPONSE
from tests.data.civo.firewalls import FIREWALLS_RESPONSE
from tests.data.civo.firewalls import TEST_FIREWALL_ID
from tests.data.civo.networks import NETWORKS_RESPONSE
from tests.data.civo.networks import SUBNETS_RESPONSE
from tests.data.civo.networks import TEST_NETWORK_ID
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
    cartography.intel.civo.databases,
    "get",
    return_value=DATABASES_PAGE["items"],
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
def test_civo_database_no_password_reaches_graph(
    mock_account_get,
    mock_networks_get,
    mock_subnets_get,
    mock_firewalls_get,
    mock_rules_get,
    mock_databases_get,
    neo4j_session,
):
    """
    Verify database properties and password exclusions together with the
    network and firewall relationships owned by the Databases layer.
    """
    # Arrange
    api_session = requests.Session()
    common_job_parameters = _common_job_parameters()
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

    # Act
    cartography.intel.civo.databases.sync(
        neo4j_session, api_session, common_job_parameters
    )

    # Assert: CivoDatabase loaded with the ontology fields mapped.
    assert check_nodes(
        neo4j_session, "CivoDatabase", ["id", "name", "username", "_ont_type"]
    ) == {(TEST_DATABASE_ID, "prod-db", "civo", "PostgreSQL")}
    assert check_rels(
        neo4j_session,
        "CivoDatabase",
        "id",
        "CivoNetwork",
        "id",
        "PART_OF_NETWORK",
    ) == {(TEST_DATABASE_ID, TEST_NETWORK_ID)}
    assert check_rels(
        neo4j_session,
        "CivoDatabase",
        "id",
        "CivoFirewall",
        "id",
        "PROTECTED_BY",
    ) == {(TEST_DATABASE_ID, TEST_FIREWALL_ID)}

    # Assert: no password ever reached the graph - check every property on
    # the loaded node, not just the ones we expect.
    db_props = neo4j_session.run(
        "MATCH (n:CivoDatabase {id: $id}) RETURN properties(n) AS props",
        id=TEST_DATABASE_ID,
    ).single()["props"]
    assert "password" not in db_props
    assert "database_user_info" not in db_props
