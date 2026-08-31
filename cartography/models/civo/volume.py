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
class CivoVolumeSchema(CartographyNodeSchema):
    """A Civo block storage volume.

    `instance_id`/`cluster_id`/`network_id` are kept as plain properties
    only in this PR - not wired as `ATTACHED_TO`/`PART_OF_CLUSTER`/
    `PART_OF_NETWORK` relationships, since `CivoInstance`/
    `CivoKubernetesCluster`/`CivoNetwork` are owned by the separate
    Compute/Kubernetes/Networking PRs and don't exist on this branch.
    Those edges are added in a follow-up cross-resource-relationships PR
    once every Civo resource PR has merged (see
    .claude-workstreams/civo-pr-split-plan.md) - a relationship must not
    target a node schema that doesn't exist yet on this PR's own
    branch."""

    label: str = "CivoVolume"
    properties: CivoVolumeNodeProperties = CivoVolumeNodeProperties()
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([BLOCK_STORAGE])
    sub_resource_relationship: CivoVolumeToAccountRel = CivoVolumeToAccountRel()
