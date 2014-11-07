__author__ = 'lzhijun'
import sys
from oslo.config import cfg
from ceilometer.openstack.common import gettextutils
from ceilometer.openstack.common import log
from ceilometer.openstack.common import rpc

LOG = log.getLogger(__name__)


def prepare_service(argv=None):
    gettextutils.install('ceilometer', lazy=True)
    gettextutils.enable_lazy()
    rpc.set_defaults(control_exchange='ceilometer')
    log_levels = (cfg.CONF.default_log_levels +
                  ['stevedore=INFO', 'keystoneclient=INFO', 'ceilometer_ebay=INFO'])
    cfg.set_defaults(log.log_opts,
                     default_log_levels=log_levels)
    if argv is None:
        argv = sys.argv
    cfg.CONF(argv[1:], project='ceilometer')
    #cfg.CONF.set_override('verbose', True)
    log.setup('ceilometer')


def send_sherlock_req():
    prepare_service(['send_sherlock_req'])
    from ceilometer_ebay.sherlock.sherlock_client import SherlockClient
    client = SherlockClient()
    client.send_metrics()