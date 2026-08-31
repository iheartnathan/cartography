from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.ips
import cartography.intel.civo.loadbalancers
import cartography.intel.civo.sshkeys
from cartography.config import Config
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.ips import IPS_PAGE
from tests.data.civo.ips import TEST_IP_ID
from tests.data.civo.ips import TEST_LB_IP_ID
from tests.data.civo.loadbalancers import LOAD_BALANCERS_RESPONSE
from tests.data.civo.loadbalancers import TEST_INSTANCE_PRIVATE_IP
from tests.data.civo.loadbalancers import TEST_LOADBALANCER_ID
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
    cartography.intel.civo.ips,
    "get",
    return_value=IPS_PAGE["items"],
)
@patch.object(
    cartography.intel.civo.loadbalancers,
    "get",
    return_value=LOAD_BALANCERS_RESPONSE,
)
@patch.object(
    cartography.intel.civo.account,
    "get",
    return_value=QUOTA_RESPONSE,
)
def test_civo_loadbalancer_ip_graph(
    mock_account_get, mock_loadbalancers_get, mock_ips_get, neo4j_session
):
    """
    CivoLoadBalancer/CivoIP loaded standalone. firewall_id/cluster_id/
    network_id are kept as plain properties only in this PR, not wired as
    PROTECTED_BY/EXPOSES/PART_OF_NETWORK relationships (and
    CivoLoadBalancerBackend's ROUTES_TO / CivoIP's instance-typed
    ASSIGNED_TO aren't wired either) - CivoFirewall/CivoKubernetesCluster/
    CivoNetwork/CivoInstance are owned by the separate Networking/
    Kubernetes/Compute PRs and don't exist on this branch. Those edges are
    added in a follow-up cross-resource-relationships PR once every Civo
    resource PR has merged (see the PR split plan).
    """
    # Arrange
    api_session = requests.Session()
    common_job_parameters = _common_job_parameters()
    account = cartography.intel.civo.account.sync(
        neo4j_session, api_session, common_job_parameters
    )
    common_job_parameters["ACCOUNT_ID"] = account["id"]

    # Act
    cartography.intel.civo.loadbalancers.sync(
        neo4j_session, api_session, common_job_parameters
    )
    cartography.intel.civo.ips.sync(neo4j_session, api_session, common_job_parameters)

    # Assert: CivoLoadBalancerBackend loaded, linked to its CivoLoadBalancer.
    backend_id = f"{TEST_LOADBALANCER_ID}/{TEST_INSTANCE_PRIVATE_IP}/http/80/8080"
    assert check_nodes(neo4j_session, "CivoLoadBalancerBackend", ["id", "ip"]) == {
        (backend_id, TEST_INSTANCE_PRIVATE_IP)
    }
    assert check_rels(
        neo4j_session,
        "CivoLoadBalancer",
        "id",
        "CivoLoadBalancerBackend",
        "id",
        "HAS_BACKEND",
    ) == {(TEST_LOADBALANCER_ID, backend_id)}

    # Assert: CivoLoadBalancerInstancePool loaded with its own routing
    # config preserved (not combined across pools), linked to its load
    # balancer.
    pool_id = f"{TEST_LOADBALANCER_ID}/https/443"
    assert check_nodes(
        neo4j_session,
        "CivoLoadBalancerInstancePool",
        ["id", "protocol", "source_port", "health_check_path"],
    ) == {(pool_id, "https", 443, "/healthz")}
    assert check_rels(
        neo4j_session,
        "CivoLoadBalancer",
        "id",
        "CivoLoadBalancerInstancePool",
        "id",
        "HAS_INSTANCE_POOL",
    ) == {(TEST_LOADBALANCER_ID, pool_id)}

    # Assert: CivoLoadBalancer loaded, with the ontology's ip_address field
    # correctly populated from public_ip.
    assert check_nodes(
        neo4j_session, "CivoLoadBalancer", ["id", "name", "_ont_ip_address"]
    ) == {
        (TEST_LOADBALANCER_ID, "prod-lb", "74.220.16.20"),
    }

    # Assert: CivoIP loaded with assigned_to flattened.
    assert check_nodes(neo4j_session, "CivoIP", ["id", "ip", "assigned_to_type"]) == {
        (TEST_IP_ID, "74.220.16.30", "instance"),
        (TEST_LB_IP_ID, "74.220.16.40", "loadbalancer"),
    }

    # Assert: the loadbalancer-assigned IP resolves its typed ASSIGNED_TO
    # relationship (the instance-assigned IP can't - no CivoInstance node in
    # this PR).
    assert check_rels(
        neo4j_session, "CivoIP", "id", "CivoLoadBalancer", "id", "ASSIGNED_TO"
    ) == {(TEST_LB_IP_ID, TEST_LOADBALANCER_ID)}
    assert (
        check_rels(neo4j_session, "CivoIP", "id", "CivoInstance", "id", "ASSIGNED_TO")
        == set()
    )


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
    cartography.intel.civo.ips,
    "get",
    return_value=IPS_PAGE["items"],
)
@patch.object(
    cartography.intel.civo.loadbalancers,
    "get",
    return_value=LOAD_BALANCERS_RESPONSE,
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
def test_start_civo_ingestion_wires_loadbalancer_ip_resources(
    mock_account_get,
    mock_sshkeys_get,
    mock_loadbalancers_get,
    mock_ips_get,
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

    # Assert: this PR's resources loaded and linked to their account,
    # proving the entrypoint actually wires this PR's sync() calls.
    assert check_nodes(neo4j_session, "CivoLoadBalancer", ["id"]) == {
        (TEST_LOADBALANCER_ID,)
    }
    assert check_nodes(neo4j_session, "CivoIP", ["id"]) == {
        (TEST_IP_ID,),
        (TEST_LB_IP_ID,),
    }
    assert check_rels(
        neo4j_session, "CivoAccount", "id", "CivoLoadBalancer", "id", "RESOURCE"
    ) == {(TEST_ACCOUNT_ID, TEST_LOADBALANCER_ID)}

    # Cleanup: this test's nodes would otherwise persist in the shared
    # module-scoped test database and pollute other tests' exact-set
    # assertions.
    neo4j_session.run(
        "MATCH (n:CivoAccount) WHERE n.id = $id DETACH DELETE n", id=TEST_ACCOUNT_ID
    )
    neo4j_session.run(
        "MATCH (n) WHERE n:CivoLoadBalancer OR n:CivoLoadBalancerBackend OR n:CivoLoadBalancerInstancePool OR n:CivoIP DETACH DELETE n"
    )
