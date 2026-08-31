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
from cartography.models.ontology.labels import NETWORK_ACCESS_CONTROL


@dataclass(frozen=True)
class CivoFirewallNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo firewall ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    name: PropertyRef = PropertyRef(
        "name", extra_index=True, description="Firewall name."
    )
    region: PropertyRef = PropertyRef(
        "region", extra_index=True, description="Civo region."
    )
    network_id: PropertyRef = PropertyRef(
        "network_id", description="ID of the network this firewall belongs to."
    )
    rules_count: PropertyRef = PropertyRef(
        "rules_count", description="Number of rules on this firewall."
    )
    instance_count: PropertyRef = PropertyRef(
        "instance_count", description="Number of instances using this firewall."
    )
    cluster_count: PropertyRef = PropertyRef(
        "cluster_count",
        description="Number of Kubernetes clusters using this firewall.",
    )
    loadbalancer_count: PropertyRef = PropertyRef(
        "loadbalancer_count",
        description="Number of load balancers using this firewall.",
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoFirewallToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoFirewall)
class CivoFirewallToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoFirewall` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoFirewallToAccountRelProperties = (
        CivoFirewallToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoFirewallToNetworkRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoFirewall)-[:PART_OF_NETWORK]->(:CivoNetwork)
class CivoFirewallToNetworkRel(CartographyRelSchema):
    """Connects `CivoFirewall` to the `CivoNetwork` it belongs to."""

    target_node_label: str = "CivoNetwork"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("network_id")},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "PART_OF_NETWORK"
    properties: CivoFirewallToNetworkRelProperties = (
        CivoFirewallToNetworkRelProperties()
    )


@dataclass(frozen=True)
class CivoFirewallSchema(CartographyNodeSchema):
    """A Civo firewall: a bidirectional container of ingress/egress rules
    attached to instances, Kubernetes clusters, and load balancers."""

    label: str = "CivoFirewall"
    properties: CivoFirewallNodeProperties = CivoFirewallNodeProperties()
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([NETWORK_ACCESS_CONTROL])
    sub_resource_relationship: CivoFirewallToAccountRel = CivoFirewallToAccountRel()
    other_relationships: OtherRelationships = OtherRelationships(
        [CivoFirewallToNetworkRel()],
    )


@dataclass(frozen=True)
class CivoFirewallRuleNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo firewall rule ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    firewall_id: PropertyRef = PropertyRef(
        "firewall_id", description="ID of the parent firewall."
    )
    protocol: PropertyRef = PropertyRef(
        "protocol", description="Protocol: `tcp`, `udp`, or `icmp`."
    )
    start_port: PropertyRef = PropertyRef(
        "start_port", description="Start of the port range."
    )
    end_port: PropertyRef = PropertyRef(
        "end_port", description="End of the port range, if a range."
    )
    cidr: PropertyRef = PropertyRef(
        "cidr", description="CIDR blocks this rule applies to."
    )
    direction: PropertyRef = PropertyRef(
        "direction", extra_index=True, description="`ingress` or `egress`."
    )
    action: PropertyRef = PropertyRef(
        "action", extra_index=True, description="`allow` or `deny`."
    )
    label: PropertyRef = PropertyRef("label", description="Optional rule label.")
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoFirewallRuleToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoFirewallRule)
class CivoFirewallRuleToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoFirewallRule` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoFirewallRuleToAccountRelProperties = (
        CivoFirewallRuleToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoFirewallRuleToFirewallRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoFirewall)-[:HAS_RULE]->(:CivoFirewallRule)
class CivoFirewallRuleToFirewallRel(CartographyRelSchema):
    """Connects `CivoFirewall` to its `CivoFirewallRule`s."""

    target_node_label: str = "CivoFirewall"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("firewall_id")},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "HAS_RULE"
    properties: CivoFirewallRuleToFirewallRelProperties = (
        CivoFirewallRuleToFirewallRelProperties()
    )


@dataclass(frozen=True)
class CivoFirewallRuleSchema(CartographyNodeSchema):
    """A single ingress/egress rule on a `CivoFirewall`."""

    label: str = "CivoFirewallRule"
    properties: CivoFirewallRuleNodeProperties = CivoFirewallRuleNodeProperties()
    sub_resource_relationship: CivoFirewallRuleToAccountRel = (
        CivoFirewallRuleToAccountRel()
    )
    other_relationships: OtherRelationships = OtherRelationships(
        [CivoFirewallRuleToFirewallRel()],
    )
