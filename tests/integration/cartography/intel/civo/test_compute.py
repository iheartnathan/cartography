from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.instances
import cartography.intel.civo.sshkeys
from cartography.config import Config
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.instances import INSTANCES_RESPONSE
from tests.data.civo.instances import TEST_INSTANCE_ID
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
    cartography.intel.civo.instances,
    "get",
    return_value=INSTANCES_RESPONSE,
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
def test_start_civo_ingestion_wires_compute_resources(
    mock_account_get,
    mock_sshkeys_get,
    mock_instances_get,
    mock_get_regions,
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

    # Assert: this PR's resource loaded and linked to its account, proving
    # the entrypoint actually wires this PR's sync() call.
    assert check_nodes(neo4j_session, "CivoInstance", ["id"]) == {(TEST_INSTANCE_ID,)}
    assert check_rels(
        neo4j_session, "CivoAccount", "id", "CivoInstance", "id", "RESOURCE"
    ) == {(TEST_ACCOUNT_ID, TEST_INSTANCE_ID)}

    # Cleanup: this test's nodes would otherwise persist in the shared
    # module-scoped test database and pollute other tests' exact-set
    # assertions.
    neo4j_session.run(
        "MATCH (n:CivoAccount) WHERE n.id = $id DETACH DELETE n", id=TEST_ACCOUNT_ID
    )
    neo4j_session.run("MATCH (n:CivoInstance) DETACH DELETE n")
