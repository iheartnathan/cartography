from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.objectstores
import cartography.intel.civo.sshkeys
import cartography.intel.civo.volumes
from cartography.config import Config
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.objectstores import OBJECTSTORE_CREDENTIALS_PAGE
from tests.data.civo.objectstores import OBJECTSTORES_PAGE
from tests.data.civo.objectstores import TEST_OBJECTSTORE_CREDENTIAL_ID
from tests.data.civo.objectstores import TEST_OBJECTSTORE_ID
from tests.data.civo.volumes import TEST_VOLUME_ID
from tests.data.civo.volumes import VOLUMES_RESPONSE
from tests.integration.util import check_nodes
from tests.integration.util import check_rels

TEST_UPDATE_TAG = 123456789
TEST_BASE_URL = "https://api.fake-civo.com"
TEST_ACCOUNT_ID = QUOTA_RESPONSE["id"]
TEST_REGION_CODE = "lon1"


def _common_job_parameters() -> dict:
    return {
        "UPDATE_TAG": TEST_UPDATE_TAG,
        "BASE_URL": TEST_BASE_URL,
        "REGIONS": [
            {
                "code": TEST_REGION_CODE,
                "features": {
                    "iaas": True,
                    "kubernetes": True,
                    "object_store": True,
                    "loadbalancer": True,
                    "gpu": True,
                    "dbaas": True,
                    "volume": True,
                    "paas": True,
                    "public_ip_node_pools": True,
                },
            },
        ],
    }


@patch.object(
    cartography.intel.civo.objectstores,
    "get_credentials",
    return_value=OBJECTSTORE_CREDENTIALS_PAGE["items"],
)
@patch.object(
    cartography.intel.civo.objectstores,
    "get_stores",
    return_value=OBJECTSTORES_PAGE["items"],
)
@patch.object(
    cartography.intel.civo.volumes,
    "get",
    return_value=VOLUMES_RESPONSE,
)
@patch.object(
    cartography.intel.civo.account,
    "get",
    return_value=QUOTA_RESPONSE,
)
def test_civo_volumes_objectstores_graph(
    mock_account_get,
    mock_volumes_get,
    mock_stores_get,
    mock_credentials_get,
    neo4j_session,
):
    """
    CivoVolume/CivoObjectStore loaded standalone. instance_id/cluster_id/
    network_id are kept as plain properties only in this PR, not wired as
    relationships - CivoInstance/CivoKubernetesCluster/CivoNetwork are
    owned by the separate Compute/Kubernetes/Networking PRs and don't
    exist on this branch. Those edges are added in a follow-up
    cross-resource-relationships PR once every Civo resource PR has
    merged (see the PR split plan).
    """
    # Arrange
    api_session = requests.Session()
    common_job_parameters = _common_job_parameters()
    account = cartography.intel.civo.account.sync(
        neo4j_session, api_session, common_job_parameters
    )
    common_job_parameters["ACCOUNT_ID"] = account["id"]

    # Act
    cartography.intel.civo.volumes.sync(
        neo4j_session, api_session, common_job_parameters
    )
    cartography.intel.civo.objectstores.sync(
        neo4j_session, api_session, common_job_parameters
    )

    # Assert: CivoVolume loaded, with the ontology BlockStorage size mapped.
    assert check_nodes(
        neo4j_session, "CivoVolume", ["id", "size_gb", "_ont_size_gb"]
    ) == {(TEST_VOLUME_ID, 50, 50)}

    # Assert: CivoObjectStore loaded with owner_info flattened.
    assert check_nodes(
        neo4j_session, "CivoObjectStore", ["id", "name", "owner_access_key_id"]
    ) == {(TEST_OBJECTSTORE_ID, "app-uploads", "AKIACIVOEXAMPLE123")}

    # Assert: CivoObjectStoreCredential loaded with access_key_id but no
    # secret_access_key_id anywhere on the node.
    assert check_nodes(
        neo4j_session, "CivoObjectStoreCredential", ["id", "access_key_id"]
    ) == {(TEST_OBJECTSTORE_CREDENTIAL_ID, "AKIACIVOEXAMPLE123")}
    credential_props = neo4j_session.run(
        "MATCH (n:CivoObjectStoreCredential {id: $id}) RETURN properties(n) AS props",
        id=TEST_OBJECTSTORE_CREDENTIAL_ID,
    ).single()["props"]
    assert "secret_access_key_id" not in credential_props

    # Assert: CivoObjectStore is linked to its owning credential.
    assert check_rels(
        neo4j_session,
        "CivoObjectStore",
        "id",
        "CivoObjectStoreCredential",
        "id",
        "HAS_OWNER_CREDENTIAL",
    ) == {(TEST_OBJECTSTORE_ID, TEST_OBJECTSTORE_CREDENTIAL_ID)}


@patch.object(
    cartography.intel.civo,
    "get_regions",
    return_value=[
        {
            "code": TEST_REGION_CODE,
            "features": {
                "iaas": True,
                "kubernetes": True,
                "object_store": True,
                "loadbalancer": True,
                "gpu": True,
                "dbaas": True,
                "volume": True,
                "paas": True,
                "public_ip_node_pools": True,
            },
        },
    ],
)
@patch.object(
    cartography.intel.civo.objectstores,
    "get_credentials",
    return_value=OBJECTSTORE_CREDENTIALS_PAGE["items"],
)
@patch.object(
    cartography.intel.civo.objectstores,
    "get_stores",
    return_value=OBJECTSTORES_PAGE["items"],
)
@patch.object(
    cartography.intel.civo.volumes,
    "get",
    return_value=VOLUMES_RESPONSE,
)
@patch.object(
    cartography.intel.civo.sshkeys,
    "get",
    return_value=[],
)
@patch.object(
    cartography.intel.civo.account,
    "get",
    return_value=QUOTA_RESPONSE,
)
def test_start_civo_ingestion_wires_storage_resources(
    mock_account_get,
    mock_sshkeys_get,
    mock_volumes_get,
    mock_stores_get,
    mock_credentials_get,
    mock_get_regions,
    neo4j_session,
):
    """
    Exercises the real entrypoint end-to-end for this PR's own resources,
    unlike the test above which calls each module's sync()/cleanup()
    directly. Catches wiring bugs a per-domain test can't: a missing
    entrypoint import, a forgotten sync() call, or a merge-conflict
    resolution that silently drops this PR's resources from __init__.py.
    """
    # Arrange
    config = Config(
        neo4j_uri="bolt://fake-neo4j:7687",
        update_tag=TEST_UPDATE_TAG,
        civo_api_key="fake-key",
        civo_base_url=TEST_BASE_URL,
    )

    # Act
    cartography.intel.civo.start_civo_ingestion(neo4j_session, config)

    # Assert: this PR's resources loaded and linked to their account,
    # proving the entrypoint actually wires this PR's sync() calls.
    assert check_nodes(neo4j_session, "CivoVolume", ["id"]) == {(TEST_VOLUME_ID,)}
    assert check_nodes(neo4j_session, "CivoObjectStore", ["id"]) == {
        (TEST_OBJECTSTORE_ID,)
    }
    assert check_rels(
        neo4j_session, "CivoAccount", "id", "CivoVolume", "id", "RESOURCE"
    ) == {(TEST_ACCOUNT_ID, TEST_VOLUME_ID)}

    # Cleanup: this test's nodes would otherwise persist in the shared
    # module-scoped test database and pollute other tests' exact-set
    # assertions.
    neo4j_session.run(
        "MATCH (n:CivoAccount) WHERE n.id = $id DETACH DELETE n", id=TEST_ACCOUNT_ID
    )
    neo4j_session.run(
        "MATCH (n) WHERE n:CivoVolume OR n:CivoObjectStore OR n:CivoObjectStoreCredential DETACH DELETE n"
    )
