from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.instances
import cartography.intel.civo.kubernetes
import cartography.intel.civo.networks
import cartography.intel.civo.objectstores
import cartography.intel.civo.sshkeys
import cartography.intel.civo.volumes
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.instances import INSTANCES_RESPONSE
from tests.data.civo.instances import TEST_INSTANCE_ID
from tests.data.civo.kubernetes import KUBERNETES_CLUSTERS_PAGE
from tests.data.civo.kubernetes import TEST_CLUSTER_ID
from tests.data.civo.networks import NETWORKS_RESPONSE
from tests.data.civo.networks import SUBNETS_RESPONSE
from tests.data.civo.networks import TEST_NETWORK_ID
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
NETWORKS_BY_REGION = [(network, TEST_REGION_CODE) for network in NETWORKS_RESPONSE]
VOLUMES_WITH_RELATIONSHIPS = [
    {**volume, "cluster_id": TEST_CLUSTER_ID} for volume in VOLUMES_RESPONSE
]


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
    return_value=VOLUMES_WITH_RELATIONSHIPS,
)
@patch.object(
    cartography.intel.civo.kubernetes,
    "get",
    return_value=KUBERNETES_CLUSTERS_PAGE["items"],
)
@patch.object(
    cartography.intel.civo.instances,
    "get",
    return_value=INSTANCES_RESPONSE,
)
@patch.object(
    cartography.intel.civo.networks,
    "get_subnets",
    return_value=cartography.intel.civo.networks.transform_subnets(
        SUBNETS_RESPONSE,
        TEST_NETWORK_ID,
    ),
)
@patch.object(
    cartography.intel.civo.networks,
    "get",
    return_value=NETWORKS_BY_REGION,
)
@patch.object(
    cartography.intel.civo.account,
    "get",
    return_value=QUOTA_RESPONSE,
)
def test_civo_volumes_objectstores_graph(
    mock_account_get,
    mock_networks_get,
    mock_subnets_get,
    mock_instances_get,
    mock_kubernetes_get,
    mock_volumes_get,
    mock_stores_get,
    mock_credentials_get,
    neo4j_session,
):
    """
    Verify storage properties and secret exclusions together with the volume
    relationships owned by the Storage layer.
    """
    # Arrange
    api_session = requests.Session()
    common_job_parameters = _common_job_parameters()
    account = cartography.intel.civo.account.sync(
        neo4j_session, api_session, common_job_parameters
    )
    common_job_parameters["ACCOUNT_ID"] = account["id"]
    cartography.intel.civo.networks.sync(
        neo4j_session, api_session, common_job_parameters
    )
    cartography.intel.civo.instances.sync(
        neo4j_session, api_session, common_job_parameters
    )
    cartography.intel.civo.kubernetes.sync(
        neo4j_session, api_session, common_job_parameters
    )

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
    assert check_rels(
        neo4j_session,
        "CivoVolume",
        "id",
        "CivoInstance",
        "id",
        "ATTACHED_TO",
    ) == {(TEST_VOLUME_ID, TEST_INSTANCE_ID)}
    assert check_rels(
        neo4j_session,
        "CivoVolume",
        "id",
        "CivoKubernetesCluster",
        "id",
        "PART_OF_CLUSTER",
    ) == {(TEST_VOLUME_ID, TEST_CLUSTER_ID)}
    assert check_rels(
        neo4j_session,
        "CivoVolume",
        "id",
        "CivoNetwork",
        "id",
        "PART_OF_NETWORK",
    ) == {(TEST_VOLUME_ID, TEST_NETWORK_ID)}

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
