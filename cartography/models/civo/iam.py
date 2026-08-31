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
from cartography.models.ontology.labels import PERMISSION_ROLE
from cartography.models.ontology.labels import USER_GROUP


@dataclass(frozen=True)
class CivoTeamNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo team ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    name: PropertyRef = PropertyRef("name", extra_index=True, description="Team name.")
    created_at: PropertyRef = PropertyRef(
        "created_at", description="Creation timestamp."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoTeamToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoTeam)
class CivoTeamToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoTeam` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoTeamToAccountRelProperties = CivoTeamToAccountRelProperties()


@dataclass(frozen=True)
class CivoTeamSchema(CartographyNodeSchema):
    """A Civo team - a group of users sharing account access."""

    label: str = "CivoTeam"
    properties: CivoTeamNodeProperties = CivoTeamNodeProperties()
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([USER_GROUP])
    sub_resource_relationship: CivoTeamToAccountRel = CivoTeamToAccountRel()


@dataclass(frozen=True)
class CivoTeamMemberNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef("id", description="Civo team member ID.")
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    team_id: PropertyRef = PropertyRef("team_id", description="ID of the parent team.")
    user_id: PropertyRef = PropertyRef(
        "user_id", description="ID of the underlying Civo user."
    )
    permissions: PropertyRef = PropertyRef(
        "permissions",
        description="Raw comma-separated permission codes granted directly"
        " to this member (independent of any role).",
    )
    permission_codes: PropertyRef = PropertyRef(
        "permission_codes",
        description="`permissions` split into a list of"
        " `<account_id>/<code>` composite refs, for matching against"
        " `CivoPermission.id` (see `CivoTeamMemberToPermissionRel`).",
    )
    roles: PropertyRef = PropertyRef(
        "roles", description="Raw comma-separated role identifiers assigned."
    )
    role_refs: PropertyRef = PropertyRef(
        "role_refs",
        description="`roles` split into a list of `<account_id>/<role id>`"
        " composite refs, for matching against `CivoRole.id` (see"
        " `CivoTeamMemberToRoleRel` - confirmed live, by assigning a real"
        " role and reading it back, that `roles` holds role IDs, not"
        " names).",
    )
    created_at: PropertyRef = PropertyRef(
        "created_at", description="Creation timestamp."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoTeamMemberToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoTeamMember)
class CivoTeamMemberToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoTeamMember` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoTeamMemberToAccountRelProperties = (
        CivoTeamMemberToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoTeamMemberToTeamRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoTeam)-[:HAS_MEMBER]->(:CivoTeamMember)
class CivoTeamMemberToTeamRel(CartographyRelSchema):
    """Connects `CivoTeam` to its `CivoTeamMember`s."""

    target_node_label: str = "CivoTeam"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("team_id")},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "HAS_MEMBER"
    properties: CivoTeamMemberToTeamRelProperties = CivoTeamMemberToTeamRelProperties()


@dataclass(frozen=True)
class CivoTeamMemberToPermissionRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoTeamMember)-[:HAS_DIRECT_PERMISSION]->(:CivoPermission)
class CivoTeamMemberToPermissionRel(CartographyRelSchema):
    """Connects `CivoTeamMember` to the `CivoPermission`s granted directly
    to it (independent of any role), matched by composite id (see
    `CivoPermissionSchema`). Named `HAS_DIRECT_PERMISSION`, not the more
    common `HAS_PERMISSION` used elsewhere in this codebase: `CivoTeamMember`
    deliberately isn't labeled `UserAccount` (see `CivoTeamMemberSchema`),
    so a generic name here would look like it participates in canonical
    ontology-level queries when it doesn't. The `DIRECT` qualifier also
    distinguishes this from permissions a member holds indirectly through
    a `CivoRole` (see `CivoRoleToPermissionRel`'s `GRANTS`)."""

    target_node_label: str = "CivoPermission"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("permission_codes", one_to_many=True)},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "HAS_DIRECT_PERMISSION"
    properties: CivoTeamMemberToPermissionRelProperties = (
        CivoTeamMemberToPermissionRelProperties()
    )


@dataclass(frozen=True)
class CivoTeamMemberToRoleRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoTeamMember)-[:HAS_ASSIGNED_ROLE]->(:CivoRole)
class CivoTeamMemberToRoleRel(CartographyRelSchema):
    """Connects `CivoTeamMember` to its assigned `CivoRole`s, matched by
    composite id (see `CivoRoleSchema`). Confirmed live (assigned a real
    role to a test member and read the response back) that `roles` holds
    role IDs, not names - Civo's API docs and civogo don't state this
    anywhere; it was previously assumed ambiguous and matched by both id
    and name defensively, which this replaces now that it's been directly
    verified. Named `HAS_ASSIGNED_ROLE`, not the more common `HAS_ROLE`
    used elsewhere in this codebase: `CivoTeamMember` deliberately isn't
    labeled `UserAccount` (see `CivoTeamMemberSchema`), so a generic name
    here would look like it participates in canonical UserAccount-to-
    PermissionRole HAS_ROLE queries elsewhere in the ontology, when it
    doesn't."""

    target_node_label: str = "CivoRole"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("role_refs", one_to_many=True)},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "HAS_ASSIGNED_ROLE"
    properties: CivoTeamMemberToRoleRelProperties = CivoTeamMemberToRoleRelProperties()


@dataclass(frozen=True)
class CivoTeamMemberSchema(CartographyNodeSchema):
    """A user's membership in a `CivoTeam`. Excludes `api_key` - Civo's
    `GET /v2/teams/{id}/members` returns each member's live API key in
    plaintext (confirmed against a real account); it must never reach the
    graph.

    Note: this represents a *membership* record (user_id + team_id +
    grants), not the user identity itself - Civo's own SDK describes
    `TeamMember` as "a link record between User and Team". A proper
    `CivoUser`/`UserAccount` node was investigated but is currently blocked:
    `GET /v2/users` and `/v2/users/{id}` both return
    `authentication_access_denied` (403) against this account's API key,
    even though its role effectively grants full account access - user
    data may require organisation-level credentials this module doesn't
    have. Because of this, `CivoTeamMember` does NOT declare the
    `UserAccount` ontology label (it also lacks the ontology's required
    `email` field, which only a real user record would carry) - its role/
    permission edges are named `HAS_ASSIGNED_ROLE`/`HAS_DIRECT_PERMISSION`
    rather than the more common `HAS_ROLE`/`HAS_PERMISSION` used elsewhere
    in this codebase, specifically so they don't look like they
    participate in canonical UserAccount-to-PermissionRole HAS_ROLE
    queries elsewhere in the ontology, when they don't."""

    label: str = "CivoTeamMember"
    properties: CivoTeamMemberNodeProperties = CivoTeamMemberNodeProperties()
    sub_resource_relationship: CivoTeamMemberToAccountRel = CivoTeamMemberToAccountRel()
    other_relationships: OtherRelationships = OtherRelationships(
        [
            CivoTeamMemberToTeamRel(),
            CivoTeamMemberToPermissionRel(),
            CivoTeamMemberToRoleRel(),
        ],
    )


@dataclass(frozen=True)
class CivoRoleNodeProperties(CartographyNodeProperties):
    id: PropertyRef = PropertyRef(
        "id",
        description="Synthetic `<account_id>/<role id>`, not Civo's own"
        " role ID - see `CivoRoleSchema` for why (a bare role ID would"
        " merge two different accounts' roles onto the same Neo4j node,"
        " which is unsafe for cleanup: confirmed live that built-in role"
        " IDs are identical across every account). The real Civo role ID"
        " is kept as `role_id`.",
    )
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    role_id: PropertyRef = PropertyRef(
        "role_id", extra_index=True, description="Civo role ID."
    )
    name: PropertyRef = PropertyRef("name", extra_index=True, description="Role name.")
    permissions: PropertyRef = PropertyRef(
        "permissions",
        description="Raw comma-separated permission codes this role grants"
        " (may include wildcards, e.g. `billing.*`).",
    )
    built_in: PropertyRef = PropertyRef(
        "built_in", description="Whether this is a Civo built-in role."
    )
    owner_account_id: PropertyRef = PropertyRef(
        "owner_account_id",
        description="Raw `account_id` from the role response, distinct from"
        " this node's own `account_id` (the tenant this row was fetched"
        " under). Confirmed live that `POST /v2/roles` accepts either this"
        " or `owner_organisation_id` to scope a custom role - built-in"
        " roles carry neither.",
    )
    owner_organisation_id: PropertyRef = PropertyRef(
        "owner_organisation_id",
        description="Raw `organisation_id` from the role response - Civo's"
        ' own SDK documents custom roles as being "for use within an'
        ' organisation", so a role with this set may be visible to (and'
        " deletable via) more than one Civo account in the same"
        " organisation. This module only has single-account access and"
        " could not verify cross-account sharing directly.",
    )
    role_type: PropertyRef = PropertyRef(
        "role_type",
        description="`built_in` as `builtin`/`custom` (for the ontology's"
        " `type` field only - a Neo4j boolean property can't be compared"
        " against a mapping's string literals).",
    )
    permission_codes: PropertyRef = PropertyRef(
        "permission_codes",
        description="`permissions` split into a list of"
        " `<account_id>/<code>` composite refs, for matching against"
        " `CivoPermission.id` (see `CivoRoleToPermissionRel`).",
    )
    created_at: PropertyRef = PropertyRef(
        "created_at", description="Creation timestamp."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoRoleToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoRole)
class CivoRoleToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoRole` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoRoleToAccountRelProperties = CivoRoleToAccountRelProperties()


@dataclass(frozen=True)
class CivoRoleToPermissionRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoRole)-[:GRANTS]->(:CivoPermission)
class CivoRoleToPermissionRel(CartographyRelSchema):
    """Connects `CivoRole` to the `CivoPermission`s it grants, matched by
    composite id (see `CivoPermissionSchema`). Resolves for every entry,
    including wildcards like `billing.*` - `CivoPermission` isn't limited
    to GET /v2/permissions' small catalog; the transform also mints an
    entry for every pattern actually observed on a role or member, so the
    target always exists."""

    target_node_label: str = "CivoPermission"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("permission_codes", one_to_many=True)},
    )
    direction: LinkDirection = LinkDirection.OUTWARD
    rel_label: str = "GRANTS"
    properties: CivoRoleToPermissionRelProperties = CivoRoleToPermissionRelProperties()


@dataclass(frozen=True)
class CivoRoleSchema(CartographyNodeSchema):
    """A Civo IAM role - a named bundle of permission codes.

    Scoped to the CivoAccount it was fetched under, same as every other
    node in this module. Confirmed live that `POST /v2/roles` accepts
    either an `account_id` or an `organisation_id` to own a custom role,
    and civogo documents roles as being "for use within an organisation" -
    so an organisation-owned role could, in principle, be visible to (and
    deleted by cleanup from) more than one Civo account sharing that
    organisation. This module only has single-account API access and could
    not verify cross-account role sharing directly - `owner_account_id`/
    `owner_organisation_id` are captured on the node for when that can be
    tested, rather than guessing at a different cleanup scope now."""

    label: str = "CivoRole"
    properties: CivoRoleNodeProperties = CivoRoleNodeProperties()
    extra_node_labels: ExtraNodeLabels = ExtraNodeLabels([PERMISSION_ROLE])
    sub_resource_relationship: CivoRoleToAccountRel = CivoRoleToAccountRel()
    other_relationships: OtherRelationships = OtherRelationships(
        [CivoRoleToPermissionRel()],
    )
    # `id` is `<account_id>/<role id>` (see CivoRoleNodeProperties.id) -
    # each account gets its own node even for a role that's genuinely
    # shared, trading a minor "why two nodes" surprise for a hard guarantee
    # that one account's cleanup can never delete another account's data.


@dataclass(frozen=True)
class CivoPermissionNodeProperties(CartographyNodeProperties):
    """`CivoPermission` combines GET /v2/permissions' small catalog (e.g.
    `*.*`, confirmed the same across at least this account's calls) with
    patterns derived from this account's own roles/members (most
    `permissions` entries, e.g. `billing.*`, aren't in the catalog at all).
    Account-scoped like every other node here, rather than left uncleaned
    as a pure global reference table: unlike `CivoAccountSchema` (a real
    tenant root with nothing to scope cleanup to), the derived entries here
    are only ever meaningful relative to the account they were observed on,
    and would otherwise orphan forever once their owning role/member is
    removed."""

    id: PropertyRef = PropertyRef(
        "id",
        description="Synthetic `<account_id>/<code>`, not the bare code -"
        " see `CivoPermissionSchema` for why (confirmed live that codes"
        " like `billing.*` are identical strings across every account, so"
        " a bare-code id would merge two accounts' permission nodes onto"
        " one, unsafe for cleanup). The bare code is kept as `code`.",
    )
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)
    code: PropertyRef = PropertyRef(
        "code", extra_index=True, description="Permission code, e.g. `*.*`."
    )
    name: PropertyRef = PropertyRef(
        "name",
        description="Permission display name (only set for entries from"
        " the GET /v2/permissions catalog - derived, account-observed"
        " patterns have none).",
    )
    description: PropertyRef = PropertyRef(
        "description", description="Permission description (see `name`)."
    )
    account_id: PropertyRef = PropertyRef(
        "ACCOUNT_ID", set_in_kwargs=True, description="Civo account ID."
    )


@dataclass(frozen=True)
class CivoPermissionToAccountRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:CivoAccount)-[:RESOURCE]->(:CivoPermission)
class CivoPermissionToAccountRel(CartographyRelSchema):
    """Connects `CivoAccount` to `CivoPermission` through `RESOURCE`."""

    target_node_label: str = "CivoAccount"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("ACCOUNT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: CivoPermissionToAccountRelProperties = (
        CivoPermissionToAccountRelProperties()
    )


@dataclass(frozen=True)
class CivoPermissionSchema(CartographyNodeSchema):
    """A Civo permission code or pattern, e.g. `*.*` or `billing.*`,
    scoped per-account (`id` is `<account_id>/<code>`, not the bare code -
    see `CivoPermissionNodeProperties.id`). Confirmed live that the same
    code is a literally identical string across different Civo accounts;
    a bare-code node identity would let two accounts' data collide onto
    one Neo4j node, and one account's scoped cleanup
    (`MATCH (n)<-[:RESOURCE]-(:CivoAccount{id: A}) WHERE stale DETACH
    DELETE n`) would then delete that node - and every relationship
    another account still holds to it - outright."""

    label: str = "CivoPermission"
    properties: CivoPermissionNodeProperties = CivoPermissionNodeProperties()
    sub_resource_relationship: CivoPermissionToAccountRel = CivoPermissionToAccountRel()
