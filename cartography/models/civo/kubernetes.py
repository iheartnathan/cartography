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
class CivoKubernetesClusterToNetworkRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoKubernetesCluster)-[:PART_OF_NETWORK]->(:CivoNetwork)
class CivoKubernetesClusterToNetworkRel(CartographyRelSchema):
    """Connects `CivoKubernetesCluster` to the `CivoNetwork` it's on."""

    target_node_label: str = "CivoNetwork"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("network_id")},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "PART_OF_NETWORK"
    properties: CivoKubernetesClusterToNetworkRelProperties = (
        CivoKubernetesClusterToNetworkRelProperties()
    )


@dataclass(frozen=True)
class CivoKubernetesClusterToFirewallRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoKubernetesCluster)-[:PROTECTED_BY]->(:CivoFirewall)
class CivoKubernetesClusterToFirewallRel(CartographyRelSchema):
    """Connects `CivoKubernetesCluster` to the `CivoFirewall` protecting it."""

    target_node_label: str = "CivoFirewall"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("firewall_id")},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "PROTECTED_BY"
    properties: CivoKubernetesClusterToFirewallRelProperties = (
        CivoKubernetesClusterToFirewallRelProperties()
    )


@dataclass(frozen=True)
class CivoKubernetesClusterSchema(CartographyNodeSchema):
    """A Civo managed Kubernetes cluster. Excludes `kubeconfig`, a real
    credential that grants full cluster access.

    `PART_OF_NETWORK` and `PROTECTED_BY` link the cluster to its network
    and firewall when the referenced resources are present in the graph."""

    label: str = "CivoKubernetesCluster"
    properties: CivoKubernetesClusterNodeProperties = (
        CivoKubernetesClusterNodeProperties()
    )
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([COMPUTE_CLUSTER])
    sub_resource_relationship: CivoKubernetesClusterToAccountRel = (
        CivoKubernetesClusterToAccountRel()
    )
    other_relationships: OtherRelationships = OtherRelationships(
        [CivoKubernetesClusterToNetworkRel(), CivoKubernetesClusterToFirewallRel()],
    )


@dataclass(frozen=True)
class CivoKubernetesNodePoolNodeProperties(CartographyNodeProperties):
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
class CivoKubernetesNodePoolToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoKubernetesNodePool)
class CivoKubernetesNodePoolToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoKubernetesNodePool` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoKubernetesNodePoolToAccountRelProperties = (
        CivoKubernetesNodePoolToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoKubernetesNodePoolToClusterRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoKubernetesCluster)-[:HAS_NODE_POOL]->(:CivoKubernetesNodePool)
class CivoKubernetesNodePoolToClusterRel(CartographyRelSchema):
    """Connects `CivoKubernetesCluster` to its `CivoKubernetesNodePool`s."""

    target_node_label: str = "CivoKubernetesCluster"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("cluster_id")},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "HAS_NODE_POOL"
    properties: CivoKubernetesNodePoolToClusterRelProperties = (
        CivoKubernetesNodePoolToClusterRelProperties()
    )


@dataclass(frozen=True)
class CivoKubernetesNodePoolSchema(CartographyNodeSchema):
    """A node pool within a `CivoKubernetesCluster`."""

    label: str = "CivoKubernetesNodePool"
    properties: CivoKubernetesNodePoolNodeProperties = CivoKubernetesNodePoolNodeProperties()
    sub_resource_relationship: CivoKubernetesNodePoolToAccountRel = (
        CivoKubernetesNodePoolToAccountRel()
    )
    other_relationships: OtherRelationships = OtherRelationships(
        [CivoKubernetesNodePoolToClusterRel()],
    )


@dataclass(frozen=True)
class CivoKubernetesWorkerNodeProperties(CartographyNodeProperties):
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
class CivoKubernetesWorkerNodeToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoKubernetesWorkerNode)
class CivoKubernetesWorkerNodeToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoKubernetesWorkerNode` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoKubernetesWorkerNodeToAccountRelProperties = (
        CivoKubernetesWorkerNodeToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoKubernetesWorkerNodeToNodePoolRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoKubernetesNodePool)-[:HAS_WORKER_NODE]->(:CivoKubernetesWorkerNode)
class CivoKubernetesWorkerNodeToNodePoolRel(CartographyRelSchema):
    """Connects `CivoKubernetesNodePool` to its `CivoKubernetesWorkerNode` worker nodes."""

    target_node_label: str = "CivoKubernetesNodePool"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("pool_id")},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "HAS_WORKER_NODE"
    properties: CivoKubernetesWorkerNodeToNodePoolRelProperties = (
        CivoKubernetesWorkerNodeToNodePoolRelProperties()
    )


@dataclass(frozen=True)
class CivoKubernetesWorkerNodeToNetworkRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoKubernetesWorkerNode)-[:PART_OF_NETWORK]->(:CivoNetwork)
class CivoKubernetesWorkerNodeToNetworkRel(CartographyRelSchema):
    """Connects `CivoKubernetesWorkerNode` to the `CivoNetwork` it's on."""

    target_node_label: str = "CivoNetwork"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("network_id")},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "PART_OF_NETWORK"
    properties: CivoKubernetesWorkerNodeToNetworkRelProperties = (
        CivoKubernetesWorkerNodeToNetworkRelProperties()
    )


@dataclass(frozen=True)
class CivoKubernetesWorkerNodeToFirewallRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoKubernetesWorkerNode)-[:PROTECTED_BY]->(:CivoFirewall)
class CivoKubernetesWorkerNodeToFirewallRel(CartographyRelSchema):
    """Connects `CivoKubernetesWorkerNode` to the `CivoFirewall` protecting it."""

    target_node_label: str = "CivoFirewall"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("firewall_id")},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "PROTECTED_BY"
    properties: CivoKubernetesWorkerNodeToFirewallRelProperties = (
        CivoKubernetesWorkerNodeToFirewallRelProperties()
    )


@dataclass(frozen=True)
class CivoKubernetesWorkerNodeSchema(CartographyNodeSchema):
    """A worker node (compute instance) within a `CivoKubernetesNodePool`. Excludes
    several fields returned by the API that are real credentials: `initial_password`,
    `civostatsd_token` (both real credentials), `ssh_key` (a placeholder on
    k3s nodes today, but not one to trust as safe), and `script`.

    `PART_OF_NETWORK` and `PROTECTED_BY` link the worker node to its network
    and firewall when the referenced resources are present in the graph."""

    label: str = "CivoKubernetesWorkerNode"
    properties: CivoKubernetesWorkerNodeProperties = (
        CivoKubernetesWorkerNodeProperties()
    )
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([COMPUTE_INSTANCE])
    sub_resource_relationship: CivoKubernetesWorkerNodeToAccountRel = (
        CivoKubernetesWorkerNodeToAccountRel()
    )
    other_relationships: OtherRelationships = OtherRelationships(
        [
            CivoKubernetesWorkerNodeToNodePoolRel(),
            CivoKubernetesWorkerNodeToNetworkRel(),
            CivoKubernetesWorkerNodeToFirewallRel(),
        ],
    )
