import logging
from typing import Any

import neo4j
import requests

from cartography.client.core.tx import load
from cartography.graph.job import GraphJob
from cartography.intel.civo.util import fan_out_paginated_across_regions
from cartography.intel.civo.util import region_codes_for_feature
from cartography.intel.civo.util import require_non_empty
from cartography.models.civo.database import CivoDatabaseSchema
from cartography.util import timeit

logger = logging.getLogger(__name__)


@timeit
def sync(
    neo4j_session: neo4j.Session,
    api_session: requests.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    region_codes = region_codes_for_feature(common_job_parameters["REGIONS"], "dbaas")
    databases = get(
        api_session,
        common_job_parameters["BASE_URL"],
        region_codes,
    )
    transformed = transform_databases(databases)
    load_databases(
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
        api_session, f"{base_url}/v2/databases", region_codes
    )


def transform_databases(databases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Drops password and database_user_info[].password - both real credentials
    returned by the API - before any row is built. username is kept (not
    secret by itself).
    """
    result = []
    for database in databases:
        database_id = require_non_empty(database.get("id"), "database id")
        result.append(
            {
                "id": database_id,
                "name": database.get("name"),
                "region": database.get("region"),
                "software": database.get("software"),
                "software_version": database.get("software_version"),
                "nodes": database.get("nodes"),
                "size": database.get("size"),
                "status": database.get("status"),
                "public_ipv4": database.get("public_ipv4"),
                "private_ipv4": database.get("private_ipv4"),
                "port": database.get("port"),
                "username": database.get("username"),
                "network_id": database.get("network_id"),
                "firewall_id": database.get("firewall_id"),
                "dns_entry": database.get("dns_entry"),
            }
        )
    return result


@timeit
def load_databases(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoDatabaseSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def cleanup(
    neo4j_session: neo4j.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    GraphJob.from_node_schema(CivoDatabaseSchema(), common_job_parameters).run(
        neo4j_session,
    )
