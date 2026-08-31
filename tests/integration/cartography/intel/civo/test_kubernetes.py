from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.kubernetes
import cartography.intel.civo.sshkeys
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.kubernetes import KUBERNETES_CLUSTERS_PAGE
from tests.data.civo.kubernetes import TEST_CLUSTER_ID
from tests.data.civo.kubernetes import TEST_POOL_ID
from tests.data.civo.kubernetes import TEST_WORKER_INSTANCE_ID
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
    cartography.intel.civo.kubernetes,
    "get",
    return_value=KUBERNETES_CLUSTERS_PAGE["items"],
)
@patch.object(
    cartography.intel.civo.account,
    "get",
    return_value=QUOTA_RESPONSE,
)
def test_civo_kubernetes_graph(mock_account_get, mock_kubernetes_get, neo4j_session):
    """
    Sync only the Kubernetes domain and verify cluster, pool, and worker-node
    properties and secret exclusions. Cross-domain relationship resolution is
    covered by the final relationship layer with matching target nodes loaded.
    """
    # Arrange
    api_session = requests.Session()
    common_job_parameters = _common_job_parameters()
    account = cartography.intel.civo.account.sync(
        neo4j_session, api_session, common_job_parameters
    )
    common_job_parameters["ACCOUNT_ID"] = account["id"]

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

    # Assert: CivoKubernetesPool linked to its cluster.
    assert check_rels(
        neo4j_session,
        "CivoKubernetesCluster",
        "id",
        "CivoKubernetesPool",
        "id",
        "HAS_POOL",
    ) == {(TEST_CLUSTER_ID, TEST_POOL_ID)}

    # Assert: CivoKubernetesInstance (a worker node) loaded, linked to its
    # pool, with the ComputeInstance ontology label, its region inherited
    # from the parent cluster (worker-node objects carry none of their
    # own), and no worker-node secrets anywhere on it.
    assert check_nodes(
        neo4j_session,
        "CivoKubernetesInstance",
        ["id", "hostname", "_ont_state", "region", "_ont_region"],
    ) == {
        (TEST_WORKER_INSTANCE_ID, "prod-cluster-pool-abc-1", "running", "lon1", "lon1")
    }
    assert check_rels(
        neo4j_session,
        "CivoKubernetesPool",
        "id",
        "CivoKubernetesInstance",
        "id",
        "HAS_WORKER_INSTANCE",
    ) == {(TEST_POOL_ID, TEST_WORKER_INSTANCE_ID)}
    worker_props = neo4j_session.run(
        "MATCH (n:CivoKubernetesInstance {id: $id}) RETURN properties(n) AS props",
        id=TEST_WORKER_INSTANCE_ID,
    ).single()["props"]
    for secret_field in ("initial_password", "civostatsd_token", "ssh_key", "script"):
        assert secret_field not in worker_props
