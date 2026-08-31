from unittest.mock import patch

import requests

import cartography.intel.civo
import cartography.intel.civo.account
import cartography.intel.civo.firewalls
import cartography.intel.civo.instances
import cartography.intel.civo.ips
import cartography.intel.civo.kubernetes
import cartography.intel.civo.loadbalancers
import cartography.intel.civo.networks
import cartography.intel.civo.sshkeys
import cartography.intel.ontology.publicips
from tests.data.civo.account import QUOTA_RESPONSE
from tests.data.civo.firewalls import FIREWALL_RULES_RESPONSE
from tests.data.civo.firewalls import FIREWALLS_RESPONSE
from tests.data.civo.firewalls import TEST_FIREWALL_ID
from tests.data.civo.instances import INSTANCES_RESPONSE
from tests.data.civo.instances import TEST_INSTANCE_ID
from tests.data.civo.ips import IPS_PAGE
from tests.data.civo.ips import TEST_IP_ID
from tests.data.civo.ips import TEST_LB_IP_ID
from tests.data.civo.ips import TEST_UNASSIGNED_IP_ID
from tests.data.civo.kubernetes import KUBERNETES_CLUSTERS_PAGE
from tests.data.civo.kubernetes import TEST_CLUSTER_ID
from tests.data.civo.loadbalancers import LOAD_BALANCERS_RESPONSE
from tests.data.civo.loadbalancers import TEST_INSTANCE_PRIVATE_IP
from tests.data.civo.loadbalancers import TEST_LOADBALANCER_ID
from tests.data.civo.networks import NETWORKS_RESPONSE
from tests.data.civo.networks import SUBNETS_RESPONSE
from tests.data.civo.networks import TEST_NETWORK_ID
from tests.integration.util import check_nodes
from tests.integration.util import check_rels

TEST_UPDATE_TAG = 123456789
TEST_BASE_URL = "https://api.fake-civo.com"
TEST_ACCOUNT_ID = QUOTA_RESPONSE["id"]
TEST_REGION_CODE = "lon1"
FIREWALLS_BY_REGION = [(firewall, TEST_REGION_CODE) for firewall in FIREWALLS_RESPONSE]
NETWORKS_BY_REGION = [(network, TEST_REGION_CODE) for network in NETWORKS_RESPONSE]


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
    cartography.intel.civo.ips,
    "get",
    return_value=IPS_PAGE["items"],
)
@patch.object(
    cartography.intel.civo.loadbalancers,
    "get",
    return_value=LOAD_BALANCERS_RESPONSE,
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
    cartography.intel.civo.firewalls,
    "get_rules",
    return_value=cartography.intel.civo.firewalls.transform_rules(
        FIREWALL_RULES_RESPONSE,
        TEST_FIREWALL_ID,
    ),
)
@patch.object(
    cartography.intel.civo.firewalls,
    "get",
    return_value=FIREWALLS_BY_REGION,
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
def test_civo_loadbalancer_ip_graph(
    mock_account_get,
    mock_networks_get,
    mock_subnets_get,
    mock_firewalls_get,
    mock_rules_get,
    mock_instances_get,
    mock_kubernetes_get,
    mock_loadbalancers_get,
    mock_ips_get,
    neo4j_session,
):
    """
    Verify the load-balancer/IP graph, including the cross-domain relationships
    owned by the Load Balancers and IPs layer.
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
    cartography.intel.civo.firewalls.sync(
        neo4j_session, api_session, common_job_parameters
    )
    cartography.intel.civo.instances.sync(
        neo4j_session, api_session, common_job_parameters
    )
    cartography.intel.civo.kubernetes.sync(
        neo4j_session, api_session, common_job_parameters
    )

    # Act
    cartography.intel.civo.loadbalancers.sync(
        neo4j_session, api_session, common_job_parameters
    )
    cartography.intel.civo.ips.sync(neo4j_session, api_session, common_job_parameters)
    cartography.intel.ontology.publicips.sync(
        neo4j_session,
        TEST_UPDATE_TAG,
        common_job_parameters,
    )

    # Assert: CivoLoadBalancerBackend loaded, linked to its CivoLoadBalancer.
    backend_id = f"{TEST_LOADBALANCER_ID}/{TEST_INSTANCE_PRIVATE_IP}/http/80/8080"
    assert check_nodes(neo4j_session, "CivoLoadBalancerBackend", ["id", "ip"]) == {
        (backend_id, TEST_INSTANCE_PRIVATE_IP)
    }
    assert check_rels(
        neo4j_session,
        "CivoLoadBalancer",
        "id",
        "CivoLoadBalancerBackend",
        "id",
        "HAS_BACKEND",
    ) == {(TEST_LOADBALANCER_ID, backend_id)}
    assert check_rels(
        neo4j_session,
        "CivoLoadBalancerBackend",
        "id",
        "CivoInstance",
        "id",
        "ROUTES_TO",
    ) == {(backend_id, TEST_INSTANCE_ID)}

    # Assert: CivoLoadBalancerInstancePool loaded with its own routing
    # config preserved (not combined across pools), linked to its load
    # balancer.
    pool_id = f"{TEST_LOADBALANCER_ID}/https/443"
    assert check_nodes(
        neo4j_session,
        "CivoLoadBalancerInstancePool",
        ["id", "protocol", "source_port", "health_check_path"],
    ) == {(pool_id, "https", 443, "/healthz")}
    assert check_rels(
        neo4j_session,
        "CivoLoadBalancer",
        "id",
        "CivoLoadBalancerInstancePool",
        "id",
        "HAS_INSTANCE_POOL",
    ) == {(TEST_LOADBALANCER_ID, pool_id)}

    # Assert: CivoLoadBalancer loaded, with the ontology's ip_address field
    # correctly populated from public_ip.
    assert check_nodes(
        neo4j_session, "CivoLoadBalancer", ["id", "name", "_ont_ip_address"]
    ) == {
        (TEST_LOADBALANCER_ID, "prod-lb", "74.220.16.20"),
    }
    assert check_rels(
        neo4j_session,
        "CivoLoadBalancer",
        "id",
        "CivoFirewall",
        "id",
        "PROTECTED_BY",
    ) == {(TEST_LOADBALANCER_ID, TEST_FIREWALL_ID)}
    assert check_rels(
        neo4j_session,
        "CivoLoadBalancer",
        "id",
        "CivoKubernetesCluster",
        "id",
        "EXPOSES",
    ) == {(TEST_LOADBALANCER_ID, TEST_CLUSTER_ID)}
    assert check_rels(
        neo4j_session,
        "CivoLoadBalancer",
        "id",
        "CivoNetwork",
        "id",
        "PART_OF_NETWORK",
    ) == {(TEST_LOADBALANCER_ID, TEST_NETWORK_ID)}

    # Assert: CivoIP loaded with assigned_to flattened.
    assert check_nodes(neo4j_session, "CivoIP", ["id", "ip", "assigned_to_type"]) == {
        (TEST_IP_ID, "74.220.16.30", "instance"),
        (TEST_LB_IP_ID, "74.220.16.40", "loadbalancer"),
        (TEST_UNASSIGNED_IP_ID, "74.220.16.50", None),
    }

    # Assert: each typed IP assignment resolves to the appropriate target.
    assert check_rels(
        neo4j_session, "CivoIP", "id", "CivoLoadBalancer", "id", "ASSIGNED_TO"
    ) == {(TEST_LB_IP_ID, TEST_LOADBALANCER_ID)}
    assert check_rels(
        neo4j_session, "CivoIP", "id", "CivoInstance", "id", "ASSIGNED_TO"
    ) == {(TEST_IP_ID, TEST_INSTANCE_ID)}

    # Canonical PublicIP provenance is independent of workload assignment, so
    # the unassigned reserved address is linked to its Civo resource as well.
    assert check_nodes(neo4j_session, "PublicIP", ["id"]) == {
        ("74.220.16.30",),
        ("74.220.16.40",),
        ("74.220.16.50",),
    }
    assert check_rels(
        neo4j_session,
        "PublicIP",
        "id",
        "CivoIP",
        "id",
        "RESERVED_BY",
    ) == {
        ("74.220.16.30", TEST_IP_ID),
        ("74.220.16.40", TEST_LB_IP_ID),
        ("74.220.16.50", TEST_UNASSIGNED_IP_ID),
    }
