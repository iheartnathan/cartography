import cartography.intel.civo.ips
from tests.data.civo.ips import IPS_PAGE
from tests.data.civo.ips import TEST_INSTANCE_ID
from tests.data.civo.ips import TEST_IP_ID
from tests.data.civo.ips import TEST_LB_IP_ID
from tests.data.civo.loadbalancers import TEST_LOADBALANCER_ID


def test_transform_ips_flattens_assigned_to() -> None:
    # Act
    ips = cartography.intel.civo.ips.transform_ips(IPS_PAGE["items"])

    # Assert: nested assigned_to is flattened into flat fields.
    row = ips[0]
    assert row["id"] == TEST_IP_ID
    assert row["ip"] == "74.220.16.30"
    assert row["assigned_to_id"] == TEST_INSTANCE_ID
    assert row["assigned_to_type"] == "instance"
    assert "assigned_to" not in row


def test_transform_ips_splits_assigned_to_by_type() -> None:
    # Act: assigned_to.type is one of `instance` or `loadbalancer` - only the
    # matching id field should be populated, driving that resource's own
    # typed ASSIGNED_TO relationship (and leaving the other one unresolved).
    ips = cartography.intel.civo.ips.transform_ips(IPS_PAGE["items"])
    by_id = {row["id"]: row for row in ips}

    instance_ip = by_id[TEST_IP_ID]
    assert instance_ip["instance_id"] == TEST_INSTANCE_ID
    assert instance_ip["loadbalancer_id"] is None

    lb_ip = by_id[TEST_LB_IP_ID]
    assert lb_ip["instance_id"] is None
    assert lb_ip["loadbalancer_id"] == TEST_LOADBALANCER_ID
