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
                       'source': 'testsource', }, 'dimension_list': {'profile_id': 11},
               'metric_list': {'counter_name': 'cpu_ratio', 'counter_volume': 100, 'counter_type': GAUGE}},
              {'msg': {'name': 'test',
                       'type': sample.TYPE_CUMULATIVE,
                       'unit': '',
                       'volume': 1,
                       'user_id': 'test',
                       'project_id': 'test',
                       'resource_id': 'test_run_tasks',
                       'timestamp': datetime.datetime.utcnow().isoformat(),
                       'resource_metadata': {'name': 'TestPublish'},
                       'source': 'testsource', }, 'dimension_list': {'profile_id': 11},
               'metric_list': {'counter_name': 'cpu_ratio', 'counter_volume': 100, 'counter_type': GAUGE}},
              {'msg': {'name': 'test',
                       'type': sample.TYPE_CUMULATIVE,
                       'unit': '',
                       'volume': 1,
                       'user_id': 'test',
                       'project_id': 'test',
                       'resource_id': 'test_run_tasks',
                       'timestamp': datetime.datetime.utcnow().isoformat(),
                       'resource_metadata': {'name': 'TestPublish'},
                       'source': 'testsource', }, 'dimension_list': {'profile_id': 11},
               'metric_list': {'counter_name': 'cpu_ratio', 'counter_volume': 100, 'counter_type': GAUGE}}]

sys.argv = ['test_sherlock_req', '--host', 'sherlock-ftr-qa.stratus.phx.qa.ebay.com', '--port', '80', '--tenant', 'pp',
            '--env', 'qa', '--app_svc', 'PyInfra', '--profile', 'PythonInfraDev', '--event',
            json.dumps(event_list)]


class TestSherlockPublisher(test.BaseTestCase):
    def test_sherlock_req(self):
        cli.send_sherlock_req()