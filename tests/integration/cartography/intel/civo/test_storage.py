from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.objectstores
import cartography.intel.civo.sshkeys
import cartography.intel.civo.volumes
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
