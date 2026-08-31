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
from cartography.models.ontology.labels import COMPUTE_INSTANCE


@dataclass(frozen=True)
class CivoInstanceNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo instance ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    hostname: PropertyRef = PropertyRef(
        "hostname", extra_index=True, description="Instance hostname."
    )
    size: PropertyRef = PropertyRef(
        "size", description="Instance size slug (e.g. `g4s.kube.small`)."
    )
    region: PropertyRef = PropertyRef("region", description="Civo region.")
    status: PropertyRef = PropertyRef("status", description="Instance status.")
    network_id: PropertyRef = PropertyRef(
        "network_id", description="ID of the private network the instance is on."
    )
    private_ip: PropertyRef = PropertyRef(
        "private_ip", description="Private IP address."
    )
    public_ip: PropertyRef = PropertyRef(
        "public_ip", extra_index=True, description="Public IP address."
    )
    ipv6: PropertyRef = PropertyRef("ipv6", description="IPv6 address, if enabled.")
    reverse_dns: PropertyRef = PropertyRef(
        "reverse_dns", description="Reverse DNS hostname."
    )
    source_type: PropertyRef = PropertyRef(
        "source_type",
        description="Type of the source the instance was built from"
        " (e.g. `diskimage`, `snapshot`). Civo's instance list/retrieve"
        " responses carry `source_type`/`source_id`, not `template_id` -"
        " confirmed live against a real account.",
    )
    source_id: PropertyRef = PropertyRef(
        "source_id", description="ID of the disk image or snapshot source."
    )
    initial_user: PropertyRef = PropertyRef(
        "initial_user", description="Default login username."
    )
    firewall_id: PropertyRef = PropertyRef(
        "firewall_id", description="ID of the firewall protecting this instance."
    )
    ssh_key_id: PropertyRef = PropertyRef(
        "ssh_key_id", description="ID of the SSH key installed on this instance."
    )
    reserved_ip_id: PropertyRef = PropertyRef(
        "reserved_ip_id", description="ID of the reserved IP attached, if any."
    )
    tags: PropertyRef = PropertyRef("tags", description="User-defined tags.")
    allowed_ips: PropertyRef = PropertyRef(
        "allowed_ips",
        description="IPs allowed to reach this instance, beyond the firewall rules.",
    )
    cpu_cores: PropertyRef = PropertyRef("cpu_cores", description="Number of vCPUs.")
    ram_mb: PropertyRef = PropertyRef("ram_mb", description="RAM in megabytes.")
    disk_gb: PropertyRef = PropertyRef(
        "disk_gb", description="Root disk size in gigabytes."
    )
    volume_backed: PropertyRef = PropertyRef(
        "volume_backed", description="Whether the instance boots from a volume."
    )
    gpu_count: PropertyRef = PropertyRef(
        "gpu_count", description="Number of attached GPUs."
    )
    gpu_type: PropertyRef = PropertyRef("gpu_type", description="GPU type, if any.")
    created_at: PropertyRef = PropertyRef(
        "created_at", description="Creation timestamp."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoInstanceToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoInstance)
class CivoInstanceToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoInstance` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoInstanceToAccountRelProperties = (
        CivoInstanceToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoInstanceToSSHKeyRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoInstance)-[:HAS_SSH_KEY]->(:CivoSSHKey)
class CivoInstanceToSSHKeyRel(CartographyRelSchema):
    """Connects `CivoInstance` to the `CivoSSHKey` installed on it."""

    target_node_label: str = "CivoSSHKey"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ssh_key_id")},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "HAS_SSH_KEY"
    properties: CivoInstanceToSSHKeyRelProperties = CivoInstanceToSSHKeyRelProperties()


@dataclass(frozen=True)
class CivoInstanceSchema(CartographyNodeSchema):
    """Represents a Civo compute instance. Excludes several fields returned by
    the API that are real credentials or may embed user secrets:
    `initial_password`, `rescue_password`, `civostatsd_token` (all real
    credentials) and `script` (a user-supplied cloud-init script that commonly
    embeds tokens/secrets at creation time).

    `network_id`/`firewall_id` are kept as plain properties only in this PR -
    not wired as `PART_OF_NETWORK`/`PROTECTED_BY` relationships, since
    `CivoNetwork`/`CivoFirewall` are owned by the separate Networking PR and
    don't exist on this branch. Those edges are added by the
    add-civo-cross-resource-relationships PR, opened once every Civo
    resource PR has merged - a relationship must not target a node schema
    that doesn't exist yet on this PR's own branch."""

    label: str = "CivoInstance"
    properties: CivoInstanceNodeProperties = CivoInstanceNodeProperties()
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([COMPUTE_INSTANCE])
    sub_resource_relationship: CivoInstanceToAccountRel = CivoInstanceToAccountRel()
    other_relationships: OtherRelationships = OtherRelationships(
        [
            CivoInstanceToSSHKeyRel(),
        ],
    )
