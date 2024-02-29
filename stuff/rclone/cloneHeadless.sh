#!/bin/bash
source /root/.profile

/usr/bin/tar -czf /tmp/backupRclone.tar.gz /home/ /root/ /etc/ /var/backups/ /var/log/ /var/mail/ /var/pretix-data/ /var/prometheus-data/ /var/spool/ /var/www/ /var/lib/grafana/ /var/lib/redis/

/usr/bin/rclone sync /tmp/backupRclone.tar.gz webservice:/backups/backupRclone.tar.gz --bwlimit 15M

/usr/bin/rm /tmp/backupRclone.tar.gz
