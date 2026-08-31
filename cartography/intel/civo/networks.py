import logging
from typing import Any

import neo4j
import requests

from cartography.client.core.tx import load
from cartography.graph.job import GraphJob
from cartography.intel.civo.util import get_json_array
from cartography.intel.civo.util import region_codes_for_feature
from cartography.intel.civo.util import require_non_empty
from cartography.models.civo.network import CivoNetworkSchema
from cartography.models.civo.network import CivoSubnetSchema
from cartography.util import timeit

logger = logging.getLogger(__name__)


@timeit
def sync(
    neo4j_session: neo4j.Session,
    api_session: requests.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    region_codes = region_codes_for_feature(common_job_parameters["REGIONS"], None)
    networks_by_region = get(
        api_session,
        common_job_parameters["BASE_URL"],
        region_codes,
    )
    transformed_networks = transform_networks(networks_by_region)
    subnets = get_subnets(
        api_session, common_job_parameters["BASE_URL"], networks_by_region
    )

    load_networks(
        neo4j_session,
        transformed_networks,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )
    load_subnets(
        neo4j_session,
        subnets,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )


@timeit
def get(
    api_session: requests.Session,
    base_url: str,
    region_codes: list[str],
) -> list[tuple[dict[str, Any], str]]:
    """
    Networks are region-scoped (optional `region` param, defaults to a
    random region if omitted - confirmed against Civo's API docs), so this
    fans the list out across every region. Returns (network, region_code)
    pairs, deduplicated by network id: the region each network came from is
    needed again immediately after to fetch that network's subnets from the
    same region.
    """
    networks_by_region: list[tuple[dict[str, Any], str]] = []
    seen_ids: set[Any] = set()
    for region_code in region_codes:
        networks = get_json_array(
            api_session, f"{base_url}/v2/networks", params={"region": region_code}
        )
        for network in networks:
            network_id = network.get("id")
            if network_id is not None:
                if network_id in seen_ids:
                    continue
                seen_ids.add(network_id)
            networks_by_region.append((network, region_code))
    return networks_by_region


@timeit
def get_subnets(
    api_session: requests.Session,
    base_url: str,
    networks_by_region: list[tuple[dict[str, Any], str]],
) -> list[dict[str, Any]]:
    all_subnets: list[dict[str, Any]] = []
    for network, region_code in networks_by_region:
        network_id = require_non_empty(network.get("id"), "network id")
        subnets = get_json_array(
            api_session,
            f"{base_url}/v2/networks/{network_id}/subnets",
            params={"region": region_code},
        )
        all_subnets.extend(transform_subnets(subnets, network_id))
    return all_subnets


def transform_networks(
    networks_by_region: list[tuple[dict[str, Any], str]],
) -> list[dict[str, Any]]:
    result = []
    for network, region_code in networks_by_region:
        network_id = require_non_empty(network.get("id"), "network id")
        result.append(
            {
                "id": network_id,
                "name": network.get("name"),
                "region": network.get("region") or region_code,
                "label": network.get("label"),
                "default": network.get("default"),
                "status": network.get("status"),
                "cidr": network.get("cidr"),
                "cidr_v6": network.get("cidr_v6"),
                "ipv4_enabled": network.get("ipv4_enabled"),
                "ipv6_enabled": network.get("ipv6_enabled"),
                "vlan_id": network.get("vlan_id"),
            }
        )
    return result


def transform_subnets(
    subnets: list[dict[str, Any]], network_id: str
) -> list[dict[str, Any]]:
    result = []
    for subnet in subnets:
        subnet_id = require_non_empty(subnet.get("id"), "subnet id")
        result.append(
            {
                "id": subnet_id,
                "name": subnet.get("name"),
                "network_id": network_id,
                "subnet_size": subnet.get("subnet_size"),
                "status": subnet.get("status"),
            }
        )
    return result


@timeit
def load_networks(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoNetworkSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def load_subnets(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoSubnetSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def cleanup(
    neo4j_session: neo4j.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    GraphJob.from_node_schema(CivoSubnetSchema(), common_job_parameters).run(
        neo4j_session,
    )
    GraphJob.from_node_schema(CivoNetworkSchema(), common_job_parameters).run(
        neo4j_session,
    )
