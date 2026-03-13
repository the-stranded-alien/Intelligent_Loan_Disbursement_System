#!/bin/sh
# Read the nameserver from /etc/resolv.conf so nginx can resolve
# .railway.internal (private) or any public hostname
RESOLVER=$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf)
export RESOLVER=${RESOLVER:-8.8.8.8}
echo "nginx resolver: $RESOLVER"
exec /docker-entrypoint.sh "$@"
