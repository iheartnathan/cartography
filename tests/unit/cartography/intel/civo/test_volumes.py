import cartography.intel.civo.volumes
from tests.data.civo.volumes import TEST_INSTANCE_ID
from tests.data.civo.volumes import TEST_VOLUME_ID
from tests.data.civo.volumes import VOLUMES_RESPONSE


def test_transform_volumes() -> None:
    # Act
    volumes = cartography.intel.civo.volumes.transform_volumes(VOLUMES_RESPONSE)

    # Assert
    row = volumes[0]
    assert row["id"] == TEST_VOLUME_ID
    assert row["instance_id"] == TEST_INSTANCE_ID
    assert row["cluster_id"] is None
    assert row["size_gb"] == 50
