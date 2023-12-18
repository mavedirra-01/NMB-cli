#!/bin/bash
# Tmux_Windows: 3
# Window_Names: Window1,Window2,Window3
# Inputs: arg1, arg2, arg3

# TMUX_CMD_START_1
# ARGS $1
echo "Running in Window1"
echo "Argument: $arg"
ls -l; sleep 500
# TMUX_CMD_END_1

# TMUX_CMD_START_2
# ARGS $2
echo "Running in Window2"
date; sleep 500
echo "Argument: $arg"
# TMUX_CMD_END_2

# TMUX_CMD_START_3
# ARGS $3
echo "Running in Window3"
pwd; sleep 500
echo "Argument: $arg"
# TMUX_CMD_END_3
