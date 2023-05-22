#!/bin/bash -x

set -o errexit
set -o pipefail
set -o nounset

flask --app public_app:app run --host 0.0.0.0 --port 8080
