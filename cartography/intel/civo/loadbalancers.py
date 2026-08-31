import logging
from typing import Any

import neo4j
import requests

from cartography.client.core.tx import load
from cartography.graph.job import GraphJob
from cartography.intel.civo.util import fan_out_array_across_regions
from cartography.intel.civo.util import region_codes_for_feature
from cartography.intel.civo.util import require_non_empty
from cartography.models.civo.loadbalancer import CivoLoadBalancerBackendSchema
from cartography.models.civo.loadbalancer import CivoLoadBalancerInstancePoolSchema
from cartography.models.civo.loadbalancer import CivoLoadBalancerSchema
from cartography.util import timeit

logger = logging.getLogger(__name__)


@timeit
def sync(
    neo4j_session: neo4j.Session,
    api_session: requests.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    region_codes = region_codes_for_feature(
        common_job_parameters["REGIONS"], "loadbalancer"
    )
    load_balancers = get(
        api_session,
        common_job_parameters["BASE_URL"],
        region_codes,
    )
    transformed = transform_load_balancers(load_balancers)
    backends = transform_backends(load_balancers)
    instance_pools = transform_instance_pools(load_balancers)

    load_load_balancers(
        neo4j_session,
        transformed,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )
    load_backends(
        neo4j_session,
        backends,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )
    load_instance_pools(
        neo4j_session,
        instance_pools,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )


@timeit
def get(
    api_session: requests.Session,
    base_url: str,
    region_codes: list[str],
) -> list[dict[str, Any]]:
    return fan_out_array_across_regions(
        api_session, f"{base_url}/v2/loadbalancers", region_codes
    )


def transform_load_balancers(
    load_balancers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Civo load balancers route to backends two ways: an explicit IP:port list
    (see transform_backends) or a dynamic tag/name-based instance pool
    selector (see transform_instance_pools) - both modeled as their own node
    types, not flattened onto the load balancer.
    """
    result = []
    for lb in load_balancers:
        lb_id = require_non_empty(lb.get("id"), "load balancer id")
        result.append(
            {
                "id": lb_id,
                "name": lb.get("name"),
                "region": lb.get("region"),
                "algorithm": lb.get("algorithm"),
                "public_ip": lb.get("public_ip"),
                "private_ip": lb.get("private_ip"),
                "state": lb.get("state"),
                "network_id": lb.get("network_id"),
                "firewall_id": lb.get("firewall_id"),
                "cluster_id": lb.get("cluster_id") or None,
                "external_traffic_policy": lb.get("external_traffic_policy"),
            }
        )
    return result


def transform_instance_pools(
    load_balancers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Each instance pool is a dynamic tag/name-based backend selector with its
    own routing configuration - preserved as a distinct node per pool rather
    than combined across pools, so which tags/names/ports belonged together
    isn't lost.

    id is `<loadbalancer_id>/<protocol>/<source_port>`, not a list index:
    Civo's response order for instance_pools isn't documented as stable, and
    an index-based id would silently swap two pools' properties onto each
    other's node identity if the order ever changed between syncs.
    `source_port` is the port the load balancer listens on for that pool,
    which is a reasonable assumption of uniqueness on its own - but Civo's
    provider contract (civogo's `InstancePool` struct) doesn't actually
    state whether uniqueness is scoped to `source_port` alone or to the pair
    `(protocol, source_port)`, so this id uses the pair, the more permissive
    (and thus safer to assume) of the two: it only claims two pools collide
    when both `protocol` and `source_port` match, never flagging same-port
    pools on different protocols as a collision the way a `source_port`-only
    id would. `protocol` is separately optional in civogo's struct (can be
    missing entirely, normalized to `""` below rather than the literal
    string `"None"`), so two pools *could* still compute the same id.
    Rather than silently letting the second pool's row overwrite the
    first's in the graph, raise loudly on any duplicate id within one load
    balancer - that's a real, visible signal that this id scheme no longer
    captures every pool, instead of quietly losing a pool's configuration.
    """
    result = []
    for lb in load_balancers:
        lb_id = require_non_empty(lb.get("id"), "load balancer id")
        seen_ids: set[str] = set()
        for pool in lb.get("instance_pools") or []:
            source_port = require_non_empty(
                pool.get("source_port"), "load balancer instance pool source port"
            )
            health_check = pool.get("health_check") or {}
            protocol = pool.get("protocol") or ""
            pool_id = f"{lb_id}/{protocol}/{source_port}"
            if pool_id in seen_ids:
                raise ValueError(
                    f"Civo load balancer {lb_id!r} has two instance pools "
                    f"that both resolve to id {pool_id!r} (protocol "
                    f"{protocol!r}, source_port {source_port!r}). Refusing "
                    "to sync: loading both under the same id would silently "
                    "keep only one pool's configuration in the graph.",
                )
            seen_ids.add(pool_id)
            result.append(
                {
                    "id": pool_id,
                    "loadbalancer_id": lb_id,
                    "tags": pool.get("tags") or None,
                    "names": pool.get("names") or None,
                    "protocol": pool.get("protocol"),
                    "source_port": source_port,
                    "target_port": pool.get("target_port"),
                    "health_check_port": health_check.get("port"),
                    "health_check_path": health_check.get("path"),
                }
            )
    return result


def transform_backends(load_balancers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for lb in load_balancers:
        lb_id = require_non_empty(lb.get("id"), "load balancer id")
        for backend in lb.get("backends") or []:
            ip = require_non_empty(backend.get("ip"), "load balancer backend ip")
            protocol = require_non_empty(
                backend.get("protocol"), "load balancer backend protocol"
            )
            source_port = require_non_empty(
                backend.get("source_port"), "load balancer backend source_port"
            )
            target_port = require_non_empty(
                backend.get("target_port"), "load balancer backend target_port"
            )
            result.append(
                {
                    "id": f"{lb_id}/{ip}/{protocol}/{source_port}/{target_port}",
                    "loadbalancer_id": lb_id,
                    "network_id": lb.get("network_id"),
                    "ip": ip,
                    "protocol": protocol,
                    "source_port": source_port,
                    "target_port": target_port,
                    "health_check_port": backend.get("health_check_port"),
                }
            )
    return result


@timeit
def load_load_balancers(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoLoadBalancerSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def load_backends(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoLoadBalancerBackendSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def load_instance_pools(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoLoadBalancerInstancePoolSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def cleanup(
    neo4j_session: neo4j.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    GraphJob.from_node_schema(
        CivoLoadBalancerBackendSchema(), common_job_parameters
    ).run(neo4j_session)
    GraphJob.from_node_schema(
        CivoLoadBalancerInstancePoolSchema(), common_job_parameters
    ).run(neo4j_session)
    GraphJob.from_node_schema(CivoLoadBalancerSchema(), common_job_parameters).run(
        neo4j_session,
    )
