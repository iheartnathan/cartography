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
from cartography.models.ontology.labels import SUBNET
from cartography.models.ontology.labels import VIRTUAL_NETWORK


@dataclass(frozen=True)
class CivoNetworkNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo network ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    name: PropertyRef = PropertyRef("name", description="Network name.")
    region: PropertyRef = PropertyRef(
        "region",
        extra_index=True,
        description="Civo region this network was queried from (Civo's Network"
        " API exposes no native region field, so this reflects the query, not"
        " necessarily a field on the raw resource).",
    )
    label: PropertyRef = PropertyRef(
        "label", extra_index=True, description="User-assigned network label."
    )
    default: PropertyRef = PropertyRef(
        "default", description="Whether this is the account's default network."
    )
    status: PropertyRef = PropertyRef("status", description="Network status.")
    cidr: PropertyRef = PropertyRef("cidr", description="IPv4 CIDR block.")
    cidr_v6: PropertyRef = PropertyRef("cidr_v6", description="IPv6 CIDR block.")
    ipv4_enabled: PropertyRef = PropertyRef(
        "ipv4_enabled", description="Whether IPv4 is enabled."
    )
    ipv6_enabled: PropertyRef = PropertyRef(
        "ipv6_enabled", description="Whether IPv6 is enabled."
    )
    vlan_id: PropertyRef = PropertyRef(
        "vlan_id", description="VLAN ID, for VLAN-connected networks."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoNetworkToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoNetwork)
class CivoNetworkToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoNetwork` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoNetworkToAccountRelProperties = CivoNetworkToAccountRelProperties()


@dataclass(frozen=True)
class CivoNetworkSchema(CartographyNodeSchema):
    """A Civo private network (VPC)."""

    label: str = "CivoNetwork"
    properties: CivoNetworkNodeProperties = CivoNetworkNodeProperties()
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([VIRTUAL_NETWORK])
    sub_resource_relationship: CivoNetworkToAccountRel = CivoNetworkToAccountRel()


@dataclass(frozen=True)
class CivoSubnetNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo subnet ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    name: PropertyRef = PropertyRef("name", description="Subnet name.")
    network_id: PropertyRef = PropertyRef(
        "network_id", description="ID of the parent network."
    )
    subnet_size: PropertyRef = PropertyRef(
        "subnet_size", description="Size of the subnet."
    )
    status: PropertyRef = PropertyRef("status", description="Subnet status.")
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoSubnetToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoSubnet)
class CivoSubnetToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoSubnet` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoSubnetToAccountRelProperties = CivoSubnetToAccountRelProperties()


@dataclass(frozen=True)
class CivoSubnetToNetworkRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoNetwork)-[:HAS_SUBNET]->(:CivoSubnet)
class CivoSubnetToNetworkRel(CartographyRelSchema):
    """Connects `CivoNetwork` to its `CivoSubnet`s."""

    target_node_label: str = "CivoNetwork"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("network_id")},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "HAS_SUBNET"
    properties: CivoSubnetToNetworkRelProperties = CivoSubnetToNetworkRelProperties()


@dataclass(frozen=True)
class CivoSubnetSchema(CartographyNodeSchema):
    """A subnet within a `CivoNetwork`."""

    label: str = "CivoSubnet"
    properties: CivoSubnetNodeProperties = CivoSubnetNodeProperties()
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([SUBNET])
    sub_resource_relationship: CivoSubnetToAccountRel = CivoSubnetToAccountRel()
    other_relationships: OtherRelationships = OtherRelationships(
        [CivoSubnetToNetworkRel()],
    )
