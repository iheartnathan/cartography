import pytest

import cartography.intel.civo.loadbalancers
from tests.data.civo.loadbalancers import LOAD_BALANCERS_RESPONSE
from tests.data.civo.loadbalancers import TEST_CLUSTER_ID
from tests.data.civo.loadbalancers import TEST_FIREWALL_ID
from tests.data.civo.loadbalancers import TEST_INSTANCE_PRIVATE_IP
from tests.data.civo.loadbalancers import TEST_LOADBALANCER_ID
from tests.data.civo.loadbalancers import TEST_NETWORK_ID


def test_transform_load_balancers() -> None:
    # Act
    lbs = cartography.intel.civo.loadbalancers.transform_load_balancers(
        LOAD_BALANCERS_RESPONSE
    )

    # Assert
    row = lbs[0]
    assert row["id"] == TEST_LOADBALANCER_ID
    assert row["firewall_id"] == TEST_FIREWALL_ID
    assert row["cluster_id"] == TEST_CLUSTER_ID
    assert row["region"] == "lon1"
    # instance_pools is modeled as its own node type (transform_instance_pools),
    # not flattened onto the load balancer.
    assert "instance_pool_tags" not in row
    assert "instance_pool_names" not in row


def test_transform_backends_builds_synthetic_id_and_links_to_loadbalancer() -> None:
    # Act
    backends = cartography.intel.civo.loadbalancers.transform_backends(
        LOAD_BALANCERS_RESPONSE
    )

    # Assert: id is a synthetic
    # `<loadbalancer_id>/<ip>/<protocol>/<source_port>/<target_port>`, since
    # Civo backends have no id of their own.
    row = backends[0]
    assert (
        row["id"] == f"{TEST_LOADBALANCER_ID}/{TEST_INSTANCE_PRIVATE_IP}/http/80/8080"
    )
    assert row["loadbalancer_id"] == TEST_LOADBALANCER_ID
    # network_id is inherited from the parent load balancer, not the backend
    # itself (Civo backends carry no network field) - used to scope the
    # ROUTES_TO match so a repeated private IP in another network/account
    # can't resolve to the wrong instance.
    assert row["network_id"] == TEST_NETWORK_ID
    assert row["ip"] == TEST_INSTANCE_PRIVATE_IP
    assert row["protocol"] == "http"
    assert row["source_port"] == 80
    assert row["target_port"] == 8080
    assert row["health_check_port"] == 8080


def test_transform_backends_same_ip_and_source_port_different_protocol_get_different_ids() -> (
    None
):
    """
    Regression test: Civo's Load Balancer API defines a backend by its full
    protocol/source_port/target_port tuple, not just ip+source_port - e.g. a
    TCP backend on source port 53 (DNS over TCP) and a UDP backend on the
    same source port 53 (DNS over UDP) are both valid, distinct backends. An
    id built from only `<ip>/<source_port>` would collide the two onto one
    Neo4j node, silently dropping one backend's routing configuration.
    """
    lb = {
        **LOAD_BALANCERS_RESPONSE[0],
        "backends": [
            {
                "ip": "10.0.0.5",
                "protocol": "tcp",
                "source_port": 53,
                "target_port": 8053,
                "health_check_port": 8053,
            },
            {
                "ip": "10.0.0.5",
                "protocol": "udp",
                "source_port": 53,
                "target_port": 5353,
                "health_check_port": 5353,
            },
        ],
    }

    # Act
    backends = cartography.intel.civo.loadbalancers.transform_backends([lb])

    # Assert: two distinct ids, one per backend - no collision.
    ids = {row["id"] for row in backends}
    assert len(ids) == 2
    assert ids == {
        f"{TEST_LOADBALANCER_ID}/10.0.0.5/tcp/53/8053",
        f"{TEST_LOADBALANCER_ID}/10.0.0.5/udp/53/5353",
    }


def test_transform_instance_pools_preserves_each_pools_own_config() -> None:
    # Act
    pools = cartography.intel.civo.loadbalancers.transform_instance_pools(
        LOAD_BALANCERS_RESPONSE
    )

    # Assert: id is a synthetic `<loadbalancer_id>/<protocol>/<source_port>`,
    # not a list index - since Civo instance pools have no id of their own,
    # and an index would silently swap two pools' properties onto each
    # other's node identity if response order ever changed. Each pool's
    # tags/names and routing config (protocol/ports/health check) are kept
    # together, rather than combined across every pool on the load balancer.
    row = pools[0]
    assert row["id"] == f"{TEST_LOADBALANCER_ID}/https/443"
    assert row["loadbalancer_id"] == TEST_LOADBALANCER_ID
    assert row["tags"] == ["web"]
    assert row["names"] == ["web-1"]
    assert row["protocol"] == "https"
    assert row["source_port"] == 443
    assert row["target_port"] == 8443
    assert row["health_check_port"] == 8443
    assert row["health_check_path"] == "/healthz"


def test_transform_instance_pools_id_stable_under_reordering() -> None:
    # Two pools, reversed order across two calls - each pool's node id must
    # stay tied to its own (protocol, source_port), not to its list position,
    # or its properties would swap onto the wrong node identity.
    lb = {
        **LOAD_BALANCERS_RESPONSE[0],
        "instance_pools": [
            {
                "tags": ["web"],
                "names": ["web-1"],
                "protocol": "https",
                "source_port": 443,
            },
            {
                "tags": ["api"],
                "names": ["api-1"],
                "protocol": "http",
                "source_port": 80,
            },
        ],
    }
    reordered_lb = {
        **lb,
        "instance_pools": list(reversed(lb["instance_pools"])),
    }

    pools = cartography.intel.civo.loadbalancers.transform_instance_pools([lb])
    reordered_pools = cartography.intel.civo.loadbalancers.transform_instance_pools(
        [reordered_lb]
    )

    by_id = {row["id"]: row for row in pools}
    reordered_by_id = {row["id"]: row for row in reordered_pools}
    assert by_id.keys() == reordered_by_id.keys()
    for pool_id, row in by_id.items():
        assert row["tags"] == reordered_by_id[pool_id]["tags"]


def test_transform_instance_pools_rejects_missing_source_port() -> None:
    lb = {
        **LOAD_BALANCERS_RESPONSE[0],
        "instance_pools": [{"tags": ["web"], "protocol": "https"}],
    }

    with pytest.raises(
        ValueError,
        match="missing required non-empty load balancer instance pool source port",
    ):
        cartography.intel.civo.loadbalancers.transform_instance_pools([lb])


def test_transform_instance_pools_empty_when_no_pools() -> None:
    lb = {**LOAD_BALANCERS_RESPONSE[0], "instance_pools": []}

    assert cartography.intel.civo.loadbalancers.transform_instance_pools([lb]) == []


def test_transform_instance_pools_raises_on_duplicate_id() -> None:
    # (protocol, source_port) is a strong identity in practice, but Civo's
    # SDK doesn't formally guarantee it's unique - two pools that both
    # resolve to the same id must raise loudly rather than silently keeping
    # only one pool's configuration in the graph.
    lb = {
        **LOAD_BALANCERS_RESPONSE[0],
        "instance_pools": [
            {"tags": ["web"], "protocol": "http", "source_port": 80},
            {"tags": ["api"], "protocol": "http", "source_port": 80},
        ],
    }

    with pytest.raises(ValueError, match="two instance pools"):
        cartography.intel.civo.loadbalancers.transform_instance_pools([lb])


def test_transform_instance_pools_normalizes_missing_protocol_in_id() -> None:
    # protocol is optional in civogo's InstancePool struct - a missing value
    # must not be stringified as the literal "None" in the id.
    lb = {
        **LOAD_BALANCERS_RESPONSE[0],
        "instance_pools": [{"tags": ["web"], "source_port": 80}],
    }

    pools = cartography.intel.civo.loadbalancers.transform_instance_pools([lb])

    assert pools[0]["id"] == f"{TEST_LOADBALANCER_ID}//80"
    assert "None" not in pools[0]["id"]
    # The property itself still reflects the real (missing) value.
    assert pools[0]["protocol"] is None


def test_transform_backends_empty_when_no_backends() -> None:
    lb = {**LOAD_BALANCERS_RESPONSE[0], "backends": []}

    assert cartography.intel.civo.loadbalancers.transform_backends([lb]) == []


def test_transform_backends_rejects_empty_ip() -> None:
    lb = {
        **LOAD_BALANCERS_RESPONSE[0],
        "backends": [{**LOAD_BALANCERS_RESPONSE[0]["backends"][0], "ip": ""}],
    }

    with pytest.raises(
        ValueError, match="missing required non-empty load balancer backend ip"
    ):
        cartography.intel.civo.loadbalancers.transform_backends([lb])


def test_transform_backends_rejects_missing_protocol() -> None:
    # protocol is part of the synthetic id (see the collision regression
    # test above) - a missing value must raise, not silently produce an id
    # like "lb-1/10.0.0.5/None/None/None" that could collide with another
    # malformed backend.
    lb = {
        **LOAD_BALANCERS_RESPONSE[0],
        "backends": [{**LOAD_BALANCERS_RESPONSE[0]["backends"][0], "protocol": None}],
    }

    with pytest.raises(
        ValueError,
        match="missing required non-empty load balancer backend protocol",
    ):
        cartography.intel.civo.loadbalancers.transform_backends([lb])


def test_transform_backends_rejects_missing_source_port() -> None:
    lb = {
        **LOAD_BALANCERS_RESPONSE[0],
        "backends": [
            {**LOAD_BALANCERS_RESPONSE[0]["backends"][0], "source_port": None},
        ],
    }

    with pytest.raises(
        ValueError,
        match="missing required non-empty load balancer backend source_port",
    ):
        cartography.intel.civo.loadbalancers.transform_backends([lb])


def test_transform_backends_rejects_missing_target_port() -> None:
    lb = {
        **LOAD_BALANCERS_RESPONSE[0],
        "backends": [
            {**LOAD_BALANCERS_RESPONSE[0]["backends"][0], "target_port": None},
        ],
    }

    with pytest.raises(
        ValueError,
        match="missing required non-empty load balancer backend target_port",
    ):
        cartography.intel.civo.loadbalancers.transform_backends([lb])


def test_transform_load_balancers_rejects_empty_id() -> None:
    lb = {**LOAD_BALANCERS_RESPONSE[0], "id": ""}
    with pytest.raises(ValueError, match="missing required non-empty load balancer id"):
        cartography.intel.civo.loadbalancers.transform_load_balancers([lb])
