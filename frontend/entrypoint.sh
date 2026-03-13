#!/bin/sh
set -e

# Only substitute PORT and BACKEND_URL — leave nginx vars ($uri, $proxy_host, etc.) intact
envsubst '${PORT} ${BACKEND_URL}' \
    < /etc/nginx/conf.d/default.conf.template \
    > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
