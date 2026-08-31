import pytest

import cartography.intel.civo.kubernetes
from tests.data.civo.kubernetes import KUBERNETES_CLUSTERS_PAGE
from tests.data.civo.kubernetes import TEST_CLUSTER_ID
from tests.data.civo.kubernetes import TEST_NODE_POOL_ID
from tests.data.civo.kubernetes import TEST_WORKER_NODE_ID


def test_transform_clusters_drops_kubeconfig_and_flattens_installed_apps() -> None:
    # Act
    clusters = cartography.intel.civo.kubernetes.transform_clusters(
        KUBERNETES_CLUSTERS_PAGE["items"]
    )

    # Assert: the real cluster-admin credential never reaches the transformed
    # row, and only actually-installed marketplace apps are kept, as names.
    row = clusters[0]
    assert row["id"] == TEST_CLUSTER_ID
    assert "kubeconfig" not in row
    assert row["installed_application_names"] == ["traefik"]
    assert row["version"] == "1.30.5-k3s1"


def test_transform_node_pools_links_to_cluster() -> None:
    # Act
    node_pools = cartography.intel.civo.kubernetes.transform_node_pools(
        KUBERNETES_CLUSTERS_PAGE["items"]
    )

    # Assert
    assert node_pools == [
        {
            "id": TEST_NODE_POOL_ID,
            "cluster_id": TEST_CLUSTER_ID,
            "count": 3,
            "size": "g4s.kube.medium",
            "instance_names": [
                "prod-cluster-pool-abc-1",
                "prod-cluster-pool-abc-2",
            ],
            "public_ip_node_pool": False,
        },
    ]


def test_transform_kubernetes_worker_nodes_drops_secrets_and_links_to_pool() -> None:
    # Act
    worker_nodes = cartography.intel.civo.kubernetes.transform_worker_nodes(
        KUBERNETES_CLUSTERS_PAGE["items"]
    )

    # Assert: worker nodes are full compute instances (previously discarded
    # entirely - only instance_names, bare strings, were kept), with the
    # same secret fields CivoInstance already excludes dropped here too.
    assert len(worker_nodes) == 1
    row = worker_nodes[0]
    assert row["id"] == TEST_WORKER_NODE_ID
    assert row["pool_id"] == TEST_NODE_POOL_ID
    assert row["hostname"] == "prod-cluster-pool-abc-1"
    assert row["private_ip"] == "192.168.1.20"
    for secret_field in ("initial_password", "civostatsd_token", "ssh_key", "script"):
        assert secret_field not in row


def test_transform_kubernetes_worker_nodes_inherits_cluster_region() -> None:
    # Worker-node objects carry no region field of their own (confirmed
    # live) - it must be inherited from the parent cluster instead.
    worker_nodes = cartography.intel.civo.kubernetes.transform_worker_nodes(
        KUBERNETES_CLUSTERS_PAGE["items"]
    )

    assert worker_nodes[0]["region"] == "lon1"


def test_transform_kubernetes_worker_nodes_rejects_empty_id() -> None:
    cluster = {
        **KUBERNETES_CLUSTERS_PAGE["items"][0],
        "pools": [
            {
                **KUBERNETES_CLUSTERS_PAGE["items"][0]["pools"][0],
                "instances": [
                    {
                        **KUBERNETES_CLUSTERS_PAGE["items"][0]["pools"][0]["instances"][
                            0
                        ],
                        "id": "",
                    }
                ],
            }
        ],
    }

    with pytest.raises(
        ValueError, match="missing required non-empty kubernetes worker node id"
    ):
        cartography.intel.civo.kubernetes.transform_worker_nodes([cluster])
