import logging
from typing import Any

import neo4j
import requests

from cartography.client.core.tx import load
from cartography.graph.job import GraphJob
from cartography.intel.civo.util import fan_out_paginated_across_regions
from cartography.intel.civo.util import region_codes_for_feature
from cartography.intel.civo.util import require_non_empty
from cartography.models.civo.instance import CivoInstanceSchema
from cartography.util import timeit

logger = logging.getLogger(__name__)


@timeit
def sync(
    neo4j_session: neo4j.Session,
    api_session: requests.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    region_codes = region_codes_for_feature(common_job_parameters["REGIONS"], "iaas")
    instances = get(
        api_session,
        common_job_parameters["BASE_URL"],
        region_codes,
    )
    transformed = transform_instances(instances)
    load_instances(
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
        api_session, f"{base_url}/v2/instances", region_codes
    )


def transform_instances(instances: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Drops fields that are real credentials or may embed user secrets:
    initial_password, rescue_password, civostatsd_token (all real credentials)
    and script (a user-supplied cloud-init script that commonly embeds
    tokens/secrets at creation time). Also drops civostatsd_stats* metric
    blobs and openstack/pseudo-ip internals, which carry no security value.
    """
    result = []
    for instance in instances:
        instance_id = require_non_empty(instance.get("id"), "instance id")
        result.append(
            {
                "id": instance_id,
                "hostname": instance.get("hostname"),
                "size": instance.get("size"),
                "region": instance.get("region"),
                "status": instance.get("status"),
                "network_id": instance.get("network_id"),
                "private_ip": instance.get("private_ip"),
                "public_ip": instance.get("public_ip"),
                "ipv6": instance.get("ipv6"),
                "reverse_dns": instance.get("reverse_dns"),
                "source_type": instance.get("source_type"),
                "source_id": instance.get("source_id"),
                "initial_user": instance.get("initial_user"),
                "firewall_id": instance.get("firewall_id"),
                "ssh_key_id": instance.get("ssh_key_id"),
                "reserved_ip_id": instance.get("reserved_ip_id"),
                "tags": instance.get("tags"),
                "allowed_ips": instance.get("allowed_ips"),
                "cpu_cores": instance.get("cpu_cores"),
                "ram_mb": instance.get("ram_mb"),
                "disk_gb": instance.get("disk_gb"),
                "volume_backed": instance.get("volume_backed"),
                "gpu_count": instance.get("gpu_count"),
                "gpu_type": instance.get("gpu_type"),
                "created_at": instance.get("created_at"),
            }
        )
    return result


@timeit
def load_instances(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoInstanceSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def cleanup(
    neo4j_session: neo4j.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    GraphJob.from_node_schema(CivoInstanceSchema(), common_job_parameters).run(
        neo4j_session,
    )
