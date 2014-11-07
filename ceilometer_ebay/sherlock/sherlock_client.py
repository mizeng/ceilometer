__author__ = 'root'

import sys
import json

from oslo.config.cfg import ConfigOpts

from oslo.config import cfg
from ceilometer.openstack.common.gettextutils import _  # noqa
from ceilometer.openstack.common import log
import infra
import infra.async
import infra.ll
import infra.contrib.frontier



LOG = log.getLogger(__name__)

sherlock_config = ConfigOpts()


class SherlockClient(object):
    def __init__(self):
        sherlock_config.register_cli_opts([
            cfg.StrOpt('env',
                       required=True,
                       help='designate sherlock parameter environment: --env <env>',
            ),
            cfg.StrOpt('tenant',
                       required=True,
                       help='designate sherlock parameter tenant: --tenant <tenant>'),
            cfg.StrOpt('host',
                       required=True,
                       help='designate sherlock parameter host: --host <host>',
            ),
            cfg.IntOpt('port',
                       default=80,
                       help='designate sherlock parameter port: --port <port>'),
            cfg.StrOpt('profile',
                       required=True,
                       help='designate sherlock parameter host: --profile <profile>',
            ),
            cfg.StrOpt('app_svc',
                       required=True,
                       help='designate sherlock parameter app_svc: --app_svc <app_svc>'),
            cfg.IntOpt('maxsize',
                       default=10000,
                       help='designate sherlock parameter maxsize: --maxsize <maxsize>',
            ),
            cfg.IntOpt('log_level',
                       default=2,
                       help='designate sherlock parameter log_level: --log_level <log_level>',
            ),
            cfg.FloatOpt('timeout',
                         default=30.0,
                         help='designate sherlock parameter timeout: --timeout <timeout>',
            ),
            cfg.IntOpt('thread_num',
                       default=10,
                       help='designate sherlock parameter thread_num: --thread_num <thread_num>'),
            cfg.StrOpt('event',
                       required=True,
                       help='designate sherlock parameter event: --event <event>'),
        ])
        sherlock_config(sys.argv[1:])
        self.host = sherlock_config.host
        self.tenant = sherlock_config.tenant
        self.port = sherlock_config.port
        self.env = sherlock_config.env
        self.app_svc = sherlock_config.app_svc
        self.timeout = sherlock_config.timeout
        self.profile = sherlock_config.profile
        self.maxsize = sherlock_config.maxsize
        self.log_level = sherlock_config.log_level
        self.thread_pool = Pool(sherlock_config.thread_num)
        infra.ll.set_log_level(self.log_level)
        self.frontier = infra.contrib.frontier.Frontier(host=self.host, port=self.port,
                                                            tenant=self.tenant,
                                                            env=self.env,
                                                            app_svc=self.app_svc,
                                                            profile=self.profile, maxsize=self.maxsize,
                                                            timeout=self.timeout)
        LOG.info(_("finish to initialize sherlock publisher"))
        self.sherlock_event_list = json.loads(sherlock_config.event)

    def send_metrics(self):
        def _send_sherlock_metrics(sherlock_event):
            try:
                self.frontier.send(dimension_list=sherlock_event['dimension_list'],
                              metric_list=sherlock_event['metric_list'])
                LOG.info(_(
                        "succeed publishing sample message over sherlock. details: [message: %(msg)s tenant: %(tenant)s env: %(env)s  ] ") % {
                                 'msg': sherlock_event['msg'], 'tenant': self.tenant, 'env': self.env})
            except Exception as e:
                LOG.error(_("Unable to send sample over sherlock"))
                LOG.exception(e)
                LOG.info(_(
                        "failed to publish sample message over sherlock. details: [message: %(msg)s tenant: %(tenant)s env: %(env)s  ] ") % {
                                 'msg': sherlock_event['msg'], 'tenant': self.tenant, 'env': self.env})


        if len(self.sherlock_event_list) > 0:
            event_task_list = [infra.async.spawn(_send_sherlock_metrics, sherlock_event) for sherlock_event in self.sherlock_event_list]
            infra.async.gevent.joinall(event_task_list)