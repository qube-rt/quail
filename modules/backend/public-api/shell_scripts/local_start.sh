#!/bin/bash -x

set -o errexit
set -o pipefail
set -o nounset

flask run --host 0.0.0.0 --port 8080
