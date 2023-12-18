#!/usr/bin/env python3
import subprocess
import sys

# Dependencies: nmap
# Inputs: target, scan_type
# Help: scan_type - Options are 'QS' or 'IS'
# Logfile: logs/nmap.log
# Silent: true

def run_nmap_scan(target, scan_type):
    # Define the nmap command based on the scan type
    if scan_type == 'QS':  # Quick Scan
        command = ['nmap', '-T4', '-F', target]
    elif scan_type == 'IS':  # Intense Scan
        command = ['nmap', '-T4', '-A', '-v', target]
    else:
        raise ValueError("Invalid scan type. Options are 'QS' or 'IS'.")

    # Execute the nmap command
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    return stdout.decode(), stderr.decode()

if __name__ == "__main__":
    target = sys.argv[1]
    scan_type = sys.argv[2]
    stdout, stderr = run_nmap_scan(target, scan_type)
    print(stderr, stdout)
