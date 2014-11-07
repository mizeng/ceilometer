#!/bin/bash -x

set -e
if [ $# -ne 1 ]
then
	echo "usage: `basename $0` <virtual_env>"
	exit 1
fi

VIRTUAL_ENV=$1

if [ ! -d $PWD/$VIRTUAL_ENV ]
then
    virtualenv $VIRTUAL_ENV
fi

export PYINFRA_HOME=$PWD/.bootstrap_download_

if [ ! -d $PYINFRA_HOME ]
then
	mkdir $PYINFRA_HOME
fi

cd $PYINFRA_HOME
python ../tools/generate_ca_cert.py

export PIP_CERT=$PYINFRA_HOME/.pyinfra/ebay.cabundle
export PIP_INDEX_URL=https://python.corp.ebay.com/pypi/pythoninfra/production/+simple/
pip install infra $VIRTUAL_ENV
exit 2