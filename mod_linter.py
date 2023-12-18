import subprocess
import os
import sys

def check_bash_syntax(file_path):
    # Using 'bash -n' to check for syntax errors
    result = subprocess.run(['bash', '-n', file_path], capture_output=True, text=True)
    if result.returncode != 0:
        return False, result.stderr
    return True, ""

def check_python_syntax(file_path):
    # Using Python's compile() function to check for syntax errors
    try:
        with open(file_path, 'r') as file:
            compile(file.read(), file_path, 'exec')
    except SyntaxError as e:
        return False, str(e)
    return True, ""


def validate_parameters(file_path):
    required_params = ['Dependencies', 'Inputs']
    optional_params = ['Help', 'Logfile', 'Silent']
    found_params = {param: False for param in required_params}
    optional_params_found = {param: False for param in optional_params}

    with open(file_path, 'r') as file:
        for line in file:
            for param in required_params:
                if line.startswith(f'# {param}:'):
                    found_params[param] = True
            for param in optional_params:
                if line.startswith(f'# {param}:'):
                    optional_params_found[param] = True
                    if not validate_optional_param_syntax(line, param):
                        return False, f"Syntax error in parameter '{param}'"

    missing_params = [param for param, found in found_params.items() if not found]
    if missing_params:
        return False, f"Missing required parameters: {', '.join(missing_params)}"
    return True, ""

def validate_optional_param_syntax(line, param):
    # Example of a basic syntax check for the optional parameters
    if param == 'Silent':
        if not line.strip().endswith('true') and not line.strip().endswith('false'):
            return False

    elif param == 'Help':
        # Assuming the format '[parameter] - Description'
        if not '-' in line:
            return False
        parts = line.split('-', 1)
        if not parts[0].strip().startswith('[') or not parts[0].strip().endswith(']'):
            return False

    elif param == 'Logfile':
        # Check for a valid path (basic check for an absolute path)
        path = line.split(':', 1)[1].strip()
        if not path.startswith('/'):
            return False

    return True




def lint_module(file_path):
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Linting {file_path}...")

    # Determine if it's a bash or python script
    if file_path.endswith('.sh'):
        syntax_ok, error = check_bash_syntax(file_path)
    elif file_path.endswith('.py'):
        syntax_ok, error = check_python_syntax(file_path)
    else:
        print("Unsupported file type. Only .sh and .py files are supported.")
        return

    if not syntax_ok:
        print(f"Syntax error: {error}")
        return

    param_ok, error = validate_parameters(file_path)
    if not param_ok:
        print(f"Potential parameter error: {error}")
        return

    print("No issues found. Linting passed.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python module_linter.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    lint_module(file_path)
