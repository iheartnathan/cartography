from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.firewalls
import cartography.intel.civo.kubernetes
import cartography.intel.civo.networks
import cartography.intel.civo.sshkeys
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.firewalls import FIREWALL_RULES_RESPONSE
from tests.data.civo.firewalls import FIREWALLS_RESPONSE
from tests.data.civo.firewalls import TEST_FIREWALL_ID
from tests.data.civo.kubernetes import KUBERNETES_CLUSTERS_PAGE
from tests.data.civo.kubernetes import TEST_CLUSTER_ID
from tests.data.civo.kubernetes import TEST_NODE_POOL_ID
from tests.data.civo.kubernetes import TEST_WORKER_NODE_ID
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
    cartography.intel.civo.kubernetes,
    "get",
    return_value=KUBERNETES_CLUSTERS_PAGE["items"],
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
def test_civo_kubernetes_graph(
    mock_account_get,
    mock_networks_get,
    mock_subnets_get,
    mock_firewalls_get,
    mock_rules_get,
    mock_kubernetes_get,
    neo4j_session,
):
    """
    Verify Kubernetes properties and secret exclusions together with the
    network and firewall relationships owned by the Kubernetes layer.
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
    cartography.intel.civo.kubernetes.sync(
        neo4j_session, api_session, common_job_parameters
    )

    # Assert: CivoKubernetesCluster loaded, with the cluster ontology label
    # and status mapped, and no kubeconfig anywhere on the node.
    assert check_nodes(
        neo4j_session, "CivoKubernetesCluster", ["id", "name", "_ont_status"]
    ) == {(TEST_CLUSTER_ID, "prod-cluster", "creating")}
    cluster_props = neo4j_session.run(
        "MATCH (n:CivoKubernetesCluster {id: $id}) RETURN properties(n) AS props",
        id=TEST_CLUSTER_ID,
    ).single()["props"]
    assert "kubeconfig" not in cluster_props
    assert check_rels(
        neo4j_session,
        "CivoKubernetesCluster",
        "id",
        "CivoNetwork",
        "id",
        "PART_OF_NETWORK",
    ) == {(TEST_CLUSTER_ID, TEST_NETWORK_ID)}
    assert check_rels(
        neo4j_session,
        "CivoKubernetesCluster",
        "id",
        "CivoFirewall",
        "id",
        "PROTECTED_BY",
    ) == {(TEST_CLUSTER_ID, TEST_FIREWALL_ID)}

    # Assert: CivoKubernetesNodePool linked to its cluster.
    assert check_rels(
        neo4j_session,
        "CivoKubernetesCluster",
        "id",
        "CivoKubernetesNodePool",
        "id",
        "HAS_NODE_POOL",
    ) == {(TEST_CLUSTER_ID, TEST_NODE_POOL_ID)}

    # Assert: CivoKubernetesWorkerNode (a worker node) loaded, linked to its
    # pool, with the ComputeInstance ontology label, its region inherited
    # from the parent cluster (worker-node objects carry none of their
    # own), and no worker-node secrets anywhere on it.
    assert check_nodes(
        neo4j_session,
        "CivoKubernetesWorkerNode",
        ["id", "hostname", "_ont_state", "region", "_ont_region"],
    ) == {(TEST_WORKER_NODE_ID, "prod-cluster-pool-abc-1", "running", "lon1", "lon1")}
    assert check_rels(
        neo4j_session,
        "CivoKubernetesNodePool",
        "id",
        "CivoKubernetesWorkerNode",
        "id",
        "HAS_WORKER_NODE",
    ) == {(TEST_NODE_POOL_ID, TEST_WORKER_NODE_ID)}
    assert check_rels(
        neo4j_session,
        "CivoKubernetesWorkerNode",
        "id",
        "CivoNetwork",
        "id",
        "PART_OF_NETWORK",
    ) == {(TEST_WORKER_NODE_ID, TEST_NETWORK_ID)}
    assert check_rels(
        neo4j_session,
        "CivoKubernetesWorkerNode",
        "id",
        "CivoFirewall",
        "id",
        "PROTECTED_BY",
    ) == {(TEST_WORKER_NODE_ID, TEST_FIREWALL_ID)}
    worker_props = neo4j_session.run(
        "MATCH (n:CivoKubernetesWorkerNode {id: $id}) RETURN properties(n) AS props",
        id=TEST_WORKER_NODE_ID,
    ).single()["props"]
    for secret_field in ("initial_password", "civostatsd_token", "ssh_key", "script"):
        assert secret_field not in worker_props
