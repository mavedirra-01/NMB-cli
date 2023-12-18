#!/bin/bash
# Dependencies: nmap
# Inputs: target, scan_type
# Help: scan_type - Options are 'QS' or 'IS'
# Logfile: logs/nmap.log
# Silent: true

# Read arguments
target=$1
scan_type=$2

# Perform nmap scan based on the provided scan type
case $scan_type in
    "QS") nmap -T4 -F $target ;;
    "IS") nmap -T4 -A $target ;;
    *) echo "Invalid scan type"; exit 1 ;;
esac

sleep 500
