import logging
from typing import Any

import neo4j
import requests

from cartography.client.core.tx import load
from cartography.graph.job import GraphJob
from cartography.intel.civo.util import fan_out_array_across_regions
from cartography.intel.civo.util import region_codes_for_feature
from cartography.intel.civo.util import require_non_empty
from cartography.models.civo.volume import CivoVolumeSchema
from cartography.util import timeit

logger = logging.getLogger(__name__)


@timeit
def sync(
    neo4j_session: neo4j.Session,
    api_session: requests.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    region_codes = region_codes_for_feature(common_job_parameters["REGIONS"], "volume")
    volumes = get(
        api_session,
        common_job_parameters["BASE_URL"],
        region_codes,
    )
    transformed = transform_volumes(volumes)
    load_volumes(
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
    return fan_out_array_across_regions(
        api_session, f"{base_url}/v2/volumes", region_codes
    )


def transform_volumes(volumes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for volume in volumes:
        volume_id = require_non_empty(volume.get("id"), "volume id")
        result.append(
            {
                "id": volume_id,
                "name": volume.get("name"),
                "region": volume.get("region"),
                "instance_id": volume.get("instance_id") or None,
                "cluster_id": volume.get("cluster_id") or None,
                "network_id": volume.get("network_id"),
                "mountpoint": volume.get("mountpoint"),
                "status": volume.get("status"),
                "volume_type": volume.get("volume_type"),
                "size_gb": volume.get("size_gb"),
                "bootable": volume.get("bootable"),
                "created_at": volume.get("created_at"),
            }
        )
    return result


@timeit
def load_volumes(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoVolumeSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def cleanup(
    neo4j_session: neo4j.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    GraphJob.from_node_schema(CivoVolumeSchema(), common_job_parameters).run(
        neo4j_session,
    )
