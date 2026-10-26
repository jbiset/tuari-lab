#!/bin/sh
set -eu
chown www-data:www-data /var/moodledata
state=$(php /opt/tuari/db-state.php)
case "$state" in
    empty)
        gosu www-data php admin/cli/install_database.php \
            --agree-license --lang=en --adminuser=admin \
            --adminpass="$ADMIN_PASSWORD" --adminemail=admin@campus.example.test \
            --fullname='Campus de capacitación - Laboratorio TUARI' --shortname='TUARI LAB'
        ;;
    installed) ;;
    *) echo 'Instalación parcial: conservar evidencias y consultar docs/operacion.md.' >&2; exit 1 ;;
esac
exec gosu www-data php /opt/tuari/seed.php
