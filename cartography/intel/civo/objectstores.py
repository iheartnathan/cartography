import logging
from typing import Any

import neo4j
import requests

from cartography.client.core.tx import load
from cartography.graph.job import GraphJob
from cartography.intel.civo.util import fan_out_paginated_across_regions
from cartography.intel.civo.util import region_codes_for_feature
from cartography.intel.civo.util import require_non_empty
from cartography.models.civo.objectstore import CivoObjectStoreCredentialSchema
from cartography.models.civo.objectstore import CivoObjectStoreSchema
from cartography.util import timeit

logger = logging.getLogger(__name__)


@timeit
def sync(
    neo4j_session: neo4j.Session,
    api_session: requests.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    region_codes = region_codes_for_feature(
        common_job_parameters["REGIONS"], "object_store"
    )
    stores = get_stores(
        api_session,
        common_job_parameters["BASE_URL"],
        region_codes,
    )
    credentials = get_credentials(
        api_session,
        common_job_parameters["BASE_URL"],
        region_codes,
    )

    # Credentials load first: CivoObjectStore's HAS_OWNER_CREDENTIAL edge
    # targets CivoObjectStoreCredential, and a relationship matcher only
    # resolves once the target node already exists in the graph.
    load_credentials(
        neo4j_session,
        transform_credentials(credentials),
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )
    load_stores(
        neo4j_session,
        transform_stores(stores),
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )


@timeit
def get_stores(
    api_session: requests.Session,
    base_url: str,
    region_codes: list[str],
) -> list[dict[str, Any]]:
    return fan_out_paginated_across_regions(
        api_session, f"{base_url}/v2/objectstores", region_codes
    )


@timeit
def get_credentials(
    api_session: requests.Session,
    base_url: str,
    region_codes: list[str],
) -> list[dict[str, Any]]:
    return fan_out_paginated_across_regions(
        api_session, f"{base_url}/v2/objectstore/credentials", region_codes
    )


def transform_stores(stores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for store in stores:
        store_id = require_non_empty(store.get("id"), "object store id")
        owner_info = store.get("owner_info") or {}
        result.append(
            {
                "id": store_id,
                "name": store.get("name"),
                "region": store.get("region"),
                # civogo's struct tag says "max_size", but Civo's current
                # REST docs show "max_size_gb" - a real discrepancy between
                # the two sources that needs live-API verification. Reading
                # both keys defensively is safe either way.
                "max_size_gb": store.get("max_size_gb") or store.get("max_size"),
                "endpoint": store.get("objectstore_endpoint"),
                "status": store.get("status"),
                "owner_access_key_id": owner_info.get("access_key_id"),
                "owner_name": owner_info.get("name"),
                "owner_credential_id": owner_info.get("credential_id"),
            }
        )
    return result


def transform_credentials(credentials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Drops secret_access_key_id - a real credential - before any row is built.
    access_key_id is kept: it is not secret by itself (same AWS access-key-id
    vs secret-access-key convention).
    """
    result = []
    for credential in credentials:
        credential_id = require_non_empty(
            credential.get("id"), "object store credential id"
        )
        result.append(
            {
                "id": credential_id,
                "name": credential.get("name"),
                "region": credential.get("region"),
                "access_key_id": credential.get("access_key_id"),
                "max_size_gb": credential.get("max_size_gb"),
                "suspended": credential.get("suspended"),
                "status": credential.get("status"),
            }
        )
    return result


@timeit
def load_stores(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoObjectStoreSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def load_credentials(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoObjectStoreCredentialSchema(),
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
        CivoObjectStoreCredentialSchema(), common_job_parameters
    ).run(neo4j_session)
    GraphJob.from_node_schema(CivoObjectStoreSchema(), common_job_parameters).run(
        neo4j_session,
    )
