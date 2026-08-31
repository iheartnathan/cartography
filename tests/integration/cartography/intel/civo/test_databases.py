from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.databases
import cartography.intel.civo.sshkeys
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.databases import DATABASES_PAGE
from tests.data.civo.databases import TEST_DATABASE_ID
from tests.integration.util import check_nodes

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
    cartography.intel.civo.databases,
    "get",
    return_value=DATABASES_PAGE["items"],
)
@patch.object(
    cartography.intel.civo.account,
    "get",
    return_value=QUOTA_RESPONSE,
)
def test_civo_database_no_password_reaches_graph(
    mock_account_get, mock_databases_get, neo4j_session
):
    """
    Sync only CivoDatabase and verify its properties and password exclusions.
    Cross-domain relationship resolution is covered by the final relationship
    layer with matching target nodes loaded.
    """
    # Arrange
    api_session = requests.Session()
    common_job_parameters = _common_job_parameters()
    account = cartography.intel.civo.account.sync(
        neo4j_session, api_session, common_job_parameters
    )
    common_job_parameters["ACCOUNT_ID"] = account["id"]

    # Act
    cartography.intel.civo.databases.sync(
        neo4j_session, api_session, common_job_parameters
    )

    # Assert: CivoDatabase loaded with the ontology fields mapped.
    assert check_nodes(
        neo4j_session, "CivoDatabase", ["id", "name", "username", "_ont_type"]
    ) == {(TEST_DATABASE_ID, "prod-db", "civo", "PostgreSQL")}

    # Assert: no password ever reached the graph - check every property on
    # the loaded node, not just the ones we expect.
    db_props = neo4j_session.run(
        "MATCH (n:CivoDatabase {id: $id}) RETURN properties(n) AS props",
        id=TEST_DATABASE_ID,
    ).single()["props"]
    assert "password" not in db_props
    assert "database_user_info" not in db_props
