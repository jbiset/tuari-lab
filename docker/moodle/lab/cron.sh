#!/bin/sh
set -eu
trap 'exit 0' TERM INT
while :; do
    date -u '+%Y-%m-%dT%H:%M:%SZ cron start'
    if gosu www-data php /var/www/html/admin/cli/cron.php --keep-alive=0; then
        echo 'cron result=ok'
    else
        echo 'cron result=error' >&2
    fi
    sleep 60 &
    wait $! || true
done
