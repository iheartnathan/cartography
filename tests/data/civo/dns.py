from typing import Any

TEST_DOMAIN_ID = "5c4b3a29-1807-f6e5-d4c3-b2a190807f6e"
TEST_RECORD_ID = "6d5c4b3a-2918-07f6-e5d4-c3b2a190807f"

DNS_DOMAINS_RESPONSE: list[dict[str, Any]] = [
    {
        "id": TEST_DOMAIN_ID,
        "account_id": "44aab548-61ca-11e5-860e-5cf9389be614",
        "name": "example.com",
    },
]

DNS_RECORDS_RESPONSE: list[dict[str, Any]] = [
    {
        "id": TEST_RECORD_ID,
        "account_id": "44aab548-61ca-11e5-860e-5cf9389be614",
        "domain_id": TEST_DOMAIN_ID,
        "name": "www",
        "value": "74.220.16.10",
        "type": "a",
        "priority": 0,
        "ttl": 600,
        "created_at": "2026-01-05T09:00:00Z",
    },
]
