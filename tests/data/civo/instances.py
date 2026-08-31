from typing import Any

TEST_INSTANCE_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
TEST_NETWORK_ID = "8d5c4e10-8b3a-4e6a-9b2e-1c2f3a4b5c6d"
TEST_FIREWALL_ID = "f1e2d3c4-b5a6-4978-8899-001122334455"
TEST_SSH_KEY_ID = "d2e0d160-2b93-4c86-ba0f-a09973bc7ce9"
TEST_INSTANCE_PRIVATE_IP = "192.168.1.10"

INSTANCES_RESPONSE: list[dict[str, Any]] = [
    {
        "id": TEST_INSTANCE_ID,
        "hostname": "web-1",
        "size": "g4s.kube.small",
        "region": "lon1",
        "network_id": TEST_NETWORK_ID,
        "private_ip": TEST_INSTANCE_PRIVATE_IP,
        "public_ip": "74.220.16.10",
        "ipv6": "",
        "pseudo_ip": "10.0.0.5",
        "source_type": "diskimage",
        "source_id": "811a8dfb-8202-49ad-b1ef-1e6320b20497",
        "initial_user": "civo",
        # Real credentials returned by Civo's API - must never reach the graph.
        "initial_password": "S3cretInitialPassw0rd!",
        "ssh_key": "ssh-rsa AAAAB3NzaC1yc2EA...",
        "ssh_key_id": TEST_SSH_KEY_ID,
        "status": "ACTIVE",
        "notes": "",
        "firewall_id": TEST_FIREWALL_ID,
        "tags": ["web", "production"],
        "civostatsd_token": "statsd-secret-token-abc123",
        "civostatsd_stats": "",
        "rescue_password": "R3scueP@ssw0rd!",
        "script": "#!/bin/bash\nexport API_TOKEN=super-secret-token\n",
        "volume_backed": False,
        "cpu_cores": 1,
        "ram_mb": 2048,
        "disk_gb": 25,
        "gpu_count": 0,
        "gpu_type": "",
        "created_at": "2026-01-15T10:30:00Z",
        "reserved_ip_id": "",
        "allowed_ips": ["203.0.113.0/24"],
    },
]

TEST_DECOY_INSTANCE_ID = "de1c0e5f-1234-4562-b3fc-2c963f66decoy"
TEST_DECOY_NETWORK_ID = "de1c0e5f-network-4e6a-9b2e-decoynetwork"
TEST_DECOY_ACCOUNT_INSTANCE_ID = "acc0decoy-4562-b3fc-2c963f66acc0"
TEST_DECOY_ACCOUNT_ID = "acc0decoy-account-4e6a-9b2e-decoyaccount"

# Same private_ip as INSTANCES_RESPONSE[0], but a different network - used to
# prove CivoLoadBalancerBackendToInstanceRel's ROUTES_TO match is actually
# scoped by network_id (and account_id), not private_ip alone, since private
# IPs are only unique within a network.
DECOY_INSTANCE_SAME_PRIVATE_IP_DIFFERENT_NETWORK: dict[str, Any] = {
    **INSTANCES_RESPONSE[0],
    "id": TEST_DECOY_INSTANCE_ID,
    "hostname": "decoy-in-other-network",
    "network_id": TEST_DECOY_NETWORK_ID,
}

# Same private_ip AND network_id as INSTANCES_RESPONSE[0] - only the account
# differs (loaded separately under TEST_DECOY_ACCOUNT_ID). Used to prove
# ROUTES_TO's account_id predicate specifically, decoupled from network_id:
# a graph holding two different Civo accounts' data (e.g. from two separate
# sync runs against the same Neo4j instance) could otherwise cross-link a
# backend to an unrelated account's instance if only private_ip and
# network_id were checked.
DECOY_INSTANCE_SAME_PRIVATE_IP_AND_NETWORK_DIFFERENT_ACCOUNT: dict[str, Any] = {
    **INSTANCES_RESPONSE[0],
    "id": TEST_DECOY_ACCOUNT_INSTANCE_ID,
    "hostname": "decoy-in-other-account",
}
