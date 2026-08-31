from typing import Any

TEST_NETWORK_ID = "8d5c4e10-8b3a-4e6a-9b2e-1c2f3a4b5c6d"
TEST_FIREWALL_ID = "f1e2d3c4-b5a6-4978-8899-001122334455"
TEST_DATABASE_ID = "7e6d5c4b-3a29-1807-f6e5-d4c3b2a19080"

DATABASES_PAGE: dict[str, Any] = {
    "page": 1,
    "per_page": 20,
    "pages": 1,
    "items": [
        {
            "id": TEST_DATABASE_ID,
            "name": "prod-db",
            "nodes": 1,
            "size": "g4s.dbaas.small",
            "software": "PostgreSQL",
            "software_version": "16",
            "public_ipv4": "74.220.16.40",
            "private_ipv4": "192.168.1.40",
            "network_id": TEST_NETWORK_ID,
            "firewall_id": TEST_FIREWALL_ID,
            "port": 5432,
            "username": "civo",
            # Real credential returned by Civo's API - must never reach the graph.
            "password": "Sup3rSecretDbPassw0rd!",
            "database_user_info": [
                {
                    "username": "civo",
                    "password": "Sup3rSecretDbPassw0rd!",
                    "port": 5432,
                },
            ],
            "dns_entry": "prod-db.civo.com",
            "status": "ready",
        },
    ],
}
