#!/bin/bash

# load config
source config.env

# variables
SSH_USER="$SSH_USER"
SSH_HOST="$SSH_HOST"
FRONTEND_LOCAL="$FRONTEND_LOCAL"
FRONTEND_REMOTE="$FRONTEND_REMOTE"

#to transfer
FOLDER_PUBLIC_LOCAL=$FRONTEND_LOCAL/public
FOLDER_SOURCE_LOCAL=$FRONTEND_LOCAL/src
echo $FRONTEND_LOCAL/package.json

## move files to server
scp -p $FRONTEND_LOCAL/package.json $SSH_USER@$SSH_HOST:$FRONTEND_REMOTE/package.json
scp -p $FRONTEND_LOCAL/package-lock.json $SSH_USER@$SSH_HOST:$FRONTEND_REMOTE/package-lock.json
scp -p $FRONTEND_LOCAL/README.md $SSH_USER@$SSH_HOST:$FRONTEND_REMOTE/README.md
scp -r $FOLDER_PUBLIC_LOCAL/* $SSH_USER@$SSH_HOST:$FRONTEND_REMOTE/public
scp -r $FOLDER_SOURCE_LOCAL/* $SSH_USER@$SSH_HOST:$FRONTEND_REMOTE/src

# go to server and build docker
ssh $SSH_USER@$SSH_HOST << EOF
  cd $FRONTEND_REMOTE
  echo $FRONTEND_REMOTE
  docker compose -f docker-compose.yaml down
  docker compose -f docker-compose.yaml up -d --build
EOF
