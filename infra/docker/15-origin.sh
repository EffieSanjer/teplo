#!/bin/sh
set -eu
# PUBLIC_BASE_URL is validated by API startup before web is started.
export PUBLIC_AUTHORITY="${PUBLIC_BASE_URL#*://}"
PUBLIC_AUTHORITY="${PUBLIC_AUTHORITY%/}"
export PUBLIC_ORIGIN="${PUBLIC_BASE_URL%/}"
envsubst '${PUBLIC_AUTHORITY} ${PUBLIC_ORIGIN}' < /etc/nginx/origin.conf.template > /etc/nginx/conf.d/default.conf
