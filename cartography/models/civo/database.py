from dataclasses import dataclass

from cartography.models.core.common import PropertyRef
from cartography.models.core.nodes import CartographyNodeProperties
from cartography.models.core.nodes import CartographyNodeSchema
from cartography.models.core.nodes import ExtraNodeLabels
from cartography.models.core.relationships import CartographyRelProperties
from cartography.models.core.relationships import CartographyRelSchema
from cartography.models.core.relationships import LinkDirection
from cartography.models.core.relationships import make_target_node_matcher
from cartography.models.core.relationships import TargetNodeMatcher
from cartography.models.ontology.labels import DATABASE


@dataclass(frozen=True)
class CivoDatabaseNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo database ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    name: PropertyRef = PropertyRef(
        "name", extra_index=True, description="Database name."
    )
    region: PropertyRef = PropertyRef(
        "region", extra_index=True, description="Civo region."
    )
    software: PropertyRef = PropertyRef(
        "software", description="Database software (e.g. `PostgreSQL`, `MySQL`)."
    )
    software_version: PropertyRef = PropertyRef(
        "software_version", description="Software version."
    )
    nodes: PropertyRef = PropertyRef("nodes", description="Number of database nodes.")
    size: PropertyRef = PropertyRef("size", description="Database instance size.")
    status: PropertyRef = PropertyRef("status", description="Database status.")
    public_ipv4: PropertyRef = PropertyRef(
        "public_ipv4", extra_index=True, description="Public IPv4 address."
    )
    private_ipv4: PropertyRef = PropertyRef(
        "private_ipv4", description="Private IPv4 address."
    )
    port: PropertyRef = PropertyRef("port", description="Connection port.")
    username: PropertyRef = PropertyRef(
        "username", description="Default connection username (not a secret by itself)."
    )
    network_id: PropertyRef = PropertyRef(
        "network_id", description="ID of the network this database is on."
    )
    firewall_id: PropertyRef = PropertyRef(
        "firewall_id", description="ID of the firewall protecting this database."
    )
    dns_entry: PropertyRef = PropertyRef(
        "dns_entry", description="DNS domain for database access, if any."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoDatabaseToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoDatabase)
class CivoDatabaseToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoDatabase` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoDatabaseToAccountRelProperties = (
        CivoDatabaseToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoDatabaseSchema(CartographyNodeSchema):
    """A Civo managed database. Excludes `password` and
    `database_user_info[].password` - real credentials returned by the API.

    `network_id`/`firewall_id` are kept as plain properties only in this PR -
    not wired as `PART_OF_NETWORK`/`PROTECTED_BY` relationships, since
    `CivoNetwork`/`CivoFirewall` are owned by the separate Networking PR and
    don't exist on this branch. Those edges are added by the
    add-civo-cross-resource-relationships PR, opened once every Civo
    resource PR has merged - a relationship must not target a node schema
    that doesn't exist yet on this PR's own branch."""

    label: str = "CivoDatabase"
    properties: CivoDatabaseNodeProperties = CivoDatabaseNodeProperties()
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([DATABASE])
    sub_resource_relationship: CivoDatabaseToAccountRel = CivoDatabaseToAccountRel()
