from typing import Any

TEST_NETWORK_ID = "8d5c4e10-8b3a-4e6a-9b2e-1c2f3a4b5c6d"
TEST_FIREWALL_ID = "f1e2d3c4-b5a6-4978-8899-001122334455"
TEST_CLUSTER_ID = "c1c2c3c4-d5d6-e7e8-f9f0-a1a2a3a4a5a6"
TEST_POOL_ID = "p1p2p3p4-q5q6-r7r8-s9s0-t1t2t3t4t5t6"
TEST_WORKER_INSTANCE_ID = "w1w2w3w4-x5x6-y7y8-z9z0-a1b2c3d4e5f6"

KUBERNETES_CLUSTERS_PAGE: dict[str, Any] = {
    "page": 1,
    "per_page": 20,
    "pages": 1,
    "items": [
        {
            "id": TEST_CLUSTER_ID,
            "name": "prod-cluster",
            "region": "lon1",
            "status": "BUILDING",
            "ready": True,
            "cluster_type": "k3s",
            "kubernetes_version": "1.30.5-k3s1",
            "version": "1.30.5-k3s1",
            "num_target_nodes": 3,
            "target_nodes_size": "g4s.kube.medium",
            "api_endpoint": "https://1.2.3.4:6443",
            # Real credential returned by Civo's API - must never reach the graph.
            "kubeconfig": "apiVersion: v1\nkind: Config\nusers:\n- name: default\n  user:\n    token: super-secret-cluster-token\n",
            "master_ip": "1.2.3.4",
            "dns_entry": "prod-cluster.k8s.civo.com",
            "network_id": TEST_NETWORK_ID,
            "firewall_id": TEST_FIREWALL_ID,
            "namespace": "prod-cluster-abc123",
            "tags": ["prod"],
            "cni_plugin": "flannel",
            "ccm_installed": "true",
            "volume_type": "ssd",
            "created_at": "2026-01-10T08:00:00Z",
            "pools": [
                {
                    "id": TEST_POOL_ID,
                    "count": 3,
                    "size": "g4s.kube.medium",
                    "instance_names": [
                        "prod-cluster-pool-abc-1",
                        "prod-cluster-pool-abc-2",
                    ],
                    "public_ip_node_pool": False,
                    "instances": [
                        {
                            "id": TEST_WORKER_INSTANCE_ID,
                            "hostname": "prod-cluster-pool-abc-1",
                            "size": "g4s.kube.medium",
                            "firewall_id": TEST_FIREWALL_ID,
                            "source_type": "diskimage",
                            "source_id": "1.30.5-k3s1",
                            "network_id": TEST_NETWORK_ID,
                            "initial_user": "root",
                            # Real credentials returned by Civo's API - must
                            # never reach the graph.
                            "initial_password": "S3cretWorkerPassw0rd!",
                            "ssh_key": "-",
                            "civostatsd_token": "worker-statsd-secret-token",
                            "script": "",
                            "tags": ["k3s"],
                            "status": "ACTIVE",
                            "public_ip": "5.6.7.8",
                            "private_ip": "192.168.1.20",
                            "reverse_dns": "",
                            "cpu_cores": 2,
                            "ram_mb": 4096,
                            "disk_gb": 40,
                            "created_at": "2026-01-10T08:05:00Z",
                        },
                    ],
                },
            ],
            "instances": [],
            "installed_applications": [
                {"application": "Traefik", "name": "traefik", "installed": True},
                {"application": "Longhorn", "name": "longhorn", "installed": False},
            ],
        },
    ],
}
