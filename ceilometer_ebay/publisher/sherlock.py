__author__ = 'lzhijun'

import urlparse
import socket
import subprocess
import json

from oslo.config import cfg
from ceilometer.openstack.common.gettextutils import _  # noqa
from ceilometer.openstack.common import log
from ceilometer import publisher
from ceilometer.publisher import utils
from ceilometer import sample
from ceilometer.openstack.common import network_utils
import gevent

LOG = log.getLogger(__name__)


class SherlockPublisher(publisher.PublisherBase):
    """
        based on the below sample_key -> sherlock_dimension_key pair to converter sample info to sherlock dimension list
    """
    keyword_list_for_sherlock_dimension = [('project_id', 'c3_project_id'),
                                           ('user_id', 'c3_user_id'),
                                           ('resource_id', 'c3_resource_id'),
                                           ('count_unit', 'c3_counter_unit'),
                                           ('resource_metadata#project_cos', 'c3_project_cos'),
                                           ('resource_metadata#hostname', 'c3_hostname'),
                                           ('resource_metadata#fqdn', 'c3_resource_fqdn'),
                                           ('resource_metadata#mpt_environment', 'c3_mpt_environment')]

    def __init__(self, parsed_url):
        super(self.__class__, self).__init__(parsed_url)
        assert parsed_url.scheme, 'target scheme should be non-empty'
        assert parsed_url.scheme.lower() == 'sherlock', "target publisher scheme should be 'sherlock'"
        assert parsed_url.netloc, 'target netloc should be non-empty'

        self.host, self.port = network_utils.parse_host_port(
            parsed_url.netloc, 80)
        self.frontier = None

        # Handling other configuration options in the query string
        if parsed_url.query:
            params = urlparse.parse_qs(parsed_url.query)
            try:
                self.tenant = str(params.get('tenant')[0])
                self.env = str(params.get('env')[0])
                self.app_svc = str(params.get('app_svc')[0])
                self.profile = str(params.get('profile')[0])
                self.maxsize = int(params.get('maxsize', [10000])[0])
                self.log_level = int(params.get('log_level', [2])[0])
                self.timeout = float(params.get('timeout', [30.0])[0])
                self.thread_num = float(params.get('thread_num', [10])[0])
            except ValueError:
                LOG.error(_(
                    "sherlock tenant, env,app_svc and profile's data type should be string. "
                    "And sherlock maxsize's data type should be long. timeout's data type should be int."))
                return

    @staticmethod
    def extract_dimension_value(msg, sample_key):
        dimension_value = None
        if sample_key:

            dimension_value = msg
            for keyword in sample_key.split('#'):
                dimension_value = dimension_value.get(keyword, {})
                if not dimension_value:
                    break
        return dimension_value

    @staticmethod
    def extract_metrics(msg):
        from infra.contrib.frontier import GAUGE, COUNTER

        metrics_name = msg['counter_name']
        metrics_value = msg['counter_volume']
        metrics_type = msg['counter_type']
        if metrics_type in (sample.TYPE_GAUGE, metrics_type == sample.TYPE_DELTA):
            return [(metrics_name, metrics_value, GAUGE)]
        elif metrics_type == sample.TYPE_CUMULATIVE:
            return [(metrics_name, metrics_value, COUNTER)]

    def convert_msg_to_sherlock_metrics(self, msg):
        dimension_dict = {'compute_node_fqdn': socket.getfqdn()}
        metrics_list = []
        if msg:
            for sample_key, sherlock_key in self.keyword_list_for_sherlock_dimension:
                dimension_value = SherlockPublisher.extract_dimension_value(msg, sample_key)
                if dimension_value:
                    dimension_dict.update({sherlock_key: dimension_value})
            metrics_list = SherlockPublisher.extract_metrics(msg)

        return dimension_dict, metrics_list

    def run_sub_process(self, sherlock_event_list):
        subprocess.call(
            ['ceilometer-sherlock-request', '--host', self.host, '--port', str(self.port), '--tenant', self.tenant,
             '--env', self.env, '--app_svc', self.app_svc, '--profile', self.profile, '--event',
             json.dumps(sherlock_event_list)])

    def publish_samples(self, context, samples):
        """Send a metering message for publishing

        :param context: Execution context from the service or RPC call
        :param samples: Samples from pipeline after transformation
        """
        sherlock_event_list = list()
        for meter_sample in samples:
            msg = utils.meter_message_from_counter(
                meter_sample,
                cfg.CONF.publisher.metering_secret)
            dimension_list, metric_list = self.convert_msg_to_sherlock_metrics(msg)
            if metric_list and len(metric_list) > 0:
                sherlock_event_list.append({'msg': msg, 'dimension_list': dimension_list, 'metric_list': metric_list})
        if len(sherlock_event_list) > 0:
            gevent.joinall([gevent.spawn(self.run_sub_process, sherlock_event_list)],
                           len(sherlock_event_list) * self.timeout)