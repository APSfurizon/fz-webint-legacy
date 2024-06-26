#!/usr/bin/python

from os import listdir, remove, getenv
from os.path import isfile, join
import datetime
import subprocess

PRETIX_BACKUP = False
WEBINT_BACKUP = False
WP_BACKUP = False
STUFF_BACKUP = False

BACKUP_DIR_PRETIX = "/home/pretix/backups/"
BACKUP_DIR_WEBINT = "/home/webint/backups/"
BACKUP_DIR_WP = "/home/worcopio/backups/"
BACKUP_DIR_STUFF = "/root/backups/"

MAX_FILE_NO = 7

COMMAND_PRETIX_POSTGRES = "pg_dump -F p pretix | gzip > %s" # Restore with psql -f %s
COMMAND_PRETIX_DATA = "tar -czf %s /var/pretix-data" # Restore with tar -xvf %s. To make .secret readable I used setfacl -m u:pretix:r /var/pretix-data/.secret
COMMAND_WEBINT = "tar -czf %s /home/webint/furizon_webint" # Restore with tar -xvf %s
COMMAND_WP_MYSQL = "mysqldump -h 127.0.0.1 -P 5688 -u root --password=__PASSWORD__ --all-databases | gzip > %s" # Restore with zcat %s | mysql -h 127.0.0.1 -P 5688 -u root
COMMAND_WP_DATA = "tar -czf %s /var/lib/docker/volumes/worcopio-docker_wordpress/_data" # Restore with tar -xvf %s
COMMAND_STUFF = "tar -czf %s /etc/ /var/backups/ /var/log/ /var/mail/ /var/pretix-data/ /var/prometheus-data/ /var/spool/ /var/www/ /var/lib/grafana/ /var/lib/redis/" # Restore with tar -xvf %s


def deleteOlder(path : str, prefix : str, postfix : str):
	backupFileNames = sorted([f for f in listdir(path) if (isfile(join(path, f)) and f.startswith(prefix) and f.endswith(postfix))])
	while(len(backupFileNames) > MAX_FILE_NO):
		print(f"Removing {backupFileNames[0]}")
		remove(join(path, backupFileNames[0]))
		backupFileNames.pop(0)

def genFileName(prefix : str, postfix : str):
	return prefix + "_" + datetime.datetime.now(datetime.UTC).strftime('%Y%m%d-%H%M%S') + "_" + postfix

def runBackup(prefix : str, postfix : str, path : str, command : str):
	deleteOlder(path, prefix, postfix)
	name = join(path, genFileName(prefix, postfix))
	process = subprocess.Popen(command % name, shell=True)
	process.wait()



if(PRETIX_BACKUP):
	runBackup("pretix_postres", "backup.sql.gz", join(BACKUP_DIR_PRETIX, "postgres"), COMMAND_PRETIX_POSTGRES)
	runBackup("pretix_data", "backup.tar.gz", join(BACKUP_DIR_PRETIX, "data"), COMMAND_PRETIX_DATA)

if(WEBINT_BACKUP):
	runBackup("webint_full", "backup.tar.gz", BACKUP_DIR_WEBINT, COMMAND_WEBINT)

if(WP_BACKUP):
	mysqlCmd = COMMAND_WP_MYSQL
	mysqlPwd = getenv("MYSQL_PWD")
	if(mysqlPwd != None and mysqlPwd.strip() != ""):
		mysqlPwd = mysqlPwd.strip()
		print(f"Running with password `{mysqlPwd}`")
		mysqlCmd = mysqlCmd.replace("__PASSWORD__", mysqlPwd)
		runBackup("wp_mysql", "backup.sql.gz", join(BACKUP_DIR_WP, "mysql"), mysqlCmd)
	else:
		print("Backup run without the $MYSQL_PWD env var set. Skipping wp_mysql backup")
	runBackup("wp_wp", "backup.tar.gz", join(BACKUP_DIR_WP, "wp"), COMMAND_WP_DATA)

if(STUFF_BACKUP):
	runBackup("stuff", "backup.tar.gz", BACKUP_DIR_STUFF, COMMAND_STUFF)
