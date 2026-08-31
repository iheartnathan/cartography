from typing import Any

TEST_OBJECTSTORE_ID = "11223344-5566-7788-99aa-bbccddeeff00"
TEST_OBJECTSTORE_CREDENTIAL_ID = "00ffeedd-ccbb-aa99-8877-665544332211"

OBJECTSTORES_PAGE: dict[str, Any] = {
    "page": 1,
    "per_page": 20,
    "pages": 1,
    "items": [
        {
            "id": TEST_OBJECTSTORE_ID,
            "name": "app-uploads",
            "max_size": 500,
            "owner_info": {
                "access_key_id": "AKIACIVOEXAMPLE123",
                "name": "app-uploads-owner",
                "credential_id": TEST_OBJECTSTORE_CREDENTIAL_ID,
            },
            "objectstore_endpoint": "objectstore.lon1.civo.com",
            "status": "ready",
        },
    ],
}

OBJECTSTORE_CREDENTIALS_PAGE: dict[str, Any] = {
    "page": 1,
    "per_page": 20,
    "pages": 1,
    "items": [
        {
            "id": TEST_OBJECTSTORE_CREDENTIAL_ID,
            "name": "app-uploads-owner",
            "access_key_id": "AKIACIVOEXAMPLE123",
            # Real secret returned by Civo's API - must never reach the graph.
            "secret_access_key_id": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "max_size_gb": 500,
            "suspended": False,
            "status": "active",
        },
    ],
}
