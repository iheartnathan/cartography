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
from cartography.models.ontology.labels import LOAD_BALANCER


@dataclass(frozen=True)
class CivoLoadBalancerNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo load balancer ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    name: PropertyRef = PropertyRef(
        "name", extra_index=True, description="Load balancer name."
    )
    region: PropertyRef = PropertyRef(
        "region", extra_index=True, description="Civo region."
    )
    algorithm: PropertyRef = PropertyRef(
        "algorithm", description="Load balancing algorithm."
    )
    public_ip: PropertyRef = PropertyRef(
        "public_ip", extra_index=True, description="Public IP address."
    )
    private_ip: PropertyRef = PropertyRef(
        "private_ip", description="Private IP address."
    )
    state: PropertyRef = PropertyRef("state", description="Load balancer state.")
    network_id: PropertyRef = PropertyRef(
        "network_id", description="ID of the network this load balancer is on."
    )
    firewall_id: PropertyRef = PropertyRef(
        "firewall_id", description="ID of the firewall protecting this load balancer."
    )
    cluster_id: PropertyRef = PropertyRef(
        "cluster_id",
        description="ID of the Kubernetes cluster this load balancer serves, if any.",
    )
    external_traffic_policy: PropertyRef = PropertyRef(
        "external_traffic_policy", description="External traffic policy."
    )
    # Civo load balancers can route to backends two ways: an explicit list of
    # IP:port pairs (modeled as CivoLoadBalancerBackend nodes below), or a
    # dynamic tag/name-based instance pool selector (modeled as
    # CivoLoadBalancerInstancePool nodes below) - neither is captured here,
    # since each pool has its own routing configuration (protocol/ports/
    # health check) that a flattened property on the load balancer would lose.
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoLoadBalancerToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoLoadBalancer)
class CivoLoadBalancerToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoLoadBalancer` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoLoadBalancerToAccountRelProperties = (
        CivoLoadBalancerToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoLoadBalancerSchema(CartographyNodeSchema):
    """A Civo load balancer.

    `firewall_id`/`cluster_id`/`network_id` are kept as plain properties
    only in this PR - not wired as `PROTECTED_BY`/`EXPOSES`/
    `PART_OF_NETWORK` relationships, since `CivoFirewall`/
    `CivoKubernetesCluster`/`CivoNetwork` are owned by the separate
    Networking/Kubernetes PRs and don't exist on this branch. Those edges
    are added by the add-civo-cross-resource-relationships PR, opened
    once every Civo resource PR has merged - a relationship must not
    target a node schema that doesn't exist yet on this PR's own
    branch."""

    label: str = "CivoLoadBalancer"
    properties: CivoLoadBalancerNodeProperties = CivoLoadBalancerNodeProperties()
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([LOAD_BALANCER])
    sub_resource_relationship: CivoLoadBalancerToAccountRel = (
        CivoLoadBalancerToAccountRel()
    )


@dataclass(frozen=True)
class CivoLoadBalancerBackendNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef(
        "id",
        description="Synthetic"
        " `<loadbalancer_id>/<ip>/<protocol>/<source_port>/<target_port>`."
        " Civo's Load Balancer API defines a backend by its full"
        " protocol/source_port/target_port tuple, not just ip+source_port -"
        " e.g. a TCP backend on source port 53 and a UDP backend on the same"
        " source port 53 are both valid and distinct. An id built from only"
        " `<ip>/<source_port>` would collide the two onto one node, silently"
        " dropping one backend's routing configuration.",
    )
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    loadbalancer_id: PropertyRef = PropertyRef(
        "loadbalancer_id", description="ID of the parent load balancer."
    )
    network_id: PropertyRef = PropertyRef(
        "network_id",
        description="ID of the network the parent load balancer is on"
        " (Civo backends carry no network field of their own; inherited from"
        " the load balancer to scope the ROUTES_TO match to the same"
        " network, since private IPs can repeat across networks/accounts).",
    )
    ip: PropertyRef = PropertyRef(
        "ip", extra_index=True, description="Backend target IP address."
    )
    protocol: PropertyRef = PropertyRef("protocol", description="Backend protocol.")
    source_port: PropertyRef = PropertyRef(
        "source_port", description="Port on the load balancer."
    )
    target_port: PropertyRef = PropertyRef(
        "target_port", description="Port on the backend target."
    )
    health_check_port: PropertyRef = PropertyRef(
        "health_check_port", description="Port used for health checks, if different."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoLoadBalancerBackendToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoLoadBalancerBackend)
class CivoLoadBalancerBackendToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoLoadBalancerBackend` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoLoadBalancerBackendToAccountRelProperties = (
        CivoLoadBalancerBackendToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoLoadBalancerBackendToLoadBalancerRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoLoadBalancer)-[:HAS_BACKEND]->(:CivoLoadBalancerBackend)
class CivoLoadBalancerBackendToLoadBalancerRel(CartographyRelSchema):
    """Connects `CivoLoadBalancer` to its `CivoLoadBalancerBackend`s."""

    target_node_label: str = "CivoLoadBalancer"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("loadbalancer_id")},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "HAS_BACKEND"
    properties: CivoLoadBalancerBackendToLoadBalancerRelProperties = (
        CivoLoadBalancerBackendToLoadBalancerRelProperties()
    )


@dataclass(frozen=True)
class CivoLoadBalancerBackendSchema(CartographyNodeSchema):
    """A single backend target (IP:port pair) on a `CivoLoadBalancer`.

    Matched by private IP scoped to the same network and account, `ROUTES_TO`
    a `CivoInstance` in the reference combined implementation - not wired
    here, since `CivoInstance` is owned by the separate Compute PR and
    doesn't exist on this branch. That edge is added by the
    add-civo-cross-resource-relationships PR, opened once every Civo
    resource PR has merged."""

    label: str = "CivoLoadBalancerBackend"
    properties: CivoLoadBalancerBackendNodeProperties = (
        CivoLoadBalancerBackendNodeProperties()
    )
    sub_resource_relationship: CivoLoadBalancerBackendToAccountRel = (
        CivoLoadBalancerBackendToAccountRel()
    )
    other_relationships: OtherRelationships = OtherRelationships(
        [
            CivoLoadBalancerBackendToLoadBalancerRel(),
        ],
    )


@dataclass(frozen=True)
class CivoLoadBalancerInstancePoolNodeProperties(CartographyNodeProperties):
    """A dynamic tag/name-based backend selector on a `CivoLoadBalancer`
    (Civo's `InstancePool`, civogo `loadbalancer.go`) - not a concrete
    resolved list of instances (Civo itself resolves the selector against
    matching instances at traffic time), so no relationship to `CivoInstance`
    is modeled; each pool's own routing configuration (protocol/ports/health
    check) is preserved here rather than flattened onto the load balancer."""

    id: PropertyRef = PropertyRef(
        "id",
        description="Synthetic `<loadbalancer_id>/<protocol>/<source_port>`"
        " (Civo instance pools have no id of their own; a list index isn't"
        " used since Civo's response order isn't documented as stable."
        " Civo's provider contract doesn't state whether uniqueness on a"
        " load balancer is scoped to source_port alone or to the"
        " (protocol, source_port) pair, so the more permissive pair is used"
        " - the transform still raises if two pools ever compute the same"
        " id, since neither scoping is formally guaranteed).",
    )
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    loadbalancer_id: PropertyRef = PropertyRef(
        "loadbalancer_id", description="ID of the parent load balancer."
    )
    tags: PropertyRef = PropertyRef(
        "tags", description="Tags used to dynamically select backend instances."
    )
    names: PropertyRef = PropertyRef(
        "names", description="Names used to dynamically select backend instances."
    )
    protocol: PropertyRef = PropertyRef("protocol", description="Backend protocol.")
    source_port: PropertyRef = PropertyRef(
        "source_port", description="Port on the load balancer."
    )
    target_port: PropertyRef = PropertyRef(
        "target_port", description="Port on each selected backend instance."
    )
    health_check_port: PropertyRef = PropertyRef(
        "health_check_port", description="Port used for health checks."
    )
    health_check_path: PropertyRef = PropertyRef(
        "health_check_path", description="HTTP path used for health checks."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoLoadBalancerInstancePoolToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoLoadBalancerInstancePool)
class CivoLoadBalancerInstancePoolToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoLoadBalancerInstancePool` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoLoadBalancerInstancePoolToAccountRelProperties = (
        CivoLoadBalancerInstancePoolToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoLoadBalancerInstancePoolToLoadBalancerRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoLoadBalancer)-[:HAS_INSTANCE_POOL]->(:CivoLoadBalancerInstancePool)
class CivoLoadBalancerInstancePoolToLoadBalancerRel(CartographyRelSchema):
    """Connects `CivoLoadBalancer` to its `CivoLoadBalancerInstancePool`s."""

    target_node_label: str = "CivoLoadBalancer"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("loadbalancer_id")},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "HAS_INSTANCE_POOL"
    properties: CivoLoadBalancerInstancePoolToLoadBalancerRelProperties = (
        CivoLoadBalancerInstancePoolToLoadBalancerRelProperties()
    )


@dataclass(frozen=True)
class CivoLoadBalancerInstancePoolSchema(CartographyNodeSchema):
    """A dynamic tag/name-based backend selector on a `CivoLoadBalancer`."""

    label: str = "CivoLoadBalancerInstancePool"
    properties: CivoLoadBalancerInstancePoolNodeProperties = (
        CivoLoadBalancerInstancePoolNodeProperties()
    )
    sub_resource_relationship: CivoLoadBalancerInstancePoolToAccountRel = (
        CivoLoadBalancerInstancePoolToAccountRel()
    )
    other_relationships: OtherRelationships = OtherRelationships(
        [CivoLoadBalancerInstancePoolToLoadBalancerRel()],
    )
