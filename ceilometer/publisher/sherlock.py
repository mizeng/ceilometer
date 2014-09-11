__author__ = 'mizeng'

import requests
import socket
import json

from oslo.config import cfg

from ceilometer.openstack.common.gettextutils import _  # noqa
from ceilometer.openstack.common import log
from ceilometer.openstack.common import network_utils
from ceilometer import publisher
from ceilometer.publisher import utils


LOG = log.getLogger(__name__)
#interval for metrics populated to Sherlock, recommended 60s or 600s
interval = 600

class SherlockPublisher(publisher.PublisherBase):
    def __init__(self, parsed_url):
        #aquire host name
        if socket.gethostname().find('.')>=0:
            self.host = socket.gethostname()
        else:
            self.host = socket.gethostbyaddr(socket.gethostname())[0]

    def send_post(post_url, msg):
        headers = {'content-type': 'application/json', 'accept': 'application/json'}
        # get payload from msg
        payload = [{"key":"tagStart","value":{"c3CeilometerProjectId":msg['project_id']}},
                    {"key":"tagStart","value":{"c3CeilometerUserId":msg['user_id']}},
                        {"key":"tagStart","value":{"c3CeilometerMessageID":msg['message_id']}},
                            {"key":"tagStart","value":{"c3CeilometerMessageSignature":msg['message_signature']}},
                                {"key":"tagStart","value":{"c3CeilometerResourceId":msg['resource_id']}},
                                    {"key":"tagStart","value":{"c3CeilometerResourceMatadata":msg['resource_metadata']}},
                                        {"key":"tagStart","value":{"c3CeilometerCounterType":msg['counter_type']}},
                                            {"key":"tagStart","value":{"c3CeilometerCounterUnit":msg['counter_unit']}},
                                                {"key":"tagStart","value":{"c3CeilometerCounterName":msg['counter_name']}},
                                                    {"key":"c3CeilometerCounterVolume","value":msg['counter_volume']},
                                                {"key":"tagEnd","value":""},
                                            {"key":"tagEnd","value":""},
                                        {"key":"tagEnd","value":""},
                                    {"key":"tagEnd","value":""},
                                {"key":"tagEnd","value":""},
                            {"key":"tagEnd","value":""},
                        {"key":"tagEnd","value":""},
                    {"key":"tagEnd","value":""},
                {"key":"tagEnd","value":""}
            ]
        r = requests.post(post_url, data=json.dumps(payload), headers=headers, verify=False)
        LOG.info(r.status_code)
        if r.status_code != requests.codes.ok:
            raise Exception


    def publish_samples(self, context, samples):
        """Send a metering message for publishing

        :param context: Execution context from the service or RPC call
        :param samples: Samples from pipeline after transformation
        """

        for sample in samples:
            msg = utils.meter_message_from_counter(
                sample,
                cfg.CONF.publisher.metering_secret)
            url = 'https://{0}:12020/agent/sendmon/{1}'.format(self.host, interval)
            LOG.info(_("Publishing sample %(msg)s over Sherlock to "
                        "%(url)s") % {'msg': msg, 'url': url})
            try:
                self.send_post(url, msg)
            except Exception as e:
                LOG.warn(_("Unable to send sample over Sherlock"))
                LOG.exception(e)
