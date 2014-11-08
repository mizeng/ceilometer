from ceilometer_ebay import cli

__author__ = 'root'
import datetime

import sys
import json

from ceilometer.openstack.common import test
from infra.contrib.frontier import GAUGE
from ceilometer import sample


event_list = [{'msg': {'name': 'test',
                       'type': sample.TYPE_CUMULATIVE,
                       'unit': '',
                       'volume': 1,
                       'user_id': 'test',
                       'project_id': 'test',
                       'resource_id': 'test_run_tasks',
                       'timestamp': datetime.datetime.utcnow().isoformat(),
                       'resource_metadata': {'name': 'TestPublish'},
                       'source': 'testsource', },
               'dimension_list': {'c3_resource_id': 'test_run_tasks', 'c3_project_cos': 'prod',
                                  'compute_node_fqdn': 'ubuntu', 'c3_resource_fqdn': 'vm-brainling.ebay.c3.com',
                                  'c3_hostname': 'vm-brianling-test', 'c3_user_id': 'test', 'c3_project_id': 'test'},
               'metric_list': [('CPU', 100, GAUGE)]},
              {'msg': {'name': 'test',
                       'type': sample.TYPE_CUMULATIVE,
                       'unit': '',
                       'volume': 1,
                       'user_id': 'test',
                       'project_id': 'test',
                       'resource_id': 'test_run_tasks',
                       'timestamp': datetime.datetime.utcnow().isoformat(),
                       'resource_metadata': {'name': 'TestPublish'},
                       'source': 'testsource', },
               'dimension_list': {'c3_resource_id': 'test_run_tasks', 'c3_project_cos': 'prod',
                                  'compute_node_fqdn': 'ubuntu', 'c3_resource_fqdn': 'vm-brainling.ebay.c3.com',
                                  'c3_hostname': 'vm-brianling-test', 'c3_user_id': 'test', 'c3_project_id': 'test'},
               'metric_list': [('CPU', 100, GAUGE)]},
              {'msg': {'name': 'test',
                       'type': sample.TYPE_CUMULATIVE,
                       'unit': '',
                       'volume': 1,
                       'user_id': 'test',
                       'project_id': 'test',
                       'resource_id': 'test_run_tasks',
                       'timestamp': datetime.datetime.utcnow().isoformat(),
                       'resource_metadata': {'name': 'TestPublish'},
                       'source': 'testsource', },
               'dimension_list': {'c3_resource_id': 'test_run_tasks', 'c3_project_cos': 'prod',
                                  'compute_node_fqdn': 'ubuntu', 'c3_resource_fqdn': 'vm-brainling.ebay.c3.com',
                                  'c3_hostname': 'vm-brianling-test', 'c3_user_id': 'test', 'c3_project_id': 'test'},
               'metric_list': [('CPU', 100, GAUGE)]}]

sys.argv = ['test_sherlock_req', '--host', 'sherlock-ftr-qa.stratus.phx.qa.ebay.com', '--port', '80', '--tenant', 'pp',
            '--env', 'qa', '--app_svc', 'PyInfra', '--profile', 'PythonInfraDev', '--event',
            json.dumps(event_list)]


class TestSherlockPublisher(test.BaseTestCase):
    def test_sherlock_req(self):
        cli.send_sherlock_req()