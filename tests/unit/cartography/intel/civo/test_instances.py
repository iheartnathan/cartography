import pytest

import cartography.intel.civo.instances
from tests.data.civo.instances import INSTANCES_RESPONSE
from tests.data.civo.instances import TEST_FIREWALL_ID
from tests.data.civo.instances import TEST_INSTANCE_ID
from tests.data.civo.instances import TEST_NETWORK_ID
from tests.data.civo.instances import TEST_SSH_KEY_ID


def test_transform_instances_drops_all_secret_and_sensitive_fields() -> None:
    # Act
    instances = cartography.intel.civo.instances.transform_instances(INSTANCES_RESPONSE)

    # Assert: real credentials and a user-supplied script (which commonly
    # embeds secrets) never reach the transformed row.
    row = instances[0]
    assert row["id"] == TEST_INSTANCE_ID
    for secret_field in (
        "initial_password",
        "rescue_password",
        "civostatsd_token",
        "civostatsd_stats",
        "script",
        "ssh_key",
    ):
        assert secret_field not in row


def test_transform_instances_keeps_real_fields() -> None:
    # Act
    instances = cartography.intel.civo.instances.transform_instances(INSTANCES_RESPONSE)

    # Assert
    row = instances[0]
    assert row["hostname"] == "web-1"
    assert row["network_id"] == TEST_NETWORK_ID
    assert row["firewall_id"] == TEST_FIREWALL_ID
    assert row["ssh_key_id"] == TEST_SSH_KEY_ID
    assert row["status"] == "ACTIVE"
    assert row["tags"] == ["web", "production"]
    # source_type/source_id, not template_id - Civo's real instance
    # list/retrieve responses don't carry template_id at all (confirmed
    # live), so this is the actual image-provenance field pair.
    assert row["source_type"] == "diskimage"
    assert row["source_id"] == "811a8dfb-8202-49ad-b1ef-1e6320b20497"


def test_transform_instances_rejects_empty_id() -> None:
    instance = {**INSTANCES_RESPONSE[0], "id": ""}
    with pytest.raises(ValueError, match="missing required non-empty instance id"):
        cartography.intel.civo.instances.transform_instances([instance])
