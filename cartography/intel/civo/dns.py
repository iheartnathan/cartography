import logging
from typing import Any

import neo4j
import requests

from cartography.client.core.tx import load
from cartography.graph.job import GraphJob
from cartography.intel.civo.util import get_json_array
from cartography.intel.civo.util import require_non_empty
from cartography.models.civo.dns import CivoDNSDomainSchema
from cartography.models.civo.dns import CivoDNSRecordSchema
from cartography.util import timeit

logger = logging.getLogger(__name__)


@timeit
def sync(
    neo4j_session: neo4j.Session,
    api_session: requests.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    domains = get(api_session, common_job_parameters["BASE_URL"])
    transformed_domains = transform_domains(domains)
    records = get_records(
        api_session, common_job_parameters["BASE_URL"], transformed_domains
    )

    load_domains(
        neo4j_session,
        transformed_domains,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )
    load_records(
        neo4j_session,
        records,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )


@timeit
def get(
    api_session: requests.Session,
    base_url: str,
) -> list[dict[str, Any]]:
    return get_json_array(api_session, f"{base_url}/v2/dns")


@timeit
def get_records(
    api_session: requests.Session,
    base_url: str,
    domains: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    all_records: list[dict[str, Any]] = []
    for domain in domains:
        domain_id = domain["id"]
        records = get_json_array(api_session, f"{base_url}/v2/dns/{domain_id}/records")
        all_records.extend(transform_records(records, domain_id))
    return all_records


def transform_domains(domains: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for domain in domains:
        domain_id = require_non_empty(domain.get("id"), "dns domain id")
        result.append(
            {
                "id": domain_id,
                "name": domain.get("name"),
            }
        )
    return result


def transform_records(
    records: list[dict[str, Any]], domain_id: str
) -> list[dict[str, Any]]:
    result = []
    for record in records:
        record_id = require_non_empty(record.get("id"), "dns record id")
        result.append(
            {
                "id": record_id,
                "domain_id": domain_id,
                "name": record.get("name"),
                "value": record.get("value"),
                "type": record.get("type"),
                "priority": record.get("priority"),
                "ttl": record.get("ttl"),
                "created_at": record.get("created_at"),
            }
        )
    return result


@timeit
def load_domains(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoDNSDomainSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def load_records(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoDNSRecordSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def cleanup(
    neo4j_session: neo4j.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    GraphJob.from_node_schema(CivoDNSRecordSchema(), common_job_parameters).run(
        neo4j_session,
    )
    GraphJob.from_node_schema(CivoDNSDomainSchema(), common_job_parameters).run(
        neo4j_session,
    )
