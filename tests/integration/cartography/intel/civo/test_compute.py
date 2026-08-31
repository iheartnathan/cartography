from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.instances
import cartography.intel.civo.sshkeys
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.instances import INSTANCES_RESPONSE
from tests.data.civo.instances import TEST_INSTANCE_ID
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
    cartography.intel.civo.instances,
    "get",
    return_value=INSTANCES_RESPONSE,
)
@patch.object(
    cartography.intel.civo.account,
    "get",
    return_value=QUOTA_RESPONSE,
)
def test_civo_instance_graph(mock_account_get, mock_instances_get, neo4j_session):
    """
    CivoInstance loaded standalone. network_id/firewall_id are kept as
    plain properties only in this PR, not wired as PART_OF_NETWORK/
    PROTECTED_BY relationships - CivoNetwork/CivoFirewall are owned by
    the separate Networking PR and don't exist on this branch. Those
    edges are added in a follow-up cross-resource-relationships PR once
    every Civo resource PR has merged (see the PR split plan).
    """
    # Arrange
    api_session = requests.Session()
    common_job_parameters = _common_job_parameters()

    # Act
    account = cartography.intel.civo.account.sync(
        neo4j_session, api_session, common_job_parameters
    )
    common_job_parameters["ACCOUNT_ID"] = account["id"]
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
