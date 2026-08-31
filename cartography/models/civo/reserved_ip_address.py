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
class CivoReservedIPAddressNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef(
        "id",
        description="Civo reserved IP address ID.",
    )
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    name: PropertyRef = PropertyRef(
        "name",
        description="Reserved IP address name.",
    )
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
class CivoReservedIPAddressToInstanceRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoReservedIPAddress)-[:ASSIGNED_TO]->(:CivoInstance)
class CivoReservedIPAddressToInstanceRel(CartographyRelSchema):
    """Connects `CivoReservedIPAddress` to the `CivoInstance` it's assigned to, when
    `assigned_to_type` is `instance`. Only ever one of this and
    `CivoReservedIPAddressToLoadBalancerRel` resolves for a given IP, since Civo's
    `assigned_to` is polymorphic and the transform only ever populates one
    of `instance_id`/`loadbalancer_id`."""

    target_node_label: str = "CivoInstance"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("instance_id")},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "ASSIGNED_TO"
    properties: CivoReservedIPAddressToInstanceRelProperties = (
        CivoReservedIPAddressToInstanceRelProperties()
    )


@dataclass(frozen=True)
class CivoReservedIPAddressToLoadBalancerRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoReservedIPAddress)-[:ASSIGNED_TO]->(:CivoLoadBalancer)
class CivoReservedIPAddressToLoadBalancerRel(CartographyRelSchema):
    """Connects `CivoReservedIPAddress` to the `CivoLoadBalancer` it's assigned to, when
    `assigned_to_type` is `loadbalancer`. See `CivoReservedIPAddressToInstanceRel`."""

    target_node_label: str = "CivoLoadBalancer"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("loadbalancer_id")},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "ASSIGNED_TO"
    properties: CivoReservedIPAddressToLoadBalancerRelProperties = (
        CivoReservedIPAddressToLoadBalancerRelProperties()
    )


@dataclass(frozen=True)
class CivoReservedIPAddressToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoReservedIPAddress)
class CivoReservedIPAddressToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoReservedIPAddress` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoReservedIPAddressToAccountRelProperties = (
        CivoReservedIPAddressToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoReservedIPAddressSchema(CartographyNodeSchema):
    """A Civo reserved (floating) IP address. `assigned_to` is polymorphic
    (an instance or a load balancer) - the transform splits it into
    `instance_id`/`loadbalancer_id` (only one populated per row, per
    `assigned_to_type`), each driving its own typed `ASSIGNED_TO`
    relationship below, alongside the flat id/type/name fields kept for
    display."""

    label: str = "CivoReservedIPAddress"
    properties: CivoReservedIPAddressNodeProperties = (
        CivoReservedIPAddressNodeProperties()
    )
    sub_resource_relationship: CivoReservedIPAddressToAccountRel = (
        CivoReservedIPAddressToAccountRel()
    )
    other_relationships: OtherRelationships = OtherRelationships(
        [
            CivoReservedIPAddressToInstanceRel(),
            CivoReservedIPAddressToLoadBalancerRel(),
        ],
    )
