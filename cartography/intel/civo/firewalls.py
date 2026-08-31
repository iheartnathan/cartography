import logging
from typing import Any

import neo4j
import requests

from cartography.client.core.tx import load
from cartography.graph.job import GraphJob
from cartography.intel.civo.util import get_json_array
from cartography.intel.civo.util import region_codes_for_feature
from cartography.intel.civo.util import require_non_empty
from cartography.models.civo.firewall import CivoFirewallRuleSchema
from cartography.models.civo.firewall import CivoFirewallSchema
from cartography.util import timeit

logger = logging.getLogger(__name__)


@timeit
def sync(
    neo4j_session: neo4j.Session,
    api_session: requests.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    region_codes = region_codes_for_feature(common_job_parameters["REGIONS"], None)
    firewalls_by_region = get(
        api_session,
        common_job_parameters["BASE_URL"],
        region_codes,
    )
    transformed_firewalls = transform_firewalls(firewalls_by_region)
    rules = get_rules(
        api_session, common_job_parameters["BASE_URL"], firewalls_by_region
    )

    load_firewalls(
        neo4j_session,
        transformed_firewalls,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )
    load_rules(
        neo4j_session,
        rules,
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
    Firewalls are region-scoped (optional `region` param, defaults to a
    random region if omitted - confirmed against Civo's API docs), so this
    fans the list out across every region. Returns (firewall, region_code)
    pairs, deduplicated by firewall id, rather than a bare list: the region
    each firewall came from is needed again immediately after to fetch that
    firewall's rules from the same region.
    """
    firewalls_by_region: list[tuple[dict[str, Any], str]] = []
    seen_ids: set[Any] = set()
    for region_code in region_codes:
        firewalls = get_json_array(
            api_session, f"{base_url}/v2/firewalls", params={"region": region_code}
        )
        for firewall in firewalls:
            firewall_id = firewall.get("id")
            if firewall_id is not None:
                if firewall_id in seen_ids:
                    continue
                seen_ids.add(firewall_id)
            firewalls_by_region.append((firewall, region_code))
    return firewalls_by_region


@timeit
def get_rules(
    api_session: requests.Session,
    base_url: str,
    firewalls_by_region: list[tuple[dict[str, Any], str]],
) -> list[dict[str, Any]]:
    all_rules: list[dict[str, Any]] = []
    for firewall, region_code in firewalls_by_region:
        firewall_id = firewall["id"]
        rules = get_json_array(
            api_session,
            f"{base_url}/v2/firewalls/{firewall_id}/rules",
            params={"region": region_code},
        )
        all_rules.extend(transform_rules(rules, firewall_id))
    return all_rules


def transform_firewalls(
    firewalls_by_region: list[tuple[dict[str, Any], str]],
) -> list[dict[str, Any]]:
    result = []
    for firewall, region_code in firewalls_by_region:
        firewall_id = require_non_empty(firewall.get("id"), "firewall id")
        result.append(
            {
                "id": firewall_id,
                "name": firewall.get("name"),
                "region": firewall.get("region") or region_code,
                "network_id": firewall.get("network_id"),
                "rules_count": firewall.get("rules_count"),
                "instance_count": firewall.get("instance_count"),
                "cluster_count": firewall.get("cluster_count"),
                "loadbalancer_count": firewall.get("loadbalancer_count"),
            }
        )
    return result


def transform_rules(
    rules: list[dict[str, Any]], firewall_id: str
) -> list[dict[str, Any]]:
    result = []
    for rule in rules:
        rule_id = require_non_empty(rule.get("id"), "firewall rule id")
        result.append(
            {
                "id": rule_id,
                "firewall_id": firewall_id,
                "protocol": rule.get("protocol"),
                "start_port": rule.get("start_port"),
                "end_port": rule.get("end_port"),
                "cidr": rule.get("cidr"),
                "direction": rule.get("direction"),
                "action": rule.get("action"),
                "label": rule.get("label"),
            }
        )
    return result


@timeit
def load_firewalls(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoFirewallSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def load_rules(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoFirewallRuleSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def cleanup(
    neo4j_session: neo4j.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    GraphJob.from_node_schema(CivoFirewallRuleSchema(), common_job_parameters).run(
        neo4j_session,
    )
    GraphJob.from_node_schema(CivoFirewallSchema(), common_job_parameters).run(
        neo4j_session,
    )
