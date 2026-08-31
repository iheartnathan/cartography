from typing import Any

from tests.data.civo.networks import TEST_NETWORK_ID

TEST_FIREWALL_ID = "f1e2d3c4-b5a6-4978-8899-001122334455"
TEST_FIREWALL_RULE_ID = "aabbccdd-1122-3344-5566-778899aabbcc"

FIREWALLS_RESPONSE: list[dict[str, Any]] = [
    {
        "id": TEST_FIREWALL_ID,
        "name": "web-firewall",
        "network_id": TEST_NETWORK_ID,
        "rules_count": 1,
        "instance_count": 1,
        "cluster_count": 0,
        "loadbalancer_count": 0,
    },
]

FIREWALL_RULES_RESPONSE: list[dict[str, Any]] = [
    {
        "id": TEST_FIREWALL_RULE_ID,
        "firewall_id": TEST_FIREWALL_ID,
        "protocol": "tcp",
        "start_port": "443",
        "end_port": "443",
        "cidr": ["0.0.0.0/0"],
        "direction": "ingress",
        "action": "allow",
        "label": "https",
    },
]
