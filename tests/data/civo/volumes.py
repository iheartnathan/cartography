from typing import Any

TEST_INSTANCE_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
TEST_NETWORK_ID = "8d5c4e10-8b3a-4e6a-9b2e-1c2f3a4b5c6d"
TEST_VOLUME_ID = "aa11bb22-cc33-dd44-ee55-ff6677889900"

VOLUMES_RESPONSE: list[dict[str, Any]] = [
    {
        "id": TEST_VOLUME_ID,
        "name": "data-volume",
        "instance_id": TEST_INSTANCE_ID,
        "cluster_id": "",
        "network_id": TEST_NETWORK_ID,
        "mountpoint": "/mnt/data",
        "status": "attached",
        "volume_type": "ssd",
        "size_gb": 50,
        "bootable": False,
        "created_at": "2026-01-15T10:30:00Z",
    },
]
