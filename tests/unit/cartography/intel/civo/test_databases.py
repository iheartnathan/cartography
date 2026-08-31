import pytest

import cartography.intel.civo.databases
from tests.data.civo.databases import DATABASES_PAGE
from tests.data.civo.databases import TEST_DATABASE_ID


def test_transform_databases_drops_all_password_fields() -> None:
    # Act
    databases = cartography.intel.civo.databases.transform_databases(
        DATABASES_PAGE["items"]
    )

    # Assert: real DB passwords never reach the transformed row, but username
    # (not secret by itself) is kept.
    row = databases[0]
    assert row["id"] == TEST_DATABASE_ID
    assert row["username"] == "civo"
    assert "password" not in row
    assert "database_user_info" not in row


def test_transform_databases_rejects_empty_id() -> None:
    database = {**DATABASES_PAGE["items"][0], "id": ""}
    with pytest.raises(ValueError, match="missing required non-empty database id"):
        cartography.intel.civo.databases.transform_databases([database])
