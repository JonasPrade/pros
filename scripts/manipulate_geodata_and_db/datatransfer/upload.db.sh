#!/bin/bash
source config.env

# backups db and loads it into the backup folder on the server
DB_USER_LOCAL="$DB_USER_LOCAL"
DB_NAME_LOCAL="$DB_NAME_LOCAL"
BACKUP_DIR_LOCAL="$BACKUP_DIR_LOCAL"
PG_BIN_PATH_LOCAL="$PG_BIN_PATH_LOCAL"

SSH_USER="$SSH_USER"
SSH_HOST="$SSH_HOST"
BACKUP_DIR_REMOTE="$BACKUP_DIR_REMOTE"
DB_USER_REMOTE="$DB_USER_REMOTE"
DB_NAME_REMOTE="$DB_NAME_REMOTE"
DB_PASSWORD_REMOTE="$DB_PASSWORD_REMOTE"
DB_PORT_REMOTE="$DB_PORT_REMOTE"

## Create Backup of db
timestamp=$(date +%Y%m%d_%H%M%S)
backup_file="$BACKUP_DIR_LOCAL/$timestamp.sql"
$PG_BIN_PATH_LOCAL/pg_dump -U $DB_USER_LOCAL -h localhost -d $DB_NAME_LOCAL -F c -b -v -f "$backup_file"
gzip "$backup_file"
echo "Backup created: $backup_file.gz"

# backup to server
scp "$backup_file.gz" $SSH_USER@$SSH_HOST:$BACKUP_DIR_REMOTE
echo "Backup copied to server $backup_file.gz"



