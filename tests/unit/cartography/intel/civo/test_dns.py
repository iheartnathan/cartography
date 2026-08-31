import pytest

import cartography.intel.civo.dns
from tests.data.civo.dns import DNS_DOMAINS_RESPONSE
from tests.data.civo.dns import DNS_RECORDS_RESPONSE
from tests.data.civo.dns import TEST_DOMAIN_ID
from tests.data.civo.dns import TEST_RECORD_ID


def test_transform_domains_and_records() -> None:
    # Act
    domains = cartography.intel.civo.dns.transform_domains(DNS_DOMAINS_RESPONSE)
    records = cartography.intel.civo.dns.transform_records(
        DNS_RECORDS_RESPONSE, TEST_DOMAIN_ID
    )

    # Assert
    assert domains[0]["id"] == TEST_DOMAIN_ID
    assert domains[0]["name"] == "example.com"
    assert records[0]["id"] == TEST_RECORD_ID
    assert records[0]["domain_id"] == TEST_DOMAIN_ID
    assert records[0]["type"] == "a"
    assert records[0]["value"] == "74.220.16.10"


def test_transform_domains_rejects_empty_id() -> None:
    domain = {**DNS_DOMAINS_RESPONSE[0], "id": ""}
    with pytest.raises(ValueError, match="missing required non-empty dns domain id"):
        cartography.intel.civo.dns.transform_domains([domain])
