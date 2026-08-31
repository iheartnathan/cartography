from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.dns
import cartography.intel.civo.sshkeys
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
    assert check_nodes(
        neo4j_session, "CivoDNSDomain", ["id", "name", "_ont_public"]
    ) == {
        (TEST_DOMAIN_ID, "example.com", True),
    }
    assert check_nodes(
        neo4j_session, "CivoDNSRecord", ["id", "name", "type", "value"]
    ) == {(TEST_RECORD_ID, "www", "a", "74.220.16.10")}
    assert check_rels(
        neo4j_session, "CivoDNSDomain", "id", "CivoDNSRecord", "id", "HAS_RECORD"
    ) == {(TEST_DOMAIN_ID, TEST_RECORD_ID)}
