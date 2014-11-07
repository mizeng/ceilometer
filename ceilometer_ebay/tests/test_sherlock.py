__author__ = 'lzhijun'
import datetime

from ceilometer.openstack.common import test
from ceilometer_ebay.publisher import sherlock
from ceilometer.openstack.common import network_utils
from ceilometer import sample
from ceilometer import publisher
import infra

COUNTER_SOURCE = 'testsource'
#eventlet.monkey_patch(socket=True, select=True, thread=True)


class TestSherlockPublisher(test.BaseTestCase):
    test_data = [
        sample.Sample(
            name = 'test',
            type = sample.TYPE_CUMULATIVE,
            unit = '',
            volume = 1,
            user_id = 'test',
            project_id = 'test',
            resource_id = 'test_run_tasks',
            timestamp = datetime.datetime.utcnow().isoformat(),
            resource_metadata = {'name': 'TestPublish'},
            source = COUNTER_SOURCE,
        ),
        sample.Sample(
            name = 'test',
            type = sample.TYPE_CUMULATIVE,
            unit = '',
            volume = 1,
            user_id = 'test',
            project_id = 'test',
            resource_id = 'test_run_tasks',
            timestamp = datetime.datetime.utcnow().isoformat(),
            resource_metadata = {'name': 'TestPublish'},
            source = COUNTER_SOURCE,
        ),
        sample.Sample(
            name = 'test2',
            type = sample.TYPE_CUMULATIVE,
            unit = '',
            volume = 1,
            user_id = 'test',
            project_id = 'test',
            resource_id = 'test_run_tasks',
            timestamp = datetime.datetime.utcnow().isoformat(),
            resource_metadata = {'name': 'TestPublish'},
            source = COUNTER_SOURCE,
        ),
        sample.Sample(
            name = 'test2',
            type = sample.TYPE_CUMULATIVE,
            unit = '',
            volume = 1,
            user_id = 'test',
            project_id = 'test',
            resource_id = 'test_run_tasks',
            timestamp = datetime.datetime.utcnow().isoformat(),
            resource_metadata = {'name': 'TestPublish'},
            source = COUNTER_SOURCE,
        ),
        sample.Sample(
            name = 'test3',
            type = sample.TYPE_DELTA,
            unit = '',
            volume = 1,
            user_id = 'test',
            project_id = 'test',
            resource_id = 'test_run_tasks',
            timestamp = datetime.datetime.utcnow().isoformat(),
            resource_metadata = {'name': 'TestPublish'},
            source = COUNTER_SOURCE,
        ),
        sample.Sample(
            name = 'test3-c3',
            type = sample.TYPE_GAUGE,
            unit = '',
            volume = 1,
            user_id = 'test',
            project_id = 'test',
            resource_id = 'test_run_tasks',
            timestamp = datetime.datetime.utcnow().isoformat(),
            resource_metadata = {'project_cos': 'prod', 'hostname':'vm-brianling-test', 'fqdn':'vm-brainling.ebay.c3.com', 'mpt.environment':'mp'},
            source = COUNTER_SOURCE,
            ),
    ]

    def test_sherlock_url_parse(self):
        publisher = sherlock.SherlockPublisher(network_utils.urlsplit(
            'sherlock://sherlock-ftr-qa.stratus.phx.qa.ebay.com:80?tenant=pp&env=qa&app_svc=PyInfra&profile=PythonInfraDev&timeout=10.0&log_level=1'));
        self.assertEqual('sherlock-ftr-qa.stratus.phx.qa.ebay.com', publisher.host)
        self.assertEqual(80, publisher.port)
        self.assertEqual('pp', publisher.tenant)
        self.assertEqual('qa', publisher.env)
        self.assertEqual('PyInfra', publisher.app_svc)
        self.assertEqual('PythonInfraDev', publisher.profile)
        self.assertEqual(10000, publisher.maxsize)
        self.assertEqual(10.0, publisher.timeout)
        self.assertEqual(1, publisher.log_level)
        start_time = datetime.datetime.now()
        print "consumed time: {time}".format(time = datetime.datetime.now() - start_time)

    def test_sherlock(self):
        publisher_1 = sherlock.SherlockPublisher(network_utils.urlsplit(
            'sherlock://sherlock-ftr-qa.stratus.phx.qa.ebay.com?tenant=pp&env=qa&app_svc=PyInfra&profile=PythonInfraDev'));
        self.assertEqual('sherlock-ftr-qa.stratus.phx.qa.ebay.com', publisher_1.host)
        self.assertEqual(80, publisher_1.port)
        self.assertEqual('pp', publisher_1.tenant)
        self.assertEqual('qa', publisher_1.env)
        self.assertEqual('PyInfra', publisher_1.app_svc)
        self.assertEqual('PythonInfraDev', publisher_1.profile)
        self.assertEqual(10000, publisher_1.maxsize)
        self.assertEqual(30.0, publisher_1.timeout)
        self.assertEqual(2, publisher_1.log_level)
        start_time = datetime.datetime.now()
        publisher_1.publish_samples(None, self.test_data)
        print "consumed time: {time}".format(time = datetime.datetime.now() - start_time)
        publisher_2 = sherlock.SherlockPublisher(network_utils.urlsplit(
            'sherlock://sherlock-ftr-qa.stratus.phx.qa.ebay.com?tenant=pp&env=qa&app_svc=PyInfra&profile=PythonInfraDev'));
        self.assertIsNot(publisher_2.get_frontier(), publisher_1.get_frontier())
        self.assertEqual(publisher_1.get_frontier(), publisher_1.get_frontier())
        self.assertEqual(publisher_2.get_frontier(), publisher_2.get_frontier())

    def test_sherlock_prod_with_single_instance(self):
        publisher = sherlock.SherlockPublisher(network_utils.urlsplit(
            'sherlock://sherlock-ftr-mp-phx.vip.ebay.com:80?tenant=mp&env=prod&app_svc=c3-metrics&profile=c3-metrics&maxsize=10000&timeout=30.0&log_level=2'));
        self.assertEqual('sherlock-ftr-mp-phx.vip.ebay.com', publisher.host)
        self.assertEqual(80, publisher.port)
        self.assertEqual('mp', publisher.tenant)
        self.assertEqual('prod', publisher.env)
        self.assertEqual('c3-metrics', publisher.app_svc)
        self.assertEqual('c3-metrics', publisher.profile)
        self.assertEqual(10000, publisher.maxsize)
        self.assertEqual(30.0, publisher.timeout)
        self.assertEqual(2, publisher.log_level)
        start_time = datetime.datetime.now()
        publisher.publish_samples(None, self.test_data)
        print "consumed time: {time}".format(time = datetime.datetime.now() - start_time)

    def test_sherlock_prod_with_multiple_instance(self):
        infra.reset()
        infra.ll.set_log_level(2)
        publisher_1 = publisher.get_publisher('sherlock://sherlock-ftr-mp-phx.vip.ebay.com:80?tenant=mp&env=prod&app_svc=c3-metrics&profile=c3-metrics&maxsize=10000&timeout=30.0&log_level=2')
        self.assertIsNotNone(publisher_1)
        publisher_2 = publisher.get_publisher('sherlock://sherlock-ftr-mp-phx.vip.ebay.com:80?tenant=mp&env=prod&app_svc=c3-metrics&profile=c3-metrics&maxsize=10000&timeout=30.0&log_level=2')
        self.assertIsNotNone(publisher_2)
        start_time = datetime.datetime.now()
        publisher_1.publish_samples(None, self.test_data)
        publisher_2.publish_samples(None, self.test_data)
        print "consumed time: {time}".format(time = datetime.datetime.now() - start_time)