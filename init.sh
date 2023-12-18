#!/bin/bash

# Check if SSH keys exist, generate them if not
SSH_KEY_DIR="/root/.ssh"
mkdir -p ${SSH_KEY_DIR}
if [ ! -f ${SSH_KEY_DIR}/id_rsa ]; then
    echo "Generating SSH keys..."
    ssh-keygen -t rsa -b 4096 -f ${SSH_KEY_DIR}/id_rsa -N ''
    echo "SSH keys generated."
else
    echo "SSH keys already exist."
fi

# Add other initialization tasks here

# Start a new tmux session and run cli.py in it
tmux new-session -d -s NMB-cli 'python3 /usr/src/app/cli.py'

# Attach to the tmux session (useful when you attach to the container's shell)
tmux attach-session -t NMB-cli