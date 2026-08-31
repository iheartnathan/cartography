import logging
from typing import Any

import neo4j
import requests

from cartography.client.core.tx import load
from cartography.graph.job import GraphJob
from cartography.intel.civo.util import fan_out_paginated_across_regions
from cartography.intel.civo.util import region_codes_for_feature
from cartography.intel.civo.util import require_non_empty
from cartography.models.civo.ip import CivoIPSchema
from cartography.util import timeit

logger = logging.getLogger(__name__)


@timeit
def sync(
    neo4j_session: neo4j.Session,
    api_session: requests.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    region_codes = region_codes_for_feature(common_job_parameters["REGIONS"], None)
    ips = get(
        api_session,
        common_job_parameters["BASE_URL"],
        region_codes,
    )
    transformed = transform_ips(ips)
    load_ips(
        neo4j_session,
        transformed,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )


@timeit
def get(
    api_session: requests.Session,
    base_url: str,
    region_codes: list[str],
) -> list[dict[str, Any]]:
    return fan_out_paginated_across_regions(
        api_session, f"{base_url}/v2/ips", region_codes
    )


def transform_ips(ips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Flattens the polymorphic assigned_to object - Neo4j does not support
    nested map properties. `assigned_to.type` is one of `instance` or
    `loadbalancer` (civogo's AssignedTo struct, ip.go) - split into
    `instance_id`/`loadbalancer_id` so each can drive its own typed
    relationship, instead of leaving the id generic and unlinkable.
    """
    result = []
    for ip in ips:
        ip_id = require_non_empty(ip.get("id"), "ip id")
        assigned_to = ip.get("assigned_to") or {}
        assigned_to_id = assigned_to.get("id") or None
        assigned_to_type = assigned_to.get("type") or None
        result.append(
            {
                "id": ip_id,
                "name": ip.get("name"),
                "region": ip.get("region"),
                "ip": ip.get("ip"),
                "assigned_to_id": assigned_to_id,
                "assigned_to_type": assigned_to_type,
                "assigned_to_name": assigned_to.get("name") or None,
                "instance_id": (
                    assigned_to_id if assigned_to_type == "instance" else None
                ),
                "loadbalancer_id": (
                    assigned_to_id if assigned_to_type == "loadbalancer" else None
                ),
            }
        )
    return result


@timeit
def load_ips(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoIPSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def cleanup(
    neo4j_session: neo4j.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    GraphJob.from_node_schema(CivoIPSchema(), common_job_parameters).run(
        neo4j_session,
    )
