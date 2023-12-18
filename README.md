# NMB-cli -> name is WIP

## Overview
NMB-cli provides a flexible platform for running various attack modules, both locally and on remote machines via SSH.

## Features
- SSH connection to remote machines for script execution.
- Modular architecture for easy integration of new scripts.
- Support for both Python and Bash scripts.
- Customizable module parameters and dependencies.
- In-built help and error handling for user guidance.
- Logging and silent mode execution.
- history file.
- Clean user interface.

## Installation
look at the 'releases' section for pre-compiled executables.


## Usage
The NMB-cli operates with the following commands:
- `connect <username@hostname>`: Connect to a remote machine via SSH.
- `disconnect`: Disconnect the current SSH session.
- `update`: Fetches/Updates the list of available modules.
- `install`: Install a selected module.
- `list`: List installed modules.
- `launch`: Launch a specific module.
- `remove`: Remove a specific module.
- `stop`: Stop a running module.
- `read <logfile>`: Reads a logfle. EX: `read nmap.log`
- `exit`: Exit the application.

## Module Syntax
Modules for NMB-cli should follow the specific syntax to be correctly parsed and executed. Both Bash and Python scripts are supported. 

### General Syntax for Modules
Each module should contain metadata comments at the top of the file, detailing its dependencies, input parameters, help text, logfile path, and silent mode preference. The syntax for these metadata comments is as follows:

```bash
# Dependencies: [list of dependencies separated by comma]
# Inputs: [list of input parameters separated by comma]
# Help: [parameter] - [description]
# Logfile: [path to the logfile]
# Silent: [true/false]
```

### Example Module
```bash
#!/bin/bash
# Author: Connor Fancy
# Dependencies: nmap
# Inputs: target, scan_type
# Help: scan_type - Options are 'QS' or 'IS'
# Logfile: logs/nmap.log
# Silent: false

# Script logic here
```
