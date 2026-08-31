from typing import Any

TEST_NETWORK_ID = "8d5c4e10-8b3a-4e6a-9b2e-1c2f3a4b5c6d"
TEST_SUBNET_ID = "12345678-90ab-cdef-1234-567890abcdef"

NETWORKS_RESPONSE: list[dict[str, Any]] = [
    {
        "id": TEST_NETWORK_ID,
        "name": "default",
        "label": "production-vpc",
        "default": True,
        "status": "available",
        "cidr": "192.168.1.0/24",
        "cidr_v6": "",
        "ipv4_enabled": True,
        "ipv6_enabled": False,
        "vlan_id": 0,
    },
]

SUBNETS_RESPONSE: list[dict[str, Any]] = [
    {
        "id": TEST_SUBNET_ID,
        "name": "default-subnet",
        "network_id": TEST_NETWORK_ID,
        "subnet_size": "/24",
        "status": "available",
    },
]
