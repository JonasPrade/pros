#!/bin/bash

# load config
source config.env

# variables
SSH_USER="$SSH_USER"
SSH_HOST="$SSH_HOST"
FRONTEND_LOCAL="$FRONTEND_LOCAL"
FRONTEND_REMOTE="$FRONTEND_REMOTE"

#to transfer
echo $FRONTEND_LOCAL/public

FOLDER_PUBLIC_LOCAL=$FRONTEND_LOCAL/public
FOLDER_SOURCE_LOCAL=$FRONTEND_LOCAL/src

## move files to server
scp -r $FOLDER_PUBLIC_LOCAL/* $SSH_USER@$SSH_HOST:$FRONTEND_REMOTE/public
scp -r $FOLDER_SOURCE_LOCAL/* $SSH_USER@$SSH_HOST:$FRONTEND_REMOTE/src

# go to server and build docker
ssh $SSH_USER@$SSH_HOST << EOF
  cd $FRONTEND_REMOTE
  docker-compose -f docker-compose.yml down
  docker-compose -f docker-compose.yml up -d --build
EOF
