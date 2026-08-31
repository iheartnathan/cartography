from dataclasses import dataclass

from cartography.models.core.common import PropertyRef
from cartography.models.core.nodes import CartographyNodeProperties
from cartography.models.core.nodes import CartographyNodeSchema
from cartography.models.core.nodes import ExtraNodeLabels
from cartography.models.core.relationships import CartographyRelProperties
from cartography.models.core.relationships import CartographyRelSchema
from cartography.models.core.relationships import LinkDirection
from cartography.models.core.relationships import make_target_node_matcher
from cartography.models.core.relationships import OtherRelationships
from cartography.models.core.relationships import TargetNodeMatcher
from cartography.models.ontology.labels import COMPUTE_CLUSTER
from cartography.models.ontology.labels import COMPUTE_INSTANCE


@dataclass(frozen=True)
class CivoKubernetesClusterNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo Kubernetes cluster ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    name: PropertyRef = PropertyRef(
        "name", extra_index=True, description="Cluster name."
    )
    status: PropertyRef = PropertyRef("status", description="Cluster status.")
    region: PropertyRef = PropertyRef(
        "region", extra_index=True, description="Civo region."
    )
    ready: PropertyRef = PropertyRef(
        "ready", description="Whether the cluster is ready."
    )
    version: PropertyRef = PropertyRef(
        "version", description="Kubernetes version, e.g. `1.30.5-k3s1`."
    )
    cluster_type: PropertyRef = PropertyRef(
        "cluster_type", description="Cluster type (e.g. `k3s`, `talos`)."
    )
    num_target_nodes: PropertyRef = PropertyRef(
        "num_target_nodes", description="Target node count."
    )
    target_nodes_size: PropertyRef = PropertyRef(
        "target_nodes_size", description="Target node instance size."
    )
    api_endpoint: PropertyRef = PropertyRef(
        "api_endpoint", description="Kubernetes API server endpoint."
    )
    dns_entry: PropertyRef = PropertyRef(
        "dns_entry", description="DNS domain for cluster access."
    )
    master_ip: PropertyRef = PropertyRef(
        "master_ip", description="Control plane IP address."
    )
    network_id: PropertyRef = PropertyRef(
        "network_id", description="ID of the network this cluster is on."
    )
    firewall_id: PropertyRef = PropertyRef(
        "firewall_id", description="ID of the firewall protecting this cluster."
    )
    namespace: PropertyRef = PropertyRef(
        "namespace", description="Civo-internal namespace identifier."
    )
    tags: PropertyRef = PropertyRef("tags", description="User-defined tags.")
    cni_plugin: PropertyRef = PropertyRef(
        "cni_plugin", description="CNI plugin in use."
    )
    ccm_installed: PropertyRef = PropertyRef(
        "ccm_installed",
        description="Whether the cloud controller manager is installed.",
    )
    volume_type: PropertyRef = PropertyRef(
        "volume_type", description="Default volume type for this cluster."
    )
    installed_application_names: PropertyRef = PropertyRef(
        "installed_application_names",
        description="Names of marketplace applications installed on this cluster.",
    )
    created_at: PropertyRef = PropertyRef(
        "created_at", description="Creation timestamp."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoKubernetesClusterToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoKubernetesCluster)
class CivoKubernetesClusterToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoKubernetesCluster` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoKubernetesClusterToAccountRelProperties = (
        CivoKubernetesClusterToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoKubernetesClusterSchema(CartographyNodeSchema):
    """A Civo managed Kubernetes cluster. Excludes `kubeconfig`, a real
    credential that grants full cluster access.

    `network_id`/`firewall_id` are kept as plain properties only in this PR -
    not wired as `PART_OF_NETWORK`/`PROTECTED_BY` relationships, since
    `CivoNetwork`/`CivoFirewall` are owned by the separate Networking PR and
    don't exist on this branch. Those edges are added by the
    add-civo-cross-resource-relationships PR, opened once every Civo
    resource PR has merged - a relationship must not target a node schema
    that doesn't exist yet on this PR's own branch."""

    label: str = "CivoKubernetesCluster"
    properties: CivoKubernetesClusterNodeProperties = (
        CivoKubernetesClusterNodeProperties()
    )
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([COMPUTE_CLUSTER])
    sub_resource_relationship: CivoKubernetesClusterToAccountRel = (
        CivoKubernetesClusterToAccountRel()
    )


@dataclass(frozen=True)
class CivoKubernetesPoolNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo Kubernetes node pool ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    cluster_id: PropertyRef = PropertyRef(
        "cluster_id", description="ID of the parent cluster."
    )
    count: PropertyRef = PropertyRef("count", description="Number of nodes.")
    size: PropertyRef = PropertyRef("size", description="Node instance size.")
    instance_names: PropertyRef = PropertyRef(
        "instance_names", description="Names of the instances in this pool."
    )
    public_ip_node_pool: PropertyRef = PropertyRef(
        "public_ip_node_pool", description="Whether nodes in this pool get a public IP."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoKubernetesPoolToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoKubernetesPool)
class CivoKubernetesPoolToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoKubernetesPool` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoKubernetesPoolToAccountRelProperties = (
        CivoKubernetesPoolToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoKubernetesPoolToClusterRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoKubernetesCluster)-[:HAS_POOL]->(:CivoKubernetesPool)
class CivoKubernetesPoolToClusterRel(CartographyRelSchema):
    """Connects `CivoKubernetesCluster` to its `CivoKubernetesPool`s."""

    target_node_label: str = "CivoKubernetesCluster"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("cluster_id")},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "HAS_POOL"
    properties: CivoKubernetesPoolToClusterRelProperties = (
        CivoKubernetesPoolToClusterRelProperties()
    )


@dataclass(frozen=True)
class CivoKubernetesPoolSchema(CartographyNodeSchema):
    """A node pool within a `CivoKubernetesCluster`."""

    label: str = "CivoKubernetesPool"
    properties: CivoKubernetesPoolNodeProperties = CivoKubernetesPoolNodeProperties()
    sub_resource_relationship: CivoKubernetesPoolToAccountRel = (
        CivoKubernetesPoolToAccountRel()
    )
    other_relationships: OtherRelationships = OtherRelationships(
        [CivoKubernetesPoolToClusterRel()],
    )


@dataclass(frozen=True)
class CivoKubernetesInstanceNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo Kubernetes worker node ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    hostname: PropertyRef = PropertyRef(
        "hostname", extra_index=True, description="Worker node hostname."
    )
    size: PropertyRef = PropertyRef("size", description="Node instance size.")
    region: PropertyRef = PropertyRef(
        "region",
        extra_index=True,
        description="Civo region this worker node is in (inherited from its"
        " parent cluster - worker-node objects carry no region field of"
        " their own).",
    )
    pool_id: PropertyRef = PropertyRef(
        "pool_id", description="ID of the parent node pool."
    )
    status: PropertyRef = PropertyRef("status", description="Worker node status.")
    network_id: PropertyRef = PropertyRef(
        "network_id", description="ID of the private network the node is on."
    )
    private_ip: PropertyRef = PropertyRef(
        "private_ip", description="Private IP address."
    )
    public_ip: PropertyRef = PropertyRef(
        "public_ip", extra_index=True, description="Public IP address."
    )
    reverse_dns: PropertyRef = PropertyRef(
        "reverse_dns", description="Reverse DNS hostname."
    )
    source_type: PropertyRef = PropertyRef(
        "source_type", description="Disk image source type."
    )
    source_id: PropertyRef = PropertyRef(
        "source_id", description="Disk image source ID (the k3s/Kubernetes version)."
    )
    initial_user: PropertyRef = PropertyRef(
        "initial_user", description="Default login username."
    )
    firewall_id: PropertyRef = PropertyRef(
        "firewall_id", description="ID of the firewall protecting this node."
    )
    tags: PropertyRef = PropertyRef("tags", description="User-defined tags.")
    cpu_cores: PropertyRef = PropertyRef("cpu_cores", description="Number of vCPUs.")
    ram_mb: PropertyRef = PropertyRef("ram_mb", description="RAM in megabytes.")
    disk_gb: PropertyRef = PropertyRef(
        "disk_gb", description="Root disk size in gigabytes."
    )
    created_at: PropertyRef = PropertyRef(
        "created_at", description="Creation timestamp."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoKubernetesInstanceToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoKubernetesInstance)
class CivoKubernetesInstanceToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoKubernetesInstance` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoKubernetesInstanceToAccountRelProperties = (
        CivoKubernetesInstanceToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoKubernetesInstanceToPoolRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoKubernetesPool)-[:HAS_WORKER_INSTANCE]->(:CivoKubernetesInstance)
class CivoKubernetesInstanceToPoolRel(CartographyRelSchema):
    """Connects `CivoKubernetesPool` to its `CivoKubernetesInstance` worker nodes."""

    target_node_label: str = "CivoKubernetesPool"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("pool_id")},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "HAS_WORKER_INSTANCE"
    properties: CivoKubernetesInstanceToPoolRelProperties = (
        CivoKubernetesInstanceToPoolRelProperties()
    )


@dataclass(frozen=True)
class CivoKubernetesInstanceSchema(CartographyNodeSchema):
    """A worker node (compute instance) within a `CivoKubernetesPool`. Excludes
    several fields returned by the API that are real credentials: `initial_password`,
    `civostatsd_token` (both real credentials), `ssh_key` (a placeholder on
    k3s nodes today, but not one to trust as safe), and `script`.

    `network_id`/`firewall_id` are kept as plain properties only in this PR -
    not wired as `PART_OF_NETWORK`/`PROTECTED_BY` relationships, since
    `CivoNetwork`/`CivoFirewall` are owned by the separate Networking PR and
    don't exist on this branch. Those edges are added by the
    add-civo-cross-resource-relationships PR, opened once every Civo
    resource PR has merged - a relationship must not target a node schema
    that doesn't exist yet on this PR's own branch."""

    label: str = "CivoKubernetesInstance"
    properties: CivoKubernetesInstanceNodeProperties = (
        CivoKubernetesInstanceNodeProperties()
    )
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([COMPUTE_INSTANCE])
    sub_resource_relationship: CivoKubernetesInstanceToAccountRel = (
        CivoKubernetesInstanceToAccountRel()
    )
    other_relationships: OtherRelationships = OtherRelationships(
        [
            CivoKubernetesInstanceToPoolRel(),
        ],
    )
