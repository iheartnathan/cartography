from typing import Any

from tests.data.civo.loadbalancers import TEST_LOADBALANCER_ID

TEST_INSTANCE_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
TEST_RESERVED_IP_ID = "9f8e7d6c-5b4a-3928-1706-f5e4d3c2b1a0"
TEST_LB_RESERVED_IP_ID = "2b1a0e9f-8d7c-6b5a-4938-271605f4e3d2"
TEST_UNASSIGNED_RESERVED_IP_ID = "7c6b5a49-3827-1605-f4e3-d2c1b0a9f8e7"

RESERVED_IPS_PAGE: dict[str, Any] = {
    "page": 1,
    "per_page": 20,
    "pages": 1,
    "items": [
        {
            "id": TEST_RESERVED_IP_ID,
            "name": "reserved-web-ip",
            "ip": "74.220.16.30",
            "assigned_to": {
                "id": TEST_INSTANCE_ID,
                "type": "instance",
                "name": "web-1",
            },
        },
        {
            "id": TEST_LB_RESERVED_IP_ID,
            "name": "reserved-lb-ip",
            "ip": "74.220.16.40",
            "assigned_to": {
                "id": TEST_LOADBALANCER_ID,
                "type": "loadbalancer",
                "name": "prod-lb",
            },
        },
        {
            "id": TEST_UNASSIGNED_RESERVED_IP_ID,
            "name": "reserved-unassigned-ip",
            "ip": "74.220.16.50",
            "assigned_to": None,
        },
    ],
}
