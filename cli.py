#!/usr/bin/python3
import requests
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import checkboxlist_dialog
from prompt_toolkit.shortcuts import button_dialog
from prompt_toolkit.styles import Style
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.keys import Keys
from prompt_toolkit.key_binding import KeyBindings

import shlex
import os
import subprocess
import shutil
import paramiko
from scp import SCPClient
from getpass import getpass
import time


class SSHModuleManager:
    def __init__(self, hostname, username, remote_path):
        self.hostname = hostname
        self.username = username
        self.remote_path = remote_path
        self.ssh_client = None

    def connect(self):
        if self.ssh_client is None:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Prompt for password
        password = getpass(f"Enter password for {self.username}@{self.hostname}: ")
        self.ssh_client.connect(self.hostname, username=self.username, password=password)
        self.add_ssh_key()

    def add_ssh_key(self, public_key_path="/root/.ssh/id_rsa.pub"):
        try:
            with open(public_key_path, "r") as key_file:
                public_key = key_file.read().strip()

            command = f"echo '{public_key}' >> ~/.ssh/authorized_keys"
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()  # Blocking call
            if exit_status == 0:
                print("SSH key added successfully.")
            else:
                print(f"Error adding SSH key: {stderr.read().decode()}")

        except Exception as e:
            print(f"Error: {e}")

    def disconnect(self):
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
    
    def convert_line_endings_to_unix(self, file_path):
        try:
            with open(file_path, 'rb') as file:
                content = file.read().decode('utf-8')
            content = content.replace('\r\n', '\n')
            with open(file_path, 'wb') as file:
                file.write(content.encode('utf-8'))
        except Exception as e:
            print(f"Error converting line endings: {e}")

    def transfer_file(self, local_path):
        # Ensure the file exists
        if not os.path.exists(local_path):
            print(f"File not found: {local_path}")
            return

        # Convert line endings before transferring the file
        self.convert_line_endings_to_unix(local_path)

        try:
            with SCPClient(self.ssh_client.get_transport()) as scp:
                scp.put(local_path, self.remote_path)
            print(f"File transferred successfully: {local_path}")
        except Exception as e:
            print(f"Error transferring file: {e}")

    def run_remote_script(self, script_name, args):
        # Determine the command based on the file extension
        if script_name.endswith('.sh'):
            command = f"bash {self.remote_path}/{script_name} " + ' '.join(args)
        elif script_name.endswith('.py'):
            command = f"python3 {self.remote_path}/{script_name} " + ' '.join(args)
        else:
            raise ValueError(f"Unsupported file type for script: {script_name}")

        stdin, stdout, stderr = self.ssh_client.exec_command(command)

        # Decode and format output
        stdout_output = stdout.read().decode('utf-8').strip()
        stderr_output = stderr.read().decode('utf-8').strip()

        combined_output = stdout_output + ("\n" + stderr_output if stderr_output else "")
        return combined_output

    def retrieve_file(self, remote_path, local_path):
        with SCPClient(self.ssh_client.get_transport()) as scp:
            scp.get(remote_path, local_path)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


class ModuleManager:
    def __init__(self, repo_url, ssh_manager=None):
        self.repo_url = repo_url
        self.modules_dir = os.path.join("modules")
        self.modules = []
        self.active_processes = {}
        self.ssh_manager = ssh_manager
        self.remote_path = "/tmp"
        


    def is_dependency_installed(self, dependency):
        """Check if a dependency is already installed."""
        return shutil.which(dependency) is not None

    def fetch_modules(self):
        try:
            response = requests.get(self.repo_url)
            response.raise_for_status()  # Raises HTTPError for bad requests
            files = response.json()
            self.modules = [file['name'] for file in files if file['type'] == 'file']
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error fetching modules: {e}")
            return False

    def download_module(self, module_name):
        # Fetch the JSON metadata first to get the download URL
        self.fetch_modules()
        metadata_url = f"{self.repo_url}/{module_name}"
        metadata_response = requests.get(metadata_url)
        if metadata_response.status_code == 200:
            download_url = metadata_response.json().get("download_url")
            if download_url:
                # Fetch the actual script content
                script_response = requests.get(download_url)
                if script_response.status_code == 200:
                    module_path = os.path.join(self.modules_dir, module_name)
                    with open(module_path, 'w') as file:
                        file.write(script_response.text)
                    return module_path
                else:
                    print(f"Failed to download the content of {module_name}")
            else:
                print(f"Download URL not found for {module_name}")
        else:
            print(f"Failed to fetch metadata for {module_name}")
        return None

    def parse_help_info(self, module_path):
        help_info = {}
        with open(module_path, 'r') as file:
            for line in file:
                if line.startswith('# Help:'):
                    _, info = line.split(':', 1)
                    parts = info.split('-', 1)
                    if len(parts) == 2:
                        key, desc = parts
                        help_info[key.strip()] = desc.strip()
                    else:
                        # Handle the case where there is no hyphen
                        help_info[parts[0].strip()] = "No description available"
        return help_info


    def parse_follow_log_flag(self, module_path):
        with open(module_path, 'r') as file:
            for line in file:
                if line.startswith('# Follow_log:'):
                    return line.strip().split(':')[1].strip().lower() == 'true'
        return False

    def parse_dependencies(self, module_path):
        dependencies = []
        with open(module_path, 'r') as file:
            for line in file:
                if line.startswith('# Dependencies:'):
                    # Splitting by comma and stripping spaces
                    dependencies = [dep.strip() for dep in line.strip().split(':')[1].split(',')]
                    break
        return dependencies


    def parse_silent_flag(self, module_path):
        with open(module_path, 'r') as file:
            for line in file:
                if line.startswith('# Silent:'):
                    return line.strip().split(':')[1].strip().lower() == 'true'
        return False

    def parse_logfile_path(self, module_path):
        with open(module_path, 'r') as file:
            for line in file:
                if line.startswith('# Logfile:'):
                    return line.strip().split(':')[1].strip()
        return None

    def parse_inputs(self, module_path):
        with open(module_path, 'r') as file:
            for line in file:
                if line.startswith('# Inputs:'):
                    return [input.strip() for input in line.split(':')[1].split(',')]
        return []

    def parse_tmux_windows(self, module_path):
        windows = 1  # Default value if not specified
        window_names = []
        with open(module_path, 'r') as file:
            for line in file:
                if line.startswith('# Tmux_Windows:'):
                    windows = int(line.split(':')[1].strip())
                elif line.startswith('# Window_Names:'):
                    window_names = [name.strip() for name in line.split(':')[1].split(',')]
        return windows, window_names


    def install_dependencies(self, dependencies):
        for dep in dependencies:
            if self.ssh_manager:  # Check if SSH session is active
                # Install dependencies on the remote machine
                install_command = f"sudo apt install -y {dep}"
                print(f"Installing dependency on remote machine: {dep}")
                # Execute the command remotely
                stdin, stdout, stderr = self.ssh_manager.ssh_client.exec_command(install_command)
                output = stdout.read() + stderr.read()
                print(output)
            else:
                # Install dependencies locally
                if not self.is_dependency_installed(dep):
                    print(f"Installing dependency: {dep}")
                    subprocess.run(['sudo', 'apt', 'install', '-y', dep], check=True)
                else:
                    print(f"Dependency '{dep}' is already installed.")


    def install_module(self, module_name):
        module_path = self.download_module(module_name)
        if module_path:
            dependencies = self.parse_dependencies(module_path)
            self.install_dependencies(dependencies)
            print(f"Module {module_name} installed successfully.")

    def show_and_select_modules(self):
        # Display a checkbox list dialog for module selection
        selected_modules = checkboxlist_dialog(
            title="Available Modules",
            text="Select modules to install:",
            values=[(module, module) for module in self.modules]
        ).run()

        return selected_modules

    def list_installed_modules(self):
        """
        List all files in the modules directory.
        """
        installed_modules = []
        for filename in os.listdir(self.modules_dir):
            full_path = os.path.join(self.modules_dir, filename)
            if os.path.isfile(full_path):
                installed_modules.append(filename)
        return installed_modules

    
    def parse_tmux_commands(self, module_path):
        with open(module_path, 'r') as file:
            lines = file.readlines()
    
        commands = []
        current_command = []
        capture = False
    
        for line in lines:
            if line.startswith('# TMUX_CMD_START_'):
                capture = True
                current_command = []
            elif line.startswith('# TMUX_CMD_END_'):
                capture = False
                commands.append(''.join(current_command).strip())
            elif capture:
                current_command.append(line)
    
        return commands
        
    def launch_module(self, module_name, args):
        module_path = os.path.join(self.modules_dir, module_name)
        if not os.path.exists(module_path):
            print(f"Module {module_name} not found.")
            return False
        
        tmux_windows, window_names = self.parse_tmux_windows(module_path)
        tmux_commands = self.parse_tmux_commands(module_path)
    
        for i, command in enumerate(tmux_commands):
            window_name = window_names[i] if i < len(window_names) else f"{module_name}_Window{i}"
    
            # Extract ARGS line from the command block
            args_line = [line for line in command.split('\n') if line.strip().startswith('# ARGS')]
    
            # If ARGS line is present, extract the argument number to be passed
            if args_line:
                arg_num_str = args_line[0].split()[2]  # Extract the placeholder like $1, $2, etc.
                arg_num = int(arg_num_str[1:]) - 1  # Extract the number from the placeholder and adjust for zero-indexing
                arg_to_pass = shlex.quote(args[arg_num]) if arg_num < len(args) else ''
                # Define the argument at the beginning of the command
                formatted_command = f"arg={arg_to_pass}; " + command.replace(args_line[0], '').replace('\n', '; ').strip()
            else:
                formatted_command = command.replace('\n', '; ').strip()
    
            full_command = f"tmux new-window -n '{window_name}' '{formatted_command}'"
    
            print(f"Debug - tmux command: {full_command}")
    
            subprocess.Popen(full_command, shell=True)
            print(f"Launched command in new tmux window: {window_name}")
    
        return True




    
    def display_installed_modules(self):
        """
        Display the list of installed modules in a formatted way.
        """
        installed_modules = self.list_installed_modules()

        if installed_modules:
            print("Installed Modules:")
            for index, module in enumerate(installed_modules, start=1):
                print(f"  {index}. {module}")
        else:
            print("No modules are currently installed.")



    def stop_module(self, module_name):
        process = self.active_processes.get(module_name)
        if process:
            process.terminate()
            print(f"Module {module_name} stopped.")
            del self.active_processes[module_name]
        else:
            print(f"No running module named {module_name}.")

    def remove_module(self, module_name):
        module_path = os.path.join(self.modules_dir, module_name)
        if os.path.exists(module_path):
            os.remove(module_path)
            print(f"Module {module_name} has been removed.")
            return True
        else:
            print(f"Module {module_name} not found.")
            return False


def get_bottom_toolbar_tokens():
    if app.ssh_manager and app.ssh_manager.ssh_client:
        return [('class:bottom-toolbar', f' Connected to {app.ssh_manager.hostname} ')]
    else:
        return [('class:bottom-toolbar', ' No Active SSH Connection ')]


class Engine:
    def __init__(self):
        self.key_bindings = KeyBindings()
        self.history = FileHistory('.hist.txt')
        self.repo = "https://api.github.com/repos/mavedirra-01/NMB-cli/contents/modules"
        self.ssh_manager = None
        self.module_manager = ModuleManager(
            repo_url=self.repo
        )
        self.commands = ["update", "install", "connect"]
        self.commands += ["list", "launch", "read"]
        self.commands += ["disconnect", "help"]
        self.commands += ["remove", "stop", "exit"]
        self.command_completer = WordCompleter(self.commands)
        self.style = Style.from_dict({
            '': '#ffffff',  # Default text color (white)
            'output': '#34b7eb',  # Output messages
            'completion-menu.completion': 'bg:#008080 #ffffff',  # Active completion
            'completion-menu.completion.current': 'bg:#00aaaa #000000',  # Selected completion
            'error': '#ff6347 bold',  # Error messages
            'prompt': 'bg:#1c1c1c #c5c1ff bold',  # Dark background with light purple bold text
            'bottom-toolbar': 'bg:#1c1c1c #c5c1ff italic', # Bottom menu bar for ssh
        })
        self.session = PromptSession(
            bottom_toolbar=get_bottom_toolbar_tokens,
            history=self.history,
            style=self.style,
            key_bindings=self.key_bindings,
            completer=self.command_completer,
            auto_suggest=AutoSuggestFromHistory(),
            complete_style=CompleteStyle.READLINE_LIKE
        )
            
    def print_output(self, message):
        print(f'[\x1b[34moutput\x1b[0m] {message}')

    def print_error(self, message):
        print(f'[\x1b[31merror\x1b[0m] {message}')
    
    def handle_ssh_connect(self, command):
        try:
            _, user_host = command.split(' ', 1)
            username, hostname = user_host.split('@', 1)
            remote_path = "/tmp/"
            self.ssh_manager = SSHModuleManager(hostname, username, remote_path)
            self.ssh_manager.connect()
            print(f"Connected to {hostname} as {username}")

            # Pass the ssh_manager to ModuleManager
            self.module_manager = ModuleManager(repo_url=self.repo, ssh_manager=self.ssh_manager)
            self.session.bottom_toolbar = get_bottom_toolbar_tokens
        except ValueError:
            print("Invalid command format. Use 'connect user@hostname'.")


    def select_and_remove_module(self):
        installed_modules = self.module_manager.list_installed_modules()
        if not installed_modules:
            print("No installed modules found.")
            return

        selected_module = checkboxlist_dialog(
            title="Remove Module",
            text="Select a module to remove:",
            values=[(module, module) for module in installed_modules]
        ).run()

        if selected_module:
            module_name = selected_module[0]
            self.module_manager.remove_module(module_name)

    def select_and_stop_module(self):
        if not self.module_manager.active_processes:
            print("No active modules to stop.")
            return

        selected_module = button_dialog(
            title="Stop Module",
            text="Select a module to stop:",
            buttons=[(module, module) for module in self.module_manager.active_processes.keys()]
        ).run()

        if selected_module:
            self.module_manager.stop_module(selected_module)



    def select_and_launch_module(self):
        installed_modules = self.module_manager.list_installed_modules()
        if not installed_modules:
            print("No installed modules found.")
            return

        module_menu = {str(i + 1): module for i, module in enumerate(installed_modules)}
        for key, module in module_menu.items():
            print(f"{key}: {module}")

        module_choice = self.session.prompt("Select a module to launch: ")
        module_name = module_menu.get(module_choice)

        if not module_name:
            print("Invalid selection. Please enter a valid number.")
            return

        module_path = os.path.join(self.module_manager.modules_dir, module_name)
        inputs = self.module_manager.parse_inputs(module_path)
        help_info = self.module_manager.parse_help_info(module_path)

        args = []
        if inputs:
            for input in inputs:
                prompt_text = f"{input}: "
                if input in help_info:
                    prompt_text += f"({help_info[input]}) "
                user_input = self.session.prompt(prompt_text)
                args.append(user_input)
        else:
            print(f"No inputs required for {module_name}.")

        self.module_manager.launch_module(module_name, args)

    def handle_ssh_disconnect(self):
        if self.ssh_manager:
            self.ssh_manager.disconnect()
            self.ssh_manager = None
            print("Disconnected from SSH session.")
            self.session.bottom_toolbar = get_bottom_toolbar_tokens
        else:
            print("No active SSH session to disconnect.")


    def display_help(self):
        print("NMB-cli Help:")
        print("  connect <username@hostname> - Connect to a remote machine via SSH.")
        print("  disconnect - Disconnect the current SSH session.")
        print("  fetch - Fetch the list of available modules.")
        print("  install - Install a selected module.")
        print("  list - List installed modules.")
        print("  launch - Launch a specific module.")
        print("  remove - Remove a specific module.")
        print("  stop - Stop a running module.")
        print("  exit - Exit the application.")
        print("  read - Reads a specified log file.")
        print("Usage examples:")
        print("  connect user@example.com")
        print("  fetch")
        print("  install")
        print("  launch")


    def read_log(self, log_file):
        log_dir = os.path.join("logs", log_file)
        try:
            with open(log_dir, 'r') as f:
                print(f.read())
        except FileNotFoundError:
            print(f"Log file {log_file} not found.")
            
        

    def run(self):
        while True:
            try:
                user_input = self.session.prompt([
                    ('class:prompt', "NMB-cli "),
                    ('class:prompt', "> ")
                ], style=self.style, completer=self.command_completer)

                if user_input == "exit":
                    break
                elif user_input == "help":
                    self.display_help()
                elif user_input == "update":
                    self.module_manager.fetch_modules()
                    print("Modules fetched: ", self.module_manager.modules)
                elif user_input == "stop":
                    self.select_and_stop_module()
                elif user_input == "install":
                    selected_modules = self.module_manager.show_and_select_modules()
                    for module in selected_modules:
                        self.module_manager.install_module(module)
                elif user_input == "remove":
                    self.select_and_remove_module()
                elif user_input.startswith("connect"):
                    if " " in user_input and "@" in user_input:
                        self.handle_ssh_connect(user_input)
                    else:
                        print("Usage: connect username@hostname")
                elif user_input.startswith("read"):
                    log_file = user_input.split(' ')[1] if len(user_input.split(' ')) > 1 else None
                    if log_file:
                        self.read_log(log_file)
                    else:
                        print("Usage: read <log_file>")
                elif user_input == "disconnect":
                    self.handle_ssh_disconnect()
                elif user_input == "list":
                    self.module_manager.display_installed_modules()
                elif user_input == "launch":
                    self.select_and_launch_module()
                else:
                    self.print_error(f"Command not {user_input} found")
            except KeyboardInterrupt:
                self.print_error("Ctrl+C detected! use 'exit' to quit.")
                continue
            except EOFError:
                break
            except TypeError:
                pass    
            except Exception as e:
                self.print_error(f"An error occurred: {e}")
    
    def setup_directories(self):
        os.makedirs("modules", exist_ok=True)
        os.makedirs("logs", exist_ok=True)



if __name__ == "__main__":
    app = Engine()
    app.setup_directories()
    app.run()
