__author__ = 'lzhijun'
import sys
import tarfile
import tempfile
from HTMLParser import HTMLParser
import urlparse
from optparse import OptionParser

import os
import ssl_support
import stat
import re


HOME = os.environ.get('PYINFRA_HOME', os.path.expanduser('~'))
PYINFRA = os.path.join(HOME, '.pyinfra')
CA_BUNDLE = os.path.join(PYINFRA, 'ebay.cabundle')
INDEX = 'https://pypi.corp.ebay.com/pythoninfra/production/+simple/'



class mkdtemp(object):
    def __init__(self, cd = False, **kwargs):
        self.cd = cd
        self.kwargs = kwargs
        self._orig_dir = None

    def __enter__(self):
        self.tmpdir = tempfile.mkdtemp(**self.kwargs)
        if self.cd:
            self._orig_dir = os.getcwd()
            os.chdir(self.tmpdir)
        return self.tmpdir

    def __exit__(self, *exc_info):
        if self._orig_dir:
            os.chdir(self._orig_dir)
        rmtree(self.tmpdir)

def rmtree(path, ignore_errors = False, onerror = None):
        """Recursively delete a directory tree.

        If ignore_errors is set, errors are ignored; otherwise, if onerror
        is set, it is called to handle the error with arguments (func,
        path, exc_info) where func is os.listdir, os.remove, or os.rmdir;
        path is the argument to that function that caused it to fail; and
        exc_info is a tuple returned by sys.exc_info().  If ignore_errors
        is false and onerror is None, an exception is raised.

        """
        if ignore_errors:
            def onerror(*args):
                pass
        elif onerror is None:
            def onerror(*args):
                raise
        try:
            if os.path.islink(path):
                # symlinks to directories are forbidden, see bug #1669
                raise OSError("Cannot call rmtree on a symbolic link")
        except OSError:
            onerror(os.path.islink, path, sys.exc_info())
            # can't continue even if onerror hook returns
            return
        names = []
        try:
            names = os.listdir(path)
        except os.error, err:
            onerror(os.listdir, path, sys.exc_info())
        for name in names:
            fullname = os.path.join(path, name)
            try:
                mode = os.lstat(fullname).st_mode
            except os.error:
                mode = 0
            if stat.S_ISDIR(mode):
                rmtree(fullname, ignore_errors, onerror)
            else:
                try:
                    os.remove(fullname)
                except os.error, err:
                    onerror(os.remove, fullname, sys.exc_info())
        try:
            os.rmdir(path)
        except os.error:
            onerror(os.rmdir, path, sys.exc_info())


def create_bootstrap_venv(index, cert_bundle):
    '''\
    Creates an internal-use only virtual environment containing the latest
    versions of pip, setuptools and and virtualenv.
    '''
    ssl_open = ssl_support.opener_for(cert_bundle)

    if not os.path.isdir(PYINFRA):
        os.makedirs(PYINFRA)

    with mkdtemp(cd = True):
        fn, url = find_latest_virtualenv(ssl_open, index)
        print 'Downloading %s from %s' % (fn, url)
        # downloaded
        with open(fn, 'wb') as f:
            f.write(ssl_open(url).read())

        print 'Expanding', fn
        with tarfile.open(fn, 'r:gz') as tar:
            toplevel = next(tar).name
            tar.extractall()


def find_latest_virtualenv(ssl_open, pypi):
    if not pypi.endswith('/'):
        pypi += '/'
    virtualenv_simple = urlparse.urljoin(pypi, 'virtualenv')
    finder = FindsLatestVirtualenv()
    finder.feed(ssl_open(virtualenv_simple).read())
    fn, relative_url = finder.latest()
    relative_url = urlparse.urlparse(relative_url).path
    upward_count = relative_url.count('../')
    relative_url = '/'.join(relative_url.split('/')[upward_count:])
    parsed_pypi = urlparse.urlparse(pypi)
    base = urlparse.urlunparse(parsed_pypi._replace(
        path = '/'.join(parsed_pypi.path.split('/')[:-upward_count])))
    return fn, urlparse.urljoin(base, relative_url)


class FindsLatestVirtualenv(HTMLParser):
    VIRTUALENV_PARSER = re.compile('virtualenv-(\d+(?:\.\d+)*).tar.gz')

    def __init__(self):
        HTMLParser.__init__(self)
        self._results = []

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        for attr, value in attrs:
            if attr == 'href':
                break
        else:
            return
        url = value
        parsed = urlparse.urlparse(url)
        _, _, fn = parsed.path.rpartition('/')
        m = self.VIRTUALENV_PARSER.match(fn)
        if not m:
            return
        self._results.append([fn, url, map(int, m.group(1).split('.'))])

    def latest(self):
        fn, url, _ = max(self._results, key = lambda (fn, url, version): version)
        return fn, url


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-i', '--index', dest = 'index_url',
                      help = 'index url for pip and easy-install', metavar = 'INDEX_URL', default=INDEX)
    parser.add_option('--cert-bundle', '-c',
                      help='cert bundle containing eBay CA chain', dest = 'cert_bundle', default = CA_BUNDLE)

    (options, args) = parser.parse_args()
    create_bootstrap_venv(options.index_url, options.cert_bundle)