# -*- encoding: utf-8 -*-
#
# Copyright © 2014 eBay, Inc
#
# Authors: Brian Ling <Ling.ZhiJun@ebay.com>
#          Bryant Zeng <mizeng@ebay.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Sherlock storage backend
"""

import requests
import pymongo
from ceilometer.openstack.common import log
from ceilometer.openstack.common.gettextutils import _  # noqa
from ceilometer.storage import base
from ceilometer.storage import models
from ceilometer.storage import pymongo_base
from datetime import datetime
import six.moves.urllib.parse as urlparse
import time
import json


LOG = log.getLogger(__name__)


def send_get_data_points(parsed_url, limit=None):
        headers = {'content-type': 'application/json', 'accept': 'application/json'}
        r = requests.get(parsed_url, headers=headers)
        if r.status_code != requests.codes.ok:
            print 'Query Sherlock returned failed'

        data_points = r.json()[0]['DataPoints']
        data_points_length = len(data_points)
        #fetch result according to the limit
        if limit is None:
            limit = 0
        if limit != 0 and data_points_length > limit:
            return data_points[data_points_length-limit:]
        return data_points

def send_get_tags(parsed_url):
    headers = {'content-type': 'application/json', 'accept': 'application/json'}
    r = requests.get(parsed_url, headers=headers)
    if r.status_code != requests.codes.ok:
        print 'Query Sherlock returned failed'

    tags = r.json()[0]['Tags']
    return tags

def make_timestamp_range(start, end,
                         start_timestamp_op=None, end_timestamp_op=None):

    """Given two possible datetimes and their operations, create the query
    document to find timestamps within that range.
    By default, using $gte for the lower bound and $lt for the
    upper bound.
    """
    ts_range = {}

    if start:
        if start_timestamp_op == 'gt':
            start_timestamp_op = '$gt'
        else:
            start_timestamp_op = '$gte'
        ts_range[start_timestamp_op] = start

    if end:
        if end_timestamp_op == 'le':
            end_timestamp_op = '$lte'
        else:
            end_timestamp_op = '$lt'
        ts_range[end_timestamp_op] = end
    return ts_range


def make_query_from_filter(sample_filter, require_meter=True):
    """Return a query dictionary based on the settings in the filter.

    :param filter: SampleFilter instance
    :param require_meter: If true and the filter does not have a meter,
                          raise an error.
    """
    q = {}

    if sample_filter.user:
        q['user_id'] = sample_filter.user
    if sample_filter.project:
        q['project_id'] = sample_filter.project

    if sample_filter.meter:
        q['counter_name'] = sample_filter.meter
    elif require_meter:
        raise RuntimeError('Missing required meter specifier')

    ts_range = make_timestamp_range(sample_filter.start,
                                    sample_filter.end,
                                    sample_filter.start_timestamp_op,
                                    sample_filter.end_timestamp_op)

    if ts_range:
        q['timestamp'] = ts_range

    if sample_filter.resource:
        q['resource_id'] = sample_filter.resource
    if sample_filter.source:
        q['source'] = sample_filter.source
    if sample_filter.message_id:
        q['message_id'] = sample_filter.message_id

    # so the samples call metadata resource_metadata, so we convert
    # to that.
    q.update(dict(('resource_%s' % k, v)
                  for (k, v) in sample_filter.metaquery.iteritems()))
    return q

class SherlockStorage(base.StorageEngine):
    """
    Put the data directly to Sherlock(Backend: OpenTSDB) with Sherlock Python Client
    """
    @staticmethod
    def get_connection(conf):
        """Return a Connection instance based on the configuration settings.
        """
        return Connection(conf)


AVAILABLE_CAPABILITIES = {
    'meters': {'query': {'simple': True,
                         'metadata': True}},
    'resources': {'query': {'simple': True,
                            'metadata': True}},
    'samples': {'query': {'simple': True,
                          'metadata': True}},
    'statistics': {'query': {'simple': True,
                             'metadata': True},
                   'aggregation': {'standard': True}},
}


class Connection(base.Connection):
    """Sherlock connection.
    """
    CONNECTION_POOL = pymongo_base.ConnectionPool()

    _GENESIS = datetime(year=2014, month=9, day=1, hour=12)
    _APOCALYPSE = datetime(year=9999, month=12, day=31,
                                    hour=23, minute=59, second=59)
    def __init__(self, conf):
        """Sherlock Connection Initialization."""
        # Since we are using pymongo, even though we are connecting to DB2
        # we still have to make sure that the scheme which used to distinguish
        # db2 driver from mongodb driver be replaced so that pymongo will not
        # produce an exception on the scheme.
        url = conf.database.connection
        mongo_url = url.replace('sherlock:', 'mongodb:', 1).split('#',1)[0]
        self.conn = self.CONNECTION_POOL.connect(mongo_url)

        connection_options = pymongo.uri_parser.parse_uri(mongo_url)
        self.mongo_host =  connection_options['nodelist'][0][0]
        self.db = getattr(self.conn, connection_options['database'])

        # Note that url is usually consist of 2 section: mongodb and sherlock
        # Sample:connection=sherlock://ceilometer:ceilometer_pass@10.9.205.221:27017/ceilometer\
        # #http://cmevpsqry.vip.stratus.slc.ebay.com:8080/q?
        self.sherlock_url = urlparse.urlparse(url).fragment

    def upgrade(self):
        pass

    def clear(self):
        self.conn.close()

    def _get_floating_resources(self, query, resource, limit=10):
        """Return an iterable of models.Resource instances unconstrained
           by timestamp.

        :param query: project/user/source query
        :param limit: maximum number of items to return. If user not defined, default set to 10
        :param resource: resource filter(resource id) , as well as _id in Mongo Collection.
        """
        if resource is not None:
            query['_id'] = resource

        for r in self.db.resource.find(query, limit=limit):
            yield models.Resource(
                resource_id=r['_id'],
                user_id=r['user_id'],
                project_id=r['project_id'],
                first_sample_timestamp=r.get('first_sample_timestamp',
                                             self._GENESIS),
                last_sample_timestamp=r.get('last_sample_timestamp',
                                            self._APOCALYPSE),
                source=r['source'],
                metadata=r['metadata'])

    def get_resources(self, user=None, project=None, source=None, resource=None, limit=10):
        """
        Web API is like /v2/resources
        :param limit: maximum number of items to return. If user not defined, default set to 10
        :return: definitions of all the resources which is a json array
        """
        query = {}
        if user is not None:
            query['user_id'] = user
        if project is not None:
            query['project_id'] = project
        if source is not None:
            query['source'] = source

        return self._get_floating_resources(query, resource)
        for resource_content in resource_contents:
            resource_id = resource_content['_id']

            # Below Section is to format query sherlock as user requested
            #interval : recommend 60s or 300s or 600s
            start = '2014-09-01T12:00:00'
            start_timestamp = int(time.mktime(time.strptime(start,'%Y-%m-%dT%H:%M:%S')))
            aggregator = 'avg'
            metricName = 'stratus.sys.cpu_util'
            interval = '600s'
            # groupBy = 'fqdn=*'+',c3CeilometerResourceId={0}'.format(resource_id)
            groupBy = 'fqdn=*'+',c3CeilometerResourceId={0}'.format('aad43446-4018-44ac-8423-1d4eec5fd0fd')
            url = 'http://cmevpsqry.vip.stratus.slc.ebay.com:8080/q?start={0}&m={1}:{2}.STATE.{3}{{{4}}}&format=json'\
            .format(start_timestamp, aggregator, metricName, interval, groupBy)
            data_points = send_get_data_points(url)

            #format output
            user_id = resource_content['user_id']
            project_id = resource_content['project_id']
            metadata = resource_content['metadata']

            first_sample_timestamp = time.strftime('%Y-%m-%dT%H-%M-%S',time.gmtime(data_points[0][0]))
            last_sample_timestamp = time.strftime('%Y-%m-%dT%H-%M-%S',time.gmtime(data_points[-1][0]))



    def get_meters(self, user=None, project=None, resource=None, source=None,
                  metaquery={}, pagination=None):
        """Return an iterable of models.Meter instances

        :param user: Optional ID for user that owns the resource.
        :param project: Optional ID for project that owns the resource.
        :param resource: Optional resource filter.
        :param source: Optional source filter.
        :param metaquery: Optional dict with metadata to match on.
        :param pagination: Optional pagination query.
        """
        if pagination:
            raise NotImplementedError(_('Pagination not implemented'))

        q = {}
        if user is not None:
            q['user_id'] = user
        if project is not None:
            q['project_id'] = project
        if resource is not None:
            q['_id'] = resource
        if source is not None:
            q['source'] = source
        q.update(metaquery)

        for r in self.db.resource.find(q):
            for r_meter in r['meter']:
                yield models.Meter(
                    name=r_meter['counter_name'],
                    type=r_meter['counter_type'],
                    # Return empty string if 'counter_unit' is not valid for
                    # backward compatibility.
                    unit=r_meter.get('counter_unit', ''),
                    resource_id=r['_id'],
                    project_id=r['project_id'],
                    source=r['source'],
                    user_id=r['user_id'],
                )

    def get_meter_statistics(self, meter_name):
        """
        Web API is like /v2/meters/cpu_util/statistics
        :param meter_name: the meter which will be calculate its statistics
        :return: an iterable of models.Statistics instance containing meter
        statistics described by the query parameters.
        """
        #get counter volume from sherlock
        # Below Section is to format query sherlock as user requested
        #interval : recommend 60s or 300s or 600s
        start = '2014-09-12T12:00:00'
        end = '2014-09-12T13:00:00'
        start_timestamp = int(time.mktime(time.strptime(start,'%Y-%m-%dT%H:%M:%S')))
        end_timestamp = int(time.mktime(time.strptime(end,'%Y-%m-%dT%H:%M:%S')))
        aggregator = 'avg'
        metricName = 'stratus.sys.'+meter_name
        period = interval = 600
        # groupBy = 'fqdn=*'+',c3CeilometerResourceId={0}'.format(resource_id)
        groupBy = 'fqdn=*'+',c3CeilometerResourceId={0}'.format('aad43446-4018-44ac-8423-1d4eec5fd0fd')
        url = 'http://cmevpsqry.vip.stratus.slc.ebay.com:8080/q?start={0}&end={1}&m={2}:{3}.STATE.{4}s{{{5}}}&format=json'\
        .format(start_timestamp, end_timestamp, aggregator, metricName, interval, groupBy)
        data_points = send_get_data_points(url)

        count_value = len(data_points)
        value_point_list = []
        total = 0
        for data_point in data_points:
            value_point_list.append(data_point[1])
            total += data_point[1]

        min_value  = min(value_point_list)
        max_value  = max(value_point_list)
        sum_value = total
        avg_value = sum_value/count_value

        duration_start = datetime.fromtimestamp(data_points[0][0]).strftime('%Y-%m-%dT%H:%M:%S')
        duration_end = datetime.fromtimestamp(data_points[-1][0]).strftime('%Y-%m-%dT%H:%M:%S')
        duration = data_points[-1][0] - data_points[0][0]
        unit = send_get_tags(url)['c3CeilometerCounterUnit']
        result = {'count': count_value, 'duration_start': duration_start, 'duration_end': duration_end, 'duration': duration,\
                  'min': min_value, 'max': max_value, 'sum': sum_value, 'avg': avg_value, 'period': period, 'unit': unit}
        return json.dumps(result)

    def _retrieve_samples(self, query, limit):
        # Notice that counter_name mapping to meter.counter_name in Resource Mongo Collection
        # We need to query Resource Collection to get all the info expert counter_volume and timestamp
        # which we will get in Sherlock
        query_for_resource = {}
        if query.has_key('counter_name'):
           query_for_resource['meter.counter_name'] = query['counter_name']

        resource_content = self.db.resource.find(query_for_resource)
        samples = []

        for r in resource_content:
            user_id = r['user_id']
            resource_id = r['_id']
            project_id = r['project_id']
            message_id = r.get('message_id','')
            source = r['source']
            resource_metadata = r['metadata']

            # Get counter volume and timestamp from sherlock
            # Below Section is to format query sherlock as user requested
            # interval : recommend 60s or 300s or 600s
            start = '2014-09-12T12:00:00'
            start_timestamp = int(time.mktime(time.strptime(start,'%Y-%m-%dT%H:%M:%S')))
            end = '2014-09-12T13:00:00'
            end_timestamp = int(time.mktime(time.strptime(end,'%Y-%m-%dT%H:%M:%S')))
            aggregator = 'avg'
            metricName = 'stratus.sys.cpu_util'
            interval = '600s'
            # groupBy = 'fqdn=*'+',c3CeilometerResourceId={0}'.format(resource_id)
            groupBy = 'fqdn=*'+',c3CeilometerResourceId={0}'.format('aad43446-4018-44ac-8423-1d4eec5fd0fd')
            url = self.sherlock_url+'start={0}&end={1}&m={2}:{3}.STATE.{4}{{{5}}}&format=json'\
            .format(start_timestamp, end_timestamp, aggregator, metricName, interval, groupBy)
            data_points = send_get_data_points(url, limit=limit)
            for data_point in data_points:
                counter_volume = data_point[1]
                timestamp = datetime.fromtimestamp(int (data_point[0]))
                for i_meter in r['meter']:
                    if i_meter['counter_name'] == query['counter_name']:
                        counter_unit = i_meter.get('counter_unit', '')
                        counter_name = i_meter['counter_name']
                        counter_type = i_meter['counter_type']
                        sample = {'counter_name': counter_name, 'user_id': user_id, 'resource_id': resource_id, 'timestamp': timestamp,\
                          'message_id': message_id, 'source': source, 'counter_unit': counter_unit, 'counter_volume': counter_volume, \
                          'project_id': project_id, 'counter_type': counter_type, 'resource_metadata': resource_metadata,\
                          'recorded_at': timestamp}
                        samples.append(sample)

        for s in samples:
            # Backward compatibility for samples without units
            # s['counter_unit'] = s.get('counter_unit', '')
            # Tolerate absence of recorded_at in older datapoints
            s['message_signature'] = s.get('message_signature', '')
            yield models.Sample(**s)

    def get_samples(self, sample_filter, limit=5):
        """Return an iterable of model.Sample instances.

        :param sample_filter: Filter.
        :param limit: Maximum number of items per resource to return. default set to 5
        """
        if limit == 0:
            return []
        q = make_query_from_filter(sample_filter,
                                   require_meter=False)

        return self._retrieve_samples(q,limit)


# if __name__ == "__main__":
#
#     # Below Section is to format query sherlock as user requested
#     #interval : recommend 60s or 300s or 600s
#     start = '2014/09/16-12:00:00'
#     end = '2014/09/16-12:10:00'
#     aggregator = 'avg'
#     metricName = 'stratus.sys.stratusHypervisorCpuUsageMaximumPercentile'
#     interval = '600s'
#     groupBy = 'stratusHypervisorLocatedReservedResource=RR-Eval'
#
#
#     url = 'http://cmevpsqry.vip.stratus.slc.ebay.com:8080/q?start={0}&end={1}&m={2}:{3}.STATE.{4}{{{5}}}&format=json'\
#         .format(start, end, aggregator, metricName, interval, groupBy)
#
#     print url
#     SherlockStorage.calculate_single_point('avg', url)
