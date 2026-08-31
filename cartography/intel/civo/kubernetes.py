import logging
from typing import Any

import neo4j
import requests

from cartography.client.core.tx import load
from cartography.graph.job import GraphJob
from cartography.intel.civo.util import fan_out_paginated_across_regions
from cartography.intel.civo.util import region_codes_for_feature
from cartography.intel.civo.util import require_non_empty
from cartography.models.civo.kubernetes import CivoKubernetesClusterSchema
from cartography.models.civo.kubernetes import CivoKubernetesInstanceSchema
from cartography.models.civo.kubernetes import CivoKubernetesPoolSchema
from cartography.util import timeit

logger = logging.getLogger(__name__)


@timeit
def sync(
    neo4j_session: neo4j.Session,
    api_session: requests.Session,
    common_job_parameters: dict[str, Any],
) -> None:
    region_codes = region_codes_for_feature(
        common_job_parameters["REGIONS"], "kubernetes"
    )
    clusters = get(
        api_session,
        common_job_parameters["BASE_URL"],
        region_codes,
    )
    transformed_clusters = transform_clusters(clusters)
    pools = transform_pools(clusters)
    instances = transform_instances(clusters)

    load_clusters(
        neo4j_session,
        transformed_clusters,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )
    load_pools(
        neo4j_session,
        pools,
        common_job_parameters["ACCOUNT_ID"],
        common_job_parameters["UPDATE_TAG"],
    )
    load_instances(
        neo4j_session,
        instances,
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
        api_session, f"{base_url}/v2/kubernetes/clusters", region_codes
    )


def transform_clusters(clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Drops kubeconfig - a real credential granting full cluster access - before
    any row is built. installed_applications is flattened to just the names
    of installed marketplace apps (the full per-app version/config detail is
    lower value for a security graph and better modeled separately later).
    """
    result = []
    for cluster in clusters:
        cluster_id = require_non_empty(cluster.get("id"), "cluster id")
        installed_apps = cluster.get("installed_applications") or []
        result.append(
            {
                "id": cluster_id,
                "name": cluster.get("name"),
                "status": cluster.get("status"),
                "region": cluster.get("region"),
                "ready": cluster.get("ready"),
                "version": cluster.get("kubernetes_version") or cluster.get("version"),
                "cluster_type": cluster.get("cluster_type"),
                "num_target_nodes": cluster.get("num_target_nodes"),
                "target_nodes_size": cluster.get("target_nodes_size"),
                "api_endpoint": cluster.get("api_endpoint"),
                "dns_entry": cluster.get("dns_entry"),
                "master_ip": cluster.get("master_ip"),
                "network_id": cluster.get("network_id"),
                "firewall_id": cluster.get("firewall_id"),
                "namespace": cluster.get("namespace"),
                "tags": cluster.get("tags"),
                "cni_plugin": cluster.get("cni_plugin"),
                "ccm_installed": cluster.get("ccm_installed"),
                "volume_type": cluster.get("volume_type"),
                "installed_application_names": [
                    app.get("name")
                    for app in installed_apps
                    if app.get("installed") and app.get("name")
                ],
                "created_at": cluster.get("created_at"),
            }
        )
    return result


def transform_pools(clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for cluster in clusters:
        cluster_id = require_non_empty(cluster.get("id"), "cluster id")
        for pool in cluster.get("pools") or []:
            pool_id = require_non_empty(pool.get("id"), "kubernetes pool id")
            result.append(
                {
                    "id": pool_id,
                    "cluster_id": cluster_id,
                    "count": pool.get("count"),
                    "size": pool.get("size"),
                    "instance_names": pool.get("instance_names"),
                    "public_ip_node_pool": pool.get("public_ip_node_pool"),
                }
            )
    return result


def transform_instances(clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Kubernetes worker nodes are full compute instances (they count against
    the account's instance quota, confirmed live) - previously discarded
    entirely, since transform_pools only read `instance_names` (bare
    strings). Reads each pool's own `instances` list (not the cluster-level
    `instances`, which is just the same objects flattened across every
    pool) so pool_id is captured directly. Drops `initial_password` and
    `civostatsd_token` (real credentials, same fields CivoInstance already
    excludes) and `ssh_key`/`script` (not proven safe just because a k3s
    node's ssh_key is a `-` placeholder today).

    Worker-node objects carry no `region` field of their own (confirmed
    live), but their parent cluster does - propagated from there so
    `_ont_region` can populate, the same pattern already used for
    `CivoLoadBalancerBackend.network_id` inheriting from its load balancer.
    """
    result = []
    for cluster in clusters:
        region = cluster.get("region")
        for pool in cluster.get("pools") or []:
            pool_id = require_non_empty(pool.get("id"), "kubernetes pool id")
            for instance in pool.get("instances") or []:
                instance_id = require_non_empty(
                    instance.get("id"), "kubernetes worker instance id"
                )
                result.append(
                    {
                        "id": instance_id,
                        "hostname": instance.get("hostname"),
                        "size": instance.get("size"),
                        "pool_id": pool_id,
                        "region": instance.get("region") or region,
                        "status": instance.get("status"),
                        "network_id": instance.get("network_id"),
                        "private_ip": instance.get("private_ip"),
                        "public_ip": instance.get("public_ip"),
                        "reverse_dns": instance.get("reverse_dns"),
                        "source_type": instance.get("source_type"),
                        "source_id": instance.get("source_id"),
                        "initial_user": instance.get("initial_user"),
                        "firewall_id": instance.get("firewall_id"),
                        "tags": instance.get("tags"),
                        "cpu_cores": instance.get("cpu_cores"),
                        "ram_mb": instance.get("ram_mb"),
                        "disk_gb": instance.get("disk_gb"),
                        "created_at": instance.get("created_at"),
                    }
                )
    return result


@timeit
def load_clusters(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoKubernetesClusterSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def load_pools(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoKubernetesPoolSchema(),
        data,
        lastupdated=update_tag,
        ACCOUNT_ID=account_id,
    )


@timeit
def load_instances(
    neo4j_session: neo4j.Session,
    data: list[dict[str, Any]],
    account_id: str,
    update_tag: int,
) -> None:
    load(
        neo4j_session,
        CivoKubernetesInstanceSchema(),
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
        CivoKubernetesInstanceSchema(), common_job_parameters
    ).run(neo4j_session)
    GraphJob.from_node_schema(CivoKubernetesPoolSchema(), common_job_parameters).run(
        neo4j_session,
    )
    GraphJob.from_node_schema(CivoKubernetesClusterSchema(), common_job_parameters).run(
        neo4j_session
    )
