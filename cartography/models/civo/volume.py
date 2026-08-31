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
from cartography.models.ontology.labels import BLOCK_STORAGE


@dataclass(frozen=True)
class CivoVolumeNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo volume ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    name: PropertyRef = PropertyRef(
        "name", extra_index=True, description="Volume name."
    )
    region: PropertyRef = PropertyRef(
        "region", extra_index=True, description="Civo region."
    )
    instance_id: PropertyRef = PropertyRef(
        "instance_id", description="ID of the instance this volume is attached to."
    )
    cluster_id: PropertyRef = PropertyRef(
        "cluster_id",
        description="ID of the Kubernetes cluster this volume belongs to, if any.",
    )
    network_id: PropertyRef = PropertyRef(
        "network_id", description="ID of the network this volume is on."
    )
    mountpoint: PropertyRef = PropertyRef(
        "mountpoint", description="Mount point on the attached instance."
    )
    status: PropertyRef = PropertyRef("status", description="Volume status.")
    volume_type: PropertyRef = PropertyRef(
        "volume_type", description="Volume type (e.g. `ssd`)."
    )
    size_gb: PropertyRef = PropertyRef(
        "size_gb", description="Volume size in gigabytes."
    )
    bootable: PropertyRef = PropertyRef(
        "bootable", description="Whether this volume can be booted from."
    )
    created_at: PropertyRef = PropertyRef(
        "created_at", description="Creation timestamp."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoVolumeToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoVolume)
class CivoVolumeToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoVolume` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoVolumeToAccountRelProperties = CivoVolumeToAccountRelProperties()


@dataclass(frozen=True)
class CivoVolumeToInstanceRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoVolume)-[:ATTACHED_TO]->(:CivoInstance)
class CivoVolumeToInstanceRel(CartographyRelSchema):
    """Connects `CivoVolume` to the `CivoInstance` it's attached to."""

    target_node_label: str = "CivoInstance"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("instance_id")},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "ATTACHED_TO"
    properties: CivoVolumeToInstanceRelProperties = CivoVolumeToInstanceRelProperties()


@dataclass(frozen=True)
class CivoVolumeToClusterRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoVolume)-[:PART_OF_CLUSTER]->(:CivoKubernetesCluster)
class CivoVolumeToClusterRel(CartographyRelSchema):
    """Connects `CivoVolume` to the `CivoKubernetesCluster` it belongs to, if any."""

    target_node_label: str = "CivoKubernetesCluster"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("cluster_id")},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "PART_OF_CLUSTER"
    properties: CivoVolumeToClusterRelProperties = CivoVolumeToClusterRelProperties()


@dataclass(frozen=True)
class CivoVolumeToNetworkRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoVolume)-[:PART_OF_NETWORK]->(:CivoNetwork)
class CivoVolumeToNetworkRel(CartographyRelSchema):
    """Connects `CivoVolume` to the `CivoNetwork` it's on."""

    target_node_label: str = "CivoNetwork"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("network_id")},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "PART_OF_NETWORK"
    properties: CivoVolumeToNetworkRelProperties = CivoVolumeToNetworkRelProperties()


@dataclass(frozen=True)
class CivoVolumeSchema(CartographyNodeSchema):
    """A Civo block storage volume."""

    label: str = "CivoVolume"
    properties: CivoVolumeNodeProperties = CivoVolumeNodeProperties()
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([BLOCK_STORAGE])
    sub_resource_relationship: CivoVolumeToAccountRel = CivoVolumeToAccountRel()
    other_relationships: OtherRelationships = OtherRelationships(
        [
            CivoVolumeToInstanceRel(),
            CivoVolumeToClusterRel(),
            CivoVolumeToNetworkRel(),
        ],
    )
