# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

''' G-assist launchpad plug in.
'''
import json
import logging
import os
from ctypes import byref, windll, wintypes
from typing import Dict, Optional
import psutil
import ast
import win32gui
import win32process
import win32api


# Data Types
Response = Dict[bool,Optional[str]]

LOG_FILE = os.path.join(os.environ.get("USERPROFILE", "."), 'LaunchPad_plugin.log')
"""Path to modes file"""
MODES_FILE = os.path.join(
    os.environ.get("PROGRAMDATA", "."),
    r'NVIDIA Corporation\nvtopps\rise\plugins\launchpad',
    'modes.json'
)


logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Common app name aliases -> actual process names (without .exe)
# Only include entries where the user-friendly name differs from the process name
APP_ALIASES = {

    
    # Browsers
    "edge": "msedge",
    "microsoft edge": "msedge",
    "google chrome": "chrome",
    
    # Development
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",

    
    # Communication
    "teams": "ms-teams",
    "microsoft teams": "ms-teams",
    
    # Gaming
    "epic games": "epicgameslauncher",
    "epic": "epicgameslauncher",
    
    # Utilities
    "file explorer": "explorer",
}

#reads modes from modes.json
def read_modes_config():
    try:
        with open(MODES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to read modes config: {str(e)}")
        return {}

#launches apps
def launch_apps(apps: list[dict]) -> list[str]:
    """Launch apps from list of {"name": str, "path": str} dicts."""
    failed = []
    for app in apps:
        path = app["path"]
        name = app["name"]
        try:
            os.startfile(path)
        except Exception as e:
            logging.error(f"Failed to launch {name} ({path}): {str(e)}")
            failed.append(name)
    return failed

#closes apps
def close_apps(apps: list[dict]) -> list[str]:
    """Close apps from list of {"name": str, "path": str} dicts."""
    failed = []
    for app in apps:
        path = app["path"]
        name = app["name"]
        closed = False
        for proc in psutil.process_iter(['exe']):
            try:
                if proc.info['exe'] and (os.path.normcase(proc.info['exe']) == os.path.normcase(path)):
                    proc.terminate()
                    closed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if not closed:
            failed.append(name)
    return failed

# --- App Matching Helper Functions ---

def get_exe_product_name(exe_path: str) -> str | None:
    """Extract the product name from an executable's version info metadata."""
    if not exe_path:
        return None
    
    # Common language code pairs to try
    lang_codepages = [
        "040904B0",  # US English, Unicode
        "040904E4",  # US English, Windows Multilingual
        "000004B0",  # Neutral, Unicode
    ]
    
    for lang_cp in lang_codepages:
        try:
            info = win32api.GetFileVersionInfo(exe_path, f"\\StringFileInfo\\{lang_cp}\\ProductName")
            if info:
                return info
        except:
            continue
    
    # Try to get the language from the file itself
    try:
        lang, codepage = win32api.GetFileVersionInfo(exe_path, "\\VarFileInfo\\Translation")[0]
        lang_cp = f"{lang:04X}{codepage:04X}"
        info = win32api.GetFileVersionInfo(exe_path, f"\\StringFileInfo\\{lang_cp}\\ProductName")
        return info
    except:
        return None


def match_by_process_name_exact(search_name: str) -> str | None:
    """Find app by exact process name match (case-insensitive)."""
    search_lower = search_name.lower()
    
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            name = proc.info['name']
            if not name:
                continue
            name_lower = name.lower()
            name_without_ext = name_lower[:-4] if name_lower.endswith(".exe") else name_lower
            
            if name_without_ext == search_lower:
                return proc.info['exe']
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return None


def match_by_process_name_fuzzy(app_name: str) -> str | None:
    """Find app by partial/fuzzy process name match."""
    search_lower = app_name.lower()
    
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            name = proc.info['name']
            if not name:
                continue
            name_lower = name.lower()
            name_without_ext = name_lower[:-4] if name_lower.endswith(".exe") else name_lower
            
            # Check if search term is contained in process name
            if search_lower in name_without_ext:
                return proc.info['exe']
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return None


def match_by_window_title(app_name: str) -> str | None:
    """Find app by its visible window title."""
    result = None
    search_lower = app_name.lower()
    
    def enum_callback(hwnd, _):
        nonlocal result
        if result:  # Already found
            return True
        
        if not win32gui.IsWindowVisible(hwnd):
            return True
        
        try:
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return True
            
            if search_lower in title.lower():
                # Get the process ID for this window
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    proc = psutil.Process(pid)
                    exe_path = proc.exe()
                    if exe_path:
                        result = exe_path
                        return False  # Stop enumeration
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
        except:
            pass
        return True  # Continue enumeration
    
    try:
        win32gui.EnumWindows(enum_callback, None)
    except:
        pass
    
    return result


def match_by_exe_metadata(app_name: str) -> str | None:
    """Find app by executable's embedded product name metadata."""
    search_lower = app_name.lower()
    
    for proc in psutil.process_iter(['exe']):
        try:
            exe_path = proc.info['exe']
            if not exe_path:
                continue
            
            product_name = get_exe_product_name(exe_path)
            if product_name and search_lower in product_name.lower():
                return exe_path
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return None


def get_app_path_by_name(app_name: str) -> str | None:
    """
    Find the executable path of a running application by name.
    
    Uses a hybrid approach with fallback chain:
    1. Alias mapping (instant, handles known app name differences)
    2. Exact process name match
    3. Fuzzy/partial process name match
    4. Window title matching (matches what users see)
    5. Executable metadata (reads ProductName from exe)
    
    Args:
        app_name: User-provided application name (e.g., "Chrome", "VS Code", "Word")
    
    Returns:
        Full executable path if found, None otherwise
    """
    logging.info(f"Searching for app: {app_name}")
    
    # 1. Try alias mapping first
    aliased_name = APP_ALIASES.get(app_name.lower())
    if aliased_name:
        logging.info(f"Found alias: {app_name} -> {aliased_name}")
        result = match_by_process_name_exact(aliased_name)
        if result:
            logging.info(f"Matched via alias: {result}")
            return result
    
    # 2. Try exact process name match
    result = match_by_process_name_exact(app_name)
    if result:
        logging.info(f"Matched via exact process name: {result}")
        return result
    
    # 3. Try fuzzy/partial process name match
    result = match_by_process_name_fuzzy(app_name)
    if result:
        logging.info(f"Matched via fuzzy process name: {result}")
        return result
    
    # 4. Try window title matching
    result = match_by_window_title(app_name)
    if result:
        logging.info(f"Matched via window title: {result}")
        return result
    
    # 5. Try executable metadata 
    result = match_by_exe_metadata(app_name)
    if result:
        logging.info(f"Matched via exe metadata: {result}")
        return result
    
    logging.warning(f"No match found for app: {app_name}")
    return None

def main():
    ''' Main entry point.

    Sits in a loop listening to a pipe, waiting for commands to be issued. After
    receiving the command, it is processed and the result returned. The loop
    continues until the "shutdown" command is issued.
    
    Returns:
        0 if no errors occurred during execution; non-zero if an error occurred
    '''
    TOOL_CALLS_PROPERTY = 'tool_calls'
    CONTEXT_PROPERTY = 'messages'
    SYSTEM_INFO_PROPERTY = 'system_info'  # Added for game information
    FUNCTION_PROPERTY = 'func'
    PARAMS_PROPERTY = 'params'
    INITIALIZE_COMMAND = 'initialize'
    SHUTDOWN_COMMAND = 'shutdown'


    ERROR_MESSAGE = 'Plugin Error!'

    # Generate command handler mapping
    commands = {
        'execute_initialize_command': execute_initialize_command,
        'execute_shutdown_command': execute_shutdown_command,
        'launch_mode_command': launch_mode_command,
        'get_modes_command': get_modes_command,
        'add_mode_command': add_mode_command,
        'delete_mode_command' : delete_mode_command,
        'add_apps_to_mode_command' : add_apps_to_mode_command,
        'remove_apps_from_mode_command' : remove_apps_from_mode_command,
        'close_mode_command' : close_mode_command,
        'list_apps_in_mode_command' : list_apps_in_mode_command
    }
    cmd = ''

    logging.info('Plugin started')
    while cmd != SHUTDOWN_COMMAND:
        response = None
        input = read_command()
        if input is None:
            logging.error('Error reading command')
            continue

        logging.info(f'Received input: {input}')
        
        if TOOL_CALLS_PROPERTY in input:
            tool_calls = input[TOOL_CALLS_PROPERTY]
            for tool_call in tool_calls:
                if FUNCTION_PROPERTY in tool_call:
                    cmd = tool_call[FUNCTION_PROPERTY]
                    logging.info(f'Processing command: {cmd}')
                    if cmd in commands:
                        if(cmd == INITIALIZE_COMMAND or cmd == SHUTDOWN_COMMAND):
                            response = commands[cmd]()
                        else:
                            params = tool_call.get(PARAMS_PROPERTY, {})
                            response = execute_initialize_command()
                            response = commands[cmd](params)
                    else:
                        logging.warning(f'Unknown command: {cmd}')
                        response = generate_failure_response(f'{ERROR_MESSAGE} Unknown command: {cmd}')
                else:
                    logging.warning('Malformed input: missing function property')
                    response = generate_failure_response(f'{ERROR_MESSAGE} Malformed input.')
        else:
            logging.warning('Malformed input: missing tool_calls property')
            response = generate_failure_response(f'{ERROR_MESSAGE} Malformed input.')

        logging.info(f'Sending response: {response}')
        write_response(response)

        if cmd == SHUTDOWN_COMMAND:
            logging.info('Shutdown command received, terminating plugin')
            break
    
    logging.info('launchpad Plugin stopped.')
    return 0


def read_command() -> dict | None:
    ''' Reads a command from the communication pipe.

    Returns:
        Command details if the input was proper JSON; `None` otherwise
    '''
    try:
        STD_INPUT_HANDLE = -10
        pipe = windll.kernel32.GetStdHandle(STD_INPUT_HANDLE)
        chunks = []

        while True:
            BUFFER_SIZE = 4096
            message_bytes = wintypes.DWORD()
            buffer = bytes(BUFFER_SIZE)
            success = windll.kernel32.ReadFile(
                pipe,
                buffer,
                BUFFER_SIZE,
                byref(message_bytes),
                None
            )

            if not success:
                logging.error('Error reading from command pipe')
                return None

            # Add the chunk we read
            chunk = buffer.decode('utf-8')[:message_bytes.value]
            chunks.append(chunk)

            # If we read less than the buffer size, we're done
            if message_bytes.value < BUFFER_SIZE:
                break

        retval = buffer.decode('utf-8')[:message_bytes.value]
        return json.loads(retval)

    except json.JSONDecodeError:
        logging.error('Failed to decode JSON input')
        return None
    except Exception as e:
        logging.error(f'Unexpected error in read_command: {str(e)}')
        return None


def write_response(response:Response) -> None:
    ''' Writes a response to the communication pipe.

    Args:
        response: Function response
    '''
    try:
        STD_OUTPUT_HANDLE = -11
        pipe = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

        json_message = json.dumps(response)
        message_bytes = json_message.encode('utf-8')
        message_len = len(message_bytes)

        bytes_written = wintypes.DWORD()
        windll.kernel32.WriteFile(
            pipe,
            message_bytes,
            message_len,
            bytes_written,
            None
        )

         # Write <<END>> to signal G-Assist the response is complete
        end_marker = b"<<END>>\n"
        windll.kernel32.WriteFile(
            pipe,
            end_marker,
            len(end_marker),
            bytes_written,
            None
        )

    except Exception as e:
        logging.error(f'Failed to write response: {str(e)}')
        pass


def generate_failure_response(message:str=None) -> Response:
    ''' Generates a response indicating failure.

    Parameters:
        message: String to be returned in the response (optional)

    Returns:
        A failure response with the attached message
    '''
    response = { 'success': False }
    if message:
        response['message'] = message
    return response


def generate_success_response(message:str=None) -> Response:
    ''' Generates a response indicating success.

    Parameters:
        message: String to be returned in the response (optional)

    Returns:
        A success response with the attached massage
    '''
    response = { 'success': True }
    if message:
        response['message'] = message
    return response


def execute_initialize_command() -> dict:
    ''' Command handler for `initialize` function

    This handler is responsible for initializing the plugin.

    Args:
        params: Function parameters

    Returns:
        The function return value(s)
    '''
    logging.info('Initializing plugin')
    # initialization function body
    return generate_success_response('initialize success.')


def execute_shutdown_command() -> dict:
    ''' Command handler for `shutdown` function

    This handler is responsible for releasing any resources the plugin may have
    acquired during its operation (memory, access to hardware, etc.).

    Args:
        params: Function parameters

    Returns:
        The function return value(s)
    '''
    logging.info('Shutting down plugin')
    # shutdown function body
    return generate_success_response('shutdown success.')


def launch_mode_command(params:dict=None, context:dict=None, system_info:dict=None) -> dict:
    ''' 
    Launches all applications associated with a given mode.

    Args:
        params: Dictionary containing function parameters. Must include the "mode" key.
        context: Optional context information (unused).
        system_info: Optional system information (unused).

    Returns:
        A success response if all applications launch, or a failure response listing any that failed.
    '''
    logging.info(f'Executing launch_mode_command with params: {params}')

    mode = params.get("mode") if params else None

    if not mode:
        return generate_failure_response("Missing 'mode' parameter")

    modes = read_modes_config()
    if mode not in modes:
        return generate_failure_response(f"Mode '{mode}' not found.")
    failed = launch_apps(modes[mode])

    if failed:
        return generate_failure_response(f"Some apps failed to launch: {failed}")
    return generate_success_response(f"Mode '{mode}' launched.")

def close_mode_command(params: dict = None, *_args) -> dict:

    '''
    Closes all applications associated with a given mode by terminating their processes.

    Args:
        params: Dictionary containing function parameters. Must include the "mode" key.
        *_args: Additional unused arguments.

    Returns:
        A success response if all applications are closed, or a failure response listing any that failed.
    '''
    logging.info(f'Executing close_mode_command with params: {params}')

    mode = params.get("mode") if params else None

    if not mode:
        return generate_failure_response("Missing 'mode' parameter")

    modes = read_modes_config()
    if mode not in modes:
        return generate_failure_response(f"Mode '{mode}' not found.")
    
    failed = close_apps(modes[mode])

    if failed:
        return generate_failure_response(f"Some apps failed to close: {failed}")
    return generate_success_response(f"Mode '{mode}' closed.")
    

def get_modes_command(params:dict=None, context:dict=None, system_info:dict=None) -> dict:
    ''' 
    Returns a list of all available modes defined in the modes configuration.

    Args:
        params: Optional dictionary of function parameters (unused).
        context: Optional context information (unused).
        system_info: Optional system information (unused).

    Returns:
        A success response containing the list of available mode names.
    '''
    logging.info(f'Executing get_modes_command with params: {params}')

    modes = read_modes_config()
    return generate_success_response(f"Available modes: {list(modes.keys())}")

def add_mode_command(params: dict = None, *_args) -> dict:
    '''
    Adds a new mode to modes.json using a selection of running apps.

    Args:
        params: Dictionary with 'mode' (str) and 'apps' (list of app names as strings).
        *_args: Additional unused arguments.

    Returns:
        Success response if mode is added, or failure response if mode exists, app is not running, or file write fails.
    '''

    logging.info(f'Executing add_mode_command with params: {params}')

    if not params or "mode" not in params or "apps" not in params:
        return generate_failure_response("Missing 'mode' or 'apps'.")

    mode = params["mode"]
    apps = params["apps"]

    # If 'apps' is a string, handle both list-like and single app cases
    if isinstance(apps, str):
        try:
            # try to parse as a list string
            parsed = ast.literal_eval(apps)
            if isinstance(parsed, list):
                apps = parsed
            # case where single app passed as string in string (e.g, "'Steam'")
            elif isinstance(parsed, str):
                apps = [parsed]
            else:
                return generate_failure_response("'apps' string could not be parsed as a list or string.")
        except Exception:
            # handles if app is just passed as a string (e.g., "Steam")
            apps = [apps]

    # Confirms apps is now a list of strings
    if not isinstance(apps, list) or not all(isinstance(p, str) for p in apps):
        return generate_failure_response("'apps' must be a list of strings.")
    app_entries = []

    # For each app name, get its executable path if running; collect valid entries, or fail if any app is not found.
    for app in apps:
        app_path = get_app_path_by_name(app)
        if app_path:
            app_entries.append({"name": app, "path": app_path})
        else:
            return generate_failure_response(f"app {app} is currently not running or not installed in your system")

    try:
        with open(MODES_FILE, "r+") as f:
            # gets json object
            modes = json.load(f)
            if mode in modes:
                return generate_failure_response(f"Mode '{mode}' already exists.")
            modes[mode] = app_entries
            # dumps new json object in modes.json
            f.seek(0)
            json.dump(modes, f, indent=4)
            f.truncate()
        return generate_success_response(f"Mode '{mode}' created with {len(app_entries)} apps.")
    except Exception as e:
        logging.error(f"Failed to add mode from selection: {str(e)}")
        return generate_failure_response("Failed to write to modes config.")


def delete_mode_command(params: dict = None, *_args) -> dict:
    '''
    Deletes a mode from modes.json.

    Args:
        params: Dictionary with 'mode' (str) to delete.
        *_args: Additional unused arguments.

    Returns:
        Success response if mode is deleted, or failure response if mode does not exist or file write fails.
    
    '''

    logging.info(f'Executing delete_mode_command with params: {params}')

    if not params or "mode" not in params:
        return generate_failure_response("Missing 'mode'")
    
    mode = params["mode"]

    try:
        with open(MODES_FILE, "r+") as f:
            # gets json object
            modes = json.load(f)
            if mode not in modes:
                return generate_failure_response(f"Mode '{mode}' does not exist.")
            del modes[mode]
            # dumps new json object in modes.json
            f.seek(0)
            json.dump(modes, f, indent=4)
            f.truncate()
        return generate_success_response(f"Mode '{mode}' successfully deleted")
    except Exception as e:
        logging.error(f"Failed to delete mode: {str(e)}")
        return generate_failure_response("Failed to write to modes config.")

def add_apps_to_mode_command(params: dict = None, *_args) -> dict:

    '''
    Adds one or more apps to an existing mode in modes.json, using currently running apps.

    Args:
        params: Dictionary with 'mode' (str) and 'apps' (list of app names as strings).
        *_args: Additional unused arguments.

    Returns:
        Success response if apps are added, or failure response if mode does not exist, app is not running, or file write fails.
        Deduplicates apps so only new apps are added to the mode.
    '''

    logging.info(f'Executing add_apps_to_mode_command with params: {params}')

    if not params or "mode" not in params or "apps" not in params:
        return generate_failure_response("Missing 'mode' or 'apps'")
    
    mode = params["mode"]
    apps = params["apps"]

    # If 'apps' is a string, handle both list-like and single app cases
    if isinstance(apps, str):
        try:
            # try to parse as a list string
            parsed = ast.literal_eval(apps)
            if isinstance(parsed, list):
                apps = parsed
            # case where single app passed as string in string (e.g, "'Steam'")
            elif isinstance(parsed, str):
                apps = [parsed]
            else:
                return generate_failure_response("'apps' string could not be parsed as a list or string.")
        except Exception:
            # handles if app is just passed as a string (e.g., "Steam")
            apps = [apps]
        
    # Confirms apps is now a list of strings
    if not isinstance(apps, list) or not all(isinstance(p, str) for p in apps):
        return generate_failure_response("'apps' must be a list of strings.")
    app_entries = []

    # For each app name, get its executable path if running; collect valid entries, or fail if any app is not found.
    for app in apps:
        app_path = get_app_path_by_name(app)
        if app_path:
            app_entries.append({"name": app, "path": app_path})
        else:
            return generate_failure_response(f"app {app} is currently not running or not installed in your system")

    try:
        with open(MODES_FILE, "r+") as f:
            # gets json object
            modes = json.load(f)
            if mode not in modes:
                return generate_failure_response(f"Mode '{mode}' does not exist.")
            existing_paths = [entry["path"] for entry in modes[mode]]
            for entry in app_entries:
                if entry["path"] not in existing_paths:
                    modes[mode].append(entry)
            
            # dumps new json object in modes.json
            f.seek(0)
            json.dump(modes, f, indent=4)
            f.truncate()
        return generate_success_response(f"apps {apps} successfully added to Mode '{mode}'")
    except Exception as e:
        logging.error(f"Failed to add apps {apps} to mode '{mode}': {str(e)}")
        return generate_failure_response("Failed to write to modes config.")


def remove_apps_from_mode_command(params: dict = None, *_args) -> dict:
    '''
    Removes one or more apps from an existing mode in modes.json by matching app names (case-insensitive, ignoring .exe) against the stored app paths.

    Args:
        params: Dictionary with 'mode' (str) and 'apps' (list of app names as strings) to remove.
        *_args: Additional unused arguments.

    Returns:
        Success response if apps are removed, or failure response if mode does not exist or file write fails.
    '''

    logging.info(f'Executing remove_apps_from_mode_command with params: {params}')

    if not params or "mode" not in params or "apps" not in params:
        return generate_failure_response("Missing 'mode' or 'apps'")
    
    mode = params["mode"]
    apps = params["apps"]

    # If 'apps' is a string, handle both list-like and single app cases
    if isinstance(apps, str):
        try:
            # try to parse as a list string
            parsed = ast.literal_eval(apps)
            if isinstance(parsed, list):
                apps = parsed
            # case where single app passed as string in string (e.g, "'Steam'")
            elif isinstance(parsed, str):
                apps = [parsed]
            else:
                return generate_failure_response("'apps' string could not be parsed as a list or string.")
        except Exception:
            # handles if app is just passed as a string (e.g., "Steam")
            apps = [apps]
        
    # Confirms apps is now a list of strings
    if not isinstance(apps, list) or not all(isinstance(p, str) for p in apps):
        return generate_failure_response("'apps' must be a list of strings.")

    try:
        with open(MODES_FILE, "r+") as f:
            # gets json object
            modes = json.load(f)
            if mode not in modes:
                return generate_failure_response(f"Mode '{mode}' does not exist.")
            new_apps = []
            for entry in modes[mode]:
                # removes apps by matching name (case-insensitive)
                keep = True
                for app in apps:
                    if app.lower() == entry["name"].lower():
                        keep = False
                        break
                if keep:
                    new_apps.append(entry)
            modes[mode] = new_apps
            
            # dumps new json object in modes.json
            f.seek(0)
            json.dump(modes, f, indent=4)
            f.truncate()
        return generate_success_response(f"apps {apps} successfully deleted from Mode '{mode}'")
    except Exception as e:
        logging.error(f"Failed to delete apps {apps} from mode '{mode}': {str(e)}")
        return generate_failure_response("Failed to write to modes config.")

def list_apps_in_mode_command(params: dict = None, *_args) -> dict:
    '''
    Returns a list of all apps stored in a specific mode

    Args:
        params: Dictionary with 'mode' (str)
        *_args: Additional unused arguments.

    Returns:
        Success response if apps in mode are successfully listed, or failure response if mode does not exist.
    '''

    logging.info(f'Executing list_apps_in_mode_command with params: {params}')

    if not params or "mode" not in params:
        return generate_failure_response("Missing 'mode'")
    
    mode = params["mode"]

    try:
        with open(MODES_FILE, "r") as f:
            # gets json object
            modes = json.load(f)
            if mode not in modes:
                return generate_failure_response(f"Mode '{mode}' does not exist.")

        app_names = [entry["name"] for entry in modes[mode]]
        return generate_success_response(f"apps in mode {mode}: {app_names}")
    except Exception as e:
        logging.error(f"Failed to list apps in mode '{mode}': {str(e)}")
        return generate_failure_response("Failed to read modes config.")
    
    

if __name__ == '__main__':
    main()

