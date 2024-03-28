#!/bin/bash
source config.env

name="20240224_221820.sql"

SSH_USER="$SSH_USER"
SSH_HOST="$SSH_HOST"
BACKUP_DIR_REMOTE="$BACKUP_DIR_REMOTE"
DB_USER_REMOTE="$DB_USER_REMOTE"
DB_NAME_REMOTE="$DB_NAME_REMOTE"
DB_PASSWORD_REMOTE="$DB_PASSWORD_REMOTE"
DB_PORT_REMOTE="$DB_PORT_REMOTE"


# change to server und load backup
ssh "$SSH_USER"@"$SSH_HOST" << EOF
  gunzip -c $BACKUP_DIR_REMOTE/$(basename "$name.gz") | pg_restore -U $DB_USER_REMOTE -h localhost -d $DB_NAME_REMOTE -p $DB_PORT_REMOTE -v --clean --if-exists
EOF
