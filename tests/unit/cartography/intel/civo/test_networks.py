import pytest

import cartography.intel.civo.networks
from tests.data.civo.networks import NETWORKS_RESPONSE
from tests.data.civo.networks import SUBNETS_RESPONSE
from tests.data.civo.networks import TEST_NETWORK_ID
from tests.data.civo.networks import TEST_SUBNET_ID

TEST_REGION_CODE = "lon1"


def test_transform_networks_and_subnets() -> None:
    # Act
    networks = cartography.intel.civo.networks.transform_networks(
        [(n, TEST_REGION_CODE) for n in NETWORKS_RESPONSE]
    )
    subnets = cartography.intel.civo.networks.transform_subnets(
        SUBNETS_RESPONSE, TEST_NETWORK_ID
    )

    # Assert
    assert networks[0]["id"] == TEST_NETWORK_ID
    assert networks[0]["label"] == "production-vpc"
    assert networks[0]["cidr"] == "192.168.1.0/24"
    assert subnets[0]["id"] == TEST_SUBNET_ID
    assert subnets[0]["network_id"] == TEST_NETWORK_ID


def test_transform_networks_rejects_empty_id() -> None:
    network = {**NETWORKS_RESPONSE[0], "id": ""}
    with pytest.raises(ValueError, match="missing required non-empty network id"):
        cartography.intel.civo.networks.transform_networks(
            [(network, TEST_REGION_CODE)]
        )
