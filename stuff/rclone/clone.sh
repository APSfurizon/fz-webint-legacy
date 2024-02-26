#!/bin/bash

/usr/bin/tar -czvf /tmp/backupRclone.tar.gz /home/ /root/ /etc/ /var/backups/ /var/log/ /var/mail/ /var/pretix-data/ /var/prometheus-data/ /var/spool/ /var/www/

/usr/bin/rclone sync /tmp/backupRclone.tar.gz webservice:/backups/backupRclone.tar.gz -P --stats=1s --bwlimit 15M

/usr/bin/rm /tmp/backupRclone.tar.gz
