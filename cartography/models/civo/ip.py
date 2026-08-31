from dataclasses import dataclass

from cartography.models.core.common import PropertyRef
from cartography.models.core.nodes import CartographyNodeProperties
from cartography.models.core.nodes import CartographyNodeSchema
from cartography.models.core.relationships import CartographyRelProperties
from cartography.models.core.relationships import CartographyRelSchema
from cartography.models.core.relationships import LinkDirection
from cartography.models.core.relationships import make_target_node_matcher
from cartography.models.core.relationships import OtherRelationships
from cartography.models.core.relationships import TargetNodeMatcher


@dataclass(frozen=True)
class CivoIPNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo reserved IP ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    name: PropertyRef = PropertyRef("name", description="Reserved IP name.")
    region: PropertyRef = PropertyRef(
        "region",
        extra_index=True,
        description="Civo region this IP was queried from (Civo's IP API"
        " exposes no native region field, so this reflects the query, not"
        " necessarily a field on the raw resource).",
    )
    ip: PropertyRef = PropertyRef(
        "ip", extra_index=True, description="The IP address itself."
    )
    assigned_to_id: PropertyRef = PropertyRef(
        "assigned_to_id",
        description="ID of the resource this IP is assigned to, if any.",
    )
    assigned_to_type: PropertyRef = PropertyRef(
        "assigned_to_type",
        description="Type of the resource this IP is assigned to: `instance` or `loadbalancer`.",
    )
    assigned_to_name: PropertyRef = PropertyRef(
        "assigned_to_name", description="Name of the resource this IP is assigned to."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoIPToLoadBalancerRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoIP)-[:ASSIGNED_TO]->(:CivoLoadBalancer)
class CivoIPToLoadBalancerRel(CartographyRelSchema):
    """Connects `CivoIP` to the `CivoLoadBalancer` it's assigned to, when
    `assigned_to_type` is `loadbalancer`. Civo's `assigned_to` is also
    polymorphic to `instance` - not wired as a `CivoInstance` relationship
    here, since `CivoInstance` is owned by the separate Compute PR and
    doesn't exist on this branch. That edge is added by the
    add-civo-cross-resource-relationships PR, opened once every Civo
    resource PR has merged."""

    target_node_label: str = "CivoLoadBalancer"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("loadbalancer_id")},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "ASSIGNED_TO"
    properties: CivoIPToLoadBalancerRelProperties = CivoIPToLoadBalancerRelProperties()


@dataclass(frozen=True)
class CivoIPToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoIP)
class CivoIPToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoIP` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoIPToAccountRelProperties = CivoIPToAccountRelProperties()


@dataclass(frozen=True)
class CivoIPSchema(CartographyNodeSchema):
    """A Civo reserved (floating) IP address. `assigned_to` is polymorphic
    (an instance or a load balancer) - the transform splits it into
    `instance_id`/`loadbalancer_id` (only one populated per row, per
    `assigned_to_type`), each driving its own typed `ASSIGNED_TO`
    relationship below, alongside the flat id/type/name fields kept for
    display."""

    label: str = "CivoIP"
    properties: CivoIPNodeProperties = CivoIPNodeProperties()
    sub_resource_relationship: CivoIPToAccountRel = CivoIPToAccountRel()
    other_relationships: OtherRelationships = OtherRelationships(
        [CivoIPToLoadBalancerRel()],
    )
