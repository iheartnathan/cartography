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
from cartography.models.ontology.labels import DNS_RECORD
from cartography.models.ontology.labels import DNS_ZONE


@dataclass(frozen=True)
class CivoDNSDomainNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo DNS domain ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    name: PropertyRef = PropertyRef(
        "name", extra_index=True, description="Domain name."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoDNSDomainToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoDNSDomain)
class CivoDNSDomainToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoDNSDomain` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoDNSDomainToAccountRelProperties = (
        CivoDNSDomainToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoDNSDomainSchema(CartographyNodeSchema):
    """A Civo-managed DNS domain."""

    label: str = "CivoDNSDomain"
    properties: CivoDNSDomainNodeProperties = CivoDNSDomainNodeProperties()
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([DNS_ZONE])
    sub_resource_relationship: CivoDNSDomainToAccountRel = CivoDNSDomainToAccountRel()


@dataclass(frozen=True)
class CivoDNSRecordNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo DNS record ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    domain_id: PropertyRef = PropertyRef(
        "domain_id", description="ID of the parent DNS domain."
    )
    name: PropertyRef = PropertyRef("name", description="Record name.")
    value: PropertyRef = PropertyRef("value", description="Record value.")
    type: PropertyRef = PropertyRef(
        "type", extra_index=True, description="Record type (e.g. `A`, `CNAME`)."
    )
    priority: PropertyRef = PropertyRef(
        "priority", description="Record priority, for MX/SRV records."
    )
    ttl: PropertyRef = PropertyRef("ttl", description="Time to live, in seconds.")
    created_at: PropertyRef = PropertyRef(
        "created_at", description="Creation timestamp."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoDNSRecordToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoDNSRecord)
class CivoDNSRecordToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoDNSRecord` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoDNSRecordToAccountRelProperties = (
        CivoDNSRecordToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoDNSRecordToDomainRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoDNSDomain)-[:HAS_RECORD]->(:CivoDNSRecord)
class CivoDNSRecordToDomainRel(CartographyRelSchema):
    """Connects `CivoDNSDomain` to its `CivoDNSRecord`s."""

    target_node_label: str = "CivoDNSDomain"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("domain_id")},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "HAS_RECORD"
    properties: CivoDNSRecordToDomainRelProperties = (
        CivoDNSRecordToDomainRelProperties()
    )


@dataclass(frozen=True)
class CivoDNSRecordSchema(CartographyNodeSchema):
    """A DNS record within a `CivoDNSDomain`."""

    label: str = "CivoDNSRecord"
    properties: CivoDNSRecordNodeProperties = CivoDNSRecordNodeProperties()
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([DNS_RECORD])
    sub_resource_relationship: CivoDNSRecordToAccountRel = CivoDNSRecordToAccountRel()
    other_relationships: OtherRelationships = OtherRelationships(
        [CivoDNSRecordToDomainRel()],
    )
