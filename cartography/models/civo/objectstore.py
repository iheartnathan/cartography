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
from cartography.models.ontology.labels import API_KEY
from cartography.models.ontology.labels import OBJECT_STORAGE


@dataclass(frozen=True)
class CivoObjectStoreNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo object store ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    name: PropertyRef = PropertyRef(
        "name", extra_index=True, description="Object store name."
    )
    region: PropertyRef = PropertyRef(
        "region", extra_index=True, description="Civo region."
    )
    max_size_gb: PropertyRef = PropertyRef(
        "max_size_gb", description="Maximum size in gigabytes."
    )
    endpoint: PropertyRef = PropertyRef(
        "endpoint", description="S3-compatible endpoint URL for this bucket."
    )
    status: PropertyRef = PropertyRef("status", description="Object store status.")
    # owner_info flattened - Neo4j does not support nested map properties.
    # access_key_id (not the secret access key) is safe to store, mirroring
    # the AWS access-key-id-vs-secret-access-key convention.
    owner_access_key_id: PropertyRef = PropertyRef(
        "owner_access_key_id", description="Access key ID of the owning credential."
    )
    owner_name: PropertyRef = PropertyRef(
        "owner_name", description="Name of the owning credential."
    )
    owner_credential_id: PropertyRef = PropertyRef(
        "owner_credential_id", description="ID of the owning credential."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoObjectStoreToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoObjectStore)
class CivoObjectStoreToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoObjectStore` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoObjectStoreToAccountRelProperties = (
        CivoObjectStoreToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoObjectStoreToCredentialRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoObjectStore)-[:HAS_OWNER_CREDENTIAL]->(:CivoObjectStoreCredential)
class CivoObjectStoreToCredentialRel(CartographyRelSchema):
    """Connects `CivoObjectStore` to the `CivoObjectStoreCredential` Civo
    designates as its owner (`owner_credential_id`) - not every credential
    that can access the store. Civo's object-store creation docs describe
    this as the credential *selected to be the store's owner*; other
    credentials can separately be granted privileges on the same store,
    so a general-sounding name like `USES_CREDENTIAL` would overclaim what
    this edge actually represents."""

    target_node_label: str = "CivoObjectStoreCredential"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("owner_credential_id")},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "HAS_OWNER_CREDENTIAL"
    properties: CivoObjectStoreToCredentialRelProperties = (
        CivoObjectStoreToCredentialRelProperties()
    )


@dataclass(frozen=True)
class CivoObjectStoreSchema(CartographyNodeSchema):
    """A Civo S3-compatible object storage bucket."""

    label: str = "CivoObjectStore"
    properties: CivoObjectStoreNodeProperties = CivoObjectStoreNodeProperties()
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([OBJECT_STORAGE])
    sub_resource_relationship: CivoObjectStoreToAccountRel = (
        CivoObjectStoreToAccountRel()
    )
    other_relationships: OtherRelationships = OtherRelationships(
        [CivoObjectStoreToCredentialRel()],
    )


@dataclass(frozen=True)
class CivoObjectStoreCredentialNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo object store credential ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    name: PropertyRef = PropertyRef(
        "name", extra_index=True, description="Credential name."
    )
    region: PropertyRef = PropertyRef(
        "region", extra_index=True, description="Civo region."
    )
    access_key_id: PropertyRef = PropertyRef(
        "access_key_id",
        extra_index=True,
        description="Access key ID (not secret - the secret access key is never stored).",
    )
    max_size_gb: PropertyRef = PropertyRef(
        "max_size_gb", description="Maximum size in gigabytes this credential allows."
    )
    suspended: PropertyRef = PropertyRef(
        "suspended", description="Whether this credential is suspended."
    )
    status: PropertyRef = PropertyRef("status", description="Credential status.")
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoObjectStoreCredentialToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoObjectStoreCredential)
class CivoObjectStoreCredentialToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoObjectStoreCredential` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoObjectStoreCredentialToAccountRelProperties = (
        CivoObjectStoreCredentialToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoObjectStoreCredentialSchema(CartographyNodeSchema):
    """A Civo object store credential (S3-compatible access key pair). The
    secret access key is a real credential and is never stored - only the
    access key ID, which is safe (same convention as AWS)."""

    label: str = "CivoObjectStoreCredential"
    properties: CivoObjectStoreCredentialNodeProperties = (
        CivoObjectStoreCredentialNodeProperties()
    )
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([API_KEY])
    sub_resource_relationship: CivoObjectStoreCredentialToAccountRel = (
        CivoObjectStoreCredentialToAccountRel()
    )
