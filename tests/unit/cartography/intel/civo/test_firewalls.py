from unittest import mock

import pytest
import requests

import cartography.intel.civo.firewalls
from tests.data.civo.firewalls import FIREWALL_RULES_RESPONSE
from tests.data.civo.firewalls import FIREWALLS_RESPONSE
from tests.data.civo.firewalls import TEST_FIREWALL_ID
from tests.data.civo.firewalls import TEST_FIREWALL_RULE_ID
from tests.data.civo.networks import TEST_NETWORK_ID

TEST_REGION_CODE = "lon1"


def _make_response(payload):
    resp = mock.MagicMock(spec=requests.Response)
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_transform_firewalls_and_rules() -> None:
    # Act
    firewalls = cartography.intel.civo.firewalls.transform_firewalls(
        [(f, TEST_REGION_CODE) for f in FIREWALLS_RESPONSE]
    )
    rules = cartography.intel.civo.firewalls.transform_rules(
        FIREWALL_RULES_RESPONSE, TEST_FIREWALL_ID
    )

    # Assert
    assert firewalls[0]["id"] == TEST_FIREWALL_ID
    assert firewalls[0]["network_id"] == TEST_NETWORK_ID
    assert rules[0]["id"] == TEST_FIREWALL_RULE_ID
    assert rules[0]["firewall_id"] == TEST_FIREWALL_ID
    assert rules[0]["direction"] == "ingress"
    assert rules[0]["action"] == "allow"
    assert rules[0]["cidr"] == ["0.0.0.0/0"]


def test_transform_firewalls_rejects_empty_id() -> None:
    firewall = {**FIREWALLS_RESPONSE[0], "id": ""}
    with pytest.raises(ValueError, match="missing required non-empty firewall id"):
        cartography.intel.civo.firewalls.transform_firewalls(
            [(firewall, TEST_REGION_CODE)]
        )


def test_get_firewalls_dedups_across_regions() -> None:
    # Arrange: the same firewall appears in two regions' responses (e.g. an
    # endpoint that ignores region and returns the full account list every
    # time) - must not be duplicated.
    session = mock.MagicMock(spec=requests.Session)
    session.get.side_effect = [
        _make_response(FIREWALLS_RESPONSE),
        _make_response(FIREWALLS_RESPONSE),
    ]

    # Act
    firewalls_by_region = cartography.intel.civo.firewalls.get(
        session, "https://api.civo.com", ["lon1", "nyc1"]
    )

    # Assert: only one (firewall, region) pair survives, tagged with the
    # first region that produced it.
    assert len(firewalls_by_region) == 1
    assert firewalls_by_region[0][0]["id"] == TEST_FIREWALL_ID
    assert firewalls_by_region[0][1] == "lon1"
