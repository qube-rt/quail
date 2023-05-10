#!/bin/bash -x

set -o errexit
set -o pipefail
set -o nounset

#/usr/local/bin/gunicorn -k gevent --bind 0.0.0.0:5050 autoapp:app

/usr/local/bin/gunicorn -b=:8080 -w=1 autoapp:app
