from typing import Any

TEST_NETWORK_ID = "8d5c4e10-8b3a-4e6a-9b2e-1c2f3a4b5c6d"
TEST_FIREWALL_ID = "f1e2d3c4-b5a6-4978-8899-001122334455"
TEST_INSTANCE_PRIVATE_IP = "192.168.1.10"
TEST_CLUSTER_ID = "c1c2c3c4-d5d6-e7e8-f9f0-a1a2a3a4a5a6"
TEST_LOADBALANCER_ID = "1a2b3c4d-5e6f-7890-abcd-ef1234567890"
TEST_LOADBALANCER_REGION = "lon1"

LOAD_BALANCERS_RESPONSE: list[dict[str, Any]] = [
    {
        "id": TEST_LOADBALANCER_ID,
        "name": "prod-lb",
        "region": TEST_LOADBALANCER_REGION,
        "algorithm": "round_robin",
        "network_id": TEST_NETWORK_ID,
        "public_ip": "74.220.16.20",
        "private_ip": "192.168.1.20",
        "state": "active",
        "firewall_id": TEST_FIREWALL_ID,
        "cluster_id": TEST_CLUSTER_ID,
        "external_traffic_policy": "Cluster",
        "backends": [
            {
                "ip": TEST_INSTANCE_PRIVATE_IP,
                "protocol": "http",
                "source_port": 80,
                "target_port": 8080,
                "health_check_port": 8080,
            },
        ],
        "instance_pools": [
            {
                "tags": ["web"],
                "names": ["web-1"],
                "protocol": "https",
                "source_port": 443,
                "target_port": 8443,
                "health_check": {"port": 8443, "path": "/healthz"},
            },
        ],
    },
]
