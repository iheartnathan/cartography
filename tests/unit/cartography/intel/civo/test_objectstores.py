import cartography.intel.civo.objectstores
from tests.data.civo.objectstores import OBJECTSTORE_CREDENTIALS_PAGE
from tests.data.civo.objectstores import OBJECTSTORES_PAGE
from tests.data.civo.objectstores import TEST_OBJECTSTORE_CREDENTIAL_ID
from tests.data.civo.objectstores import TEST_OBJECTSTORE_ID


def test_transform_stores_flattens_owner_info_and_keeps_access_key_id() -> None:
    # Act
    stores = cartography.intel.civo.objectstores.transform_stores(
        OBJECTSTORES_PAGE["items"]
    )

    # Assert: nested owner_info is flattened; access_key_id (not secret) is kept.
    row = stores[0]
    assert row["id"] == TEST_OBJECTSTORE_ID
    assert row["owner_access_key_id"] == "AKIACIVOEXAMPLE123"
    assert row["owner_credential_id"] == TEST_OBJECTSTORE_CREDENTIAL_ID
    assert "owner_info" not in row


def test_transform_credentials_drops_secret_access_key() -> None:
    # Act
    credentials = cartography.intel.civo.objectstores.transform_credentials(
        OBJECTSTORE_CREDENTIALS_PAGE["items"]
    )

    # Assert: the real secret never reaches the transformed row.
    row = credentials[0]
    assert row["id"] == TEST_OBJECTSTORE_CREDENTIAL_ID
    assert row["access_key_id"] == "AKIACIVOEXAMPLE123"
    assert "secret_access_key_id" not in row
