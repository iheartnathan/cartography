from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.dns
import cartography.intel.civo.sshkeys
from cartography.config import Config
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.dns import DNS_DOMAINS_RESPONSE
from tests.data.civo.dns import DNS_RECORDS_RESPONSE
from tests.data.civo.dns import TEST_DOMAIN_ID
from tests.data.civo.dns import TEST_RECORD_ID
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
    cartography.intel.civo.dns,
    "get_records",
    return_value=cartography.intel.civo.dns.transform_records(
        DNS_RECORDS_RESPONSE, TEST_DOMAIN_ID
    ),
)
@patch.object(
    cartography.intel.civo.dns,
    "get",
    return_value=DNS_DOMAINS_RESPONSE,
)
@patch.object(
    cartography.intel.civo.account,
    "get",
    return_value=QUOTA_RESPONSE,
)
def test_civo_dns_graph(
    mock_account_get, mock_domains_get, mock_records_get, neo4j_session
):
    # Arrange
    api_session = requests.Session()
    common_job_parameters = _common_job_parameters()
    account = cartography.intel.civo.account.sync(
        neo4j_session, api_session, common_job_parameters
    )
    common_job_parameters["ACCOUNT_ID"] = account["id"]

    # Act
    cartography.intel.civo.dns.sync(neo4j_session, api_session, common_job_parameters)

    # Assert: CivoDNSDomain + CivoDNSRecord, correctly linked.
    assert check_nodes(neo4j_session, "CivoDNSDomain", ["id", "name"]) == {
        (TEST_DOMAIN_ID, "example.com"),
    }
    assert check_nodes(
        neo4j_session, "CivoDNSRecord", ["id", "name", "type", "value"]
    ) == {(TEST_RECORD_ID, "www", "a", "74.220.16.10")}
    assert check_rels(
        neo4j_session, "CivoDNSDomain", "id", "CivoDNSRecord", "id", "HAS_RECORD"
    ) == {(TEST_DOMAIN_ID, TEST_RECORD_ID)}


@patch.object(
    cartography.intel.civo.dns,
    "get_records",
    return_value=cartography.intel.civo.dns.transform_records(
        DNS_RECORDS_RESPONSE, TEST_DOMAIN_ID
    ),
)
@patch.object(
    cartography.intel.civo.dns,
    "get",
    return_value=DNS_DOMAINS_RESPONSE,
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
def test_start_civo_ingestion_wires_dns_resources(
    mock_account_get,
    mock_sshkeys_get,
    mock_domains_get,
    mock_records_get,
    neo4j_session,
):
    """
    Exercises the real entrypoint end-to-end for this PR's own resources,
    unlike the test above which calls each module's sync()/cleanup()
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

    # Assert: this PR's resources loaded and linked to their account,
    # proving the entrypoint actually wires this PR's sync() call.
    assert check_nodes(neo4j_session, "CivoDNSDomain", ["id"]) == {(TEST_DOMAIN_ID,)}
    assert check_rels(
        neo4j_session, "CivoAccount", "id", "CivoDNSDomain", "id", "RESOURCE"
    ) == {(TEST_ACCOUNT_ID, TEST_DOMAIN_ID)}

    # Cleanup: this test's nodes would otherwise persist in the shared
    # module-scoped test database and pollute other tests' exact-set
    # assertions.
    neo4j_session.run(
        "MATCH (n:CivoAccount) WHERE n.id = $id DETACH DELETE n", id=TEST_ACCOUNT_ID
    )
    neo4j_session.run(
        "MATCH (n) WHERE n:CivoDNSDomain OR n:CivoDNSRecord DETACH DELETE n"
    )
