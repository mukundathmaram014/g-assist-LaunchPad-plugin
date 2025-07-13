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

''' RISE plugin template code.

The following code can be used to create a RISE plugin written in Python. RISE
plugins are Windows based executables. They are spawned by the RISE plugin
manager. Communication between the plugin and the manager are done via pipes.
'''
import json
import logging
import os
from ctypes import byref, windll, wintypes
from typing import Dict, Optional
import psutil


# Data Types
Response = Dict[bool,Optional[str]]

LOG_FILE = os.path.join(os.environ.get("USERPROFILE", "."), 'LaunchPad_plugin.log')
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "modes.json")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

#reads modes from modes.json
def read_modes_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to read modes config: {str(e)}")
        return {}

#launches apps
def launch_apps(app_paths: list[str]) -> list[str]:
    failed = []
    for path in app_paths:
        try:
            os.startfile(path)
        except Exception as e:
            logging.error(f"Failed to launch {path}: {str(e)}")
            failed.append(path)
    return failed

#closes apps
def close_apps(app_paths: list[str]) -> list[str]:
    failed = []
    for path in app_paths:
        closed = False
        for proc in psutil.process_iter(['exe']):
            try:
                if proc.info['exe'] and (os.path.normcase(proc.info['exe']) == os.path.normcase(path)):
                    proc.terminate()
                    closed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if not closed:
            failed.append(path)
    return failed

#gets file path of running file by name
def get_app_path_by_name(app_name: str) -> str | None:
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            name = proc.info['name'].lower()
            if name.endswith(".exe"):
                name_without_ext = name[:-4]
            else:
                name_without_ext = name
            if name_without_ext == app_name.lower():
                return proc.info['exe']
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
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
    PARAMS_PROPERTY = 'properties'
    INITIALIZE_COMMAND = 'initialize'
    SHUTDOWN_COMMAND = 'shutdown'


    ERROR_MESSAGE = 'Plugin Error!'

    # Generate command handler mapping
    commands = {
        'initialize': execute_initialize_command,
        'shutdown': execute_shutdown_command,
        'launch_mode': launch_mode_command,
        'get_modes': get_modes_command,
        'list_running_apps': add_mode_command,
        'delete_mode' : delete_mode_command,
        'add_apps_to_mode' : add_apps_to_mode_command,
        'delete_apps_from_mode' : remove_apps_from_mode_command,
        'close_mode' : close_mode_command,
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
                            response = execute_initialize_command()
                            response = commands[cmd](
                                input[PARAMS_PROPERTY] if PARAMS_PROPERTY in input else None,
                                input[CONTEXT_PROPERTY] if CONTEXT_PROPERTY in input else None,
                                input[SYSTEM_INFO_PROPERTY] if SYSTEM_INFO_PROPERTY in input else None  # Pass system_info directly
                            )
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
    
    logging.info('G-Assist Plugin stopped.')
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

    This handler is responseible for initializing the plugin.

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

    if not isinstance(apps, list) or not all(isinstance(p, str) for p in apps):
        return generate_failure_response("'apps' must be a list of strings.")
    app_paths = []

    for app in apps:
        app_path = get_app_path_by_name(app)
        if (app_path):
            app_paths.append(get_app_path_by_name(app))
        else:
            return generate_failure_response(f"app {app} is currently not running or not installed in your system")

    try:
        with open(CONFIG_FILE, "r+") as f:
            # gets json object
            modes = json.load(f)
            if mode in modes:
                return generate_failure_response(f"Mode '{mode}' already exists.")
            modes[mode] = app_paths
            # dumps new json object in modes.json
            f.seek(0)
            json.dump(modes, f, indent=4)
            f.truncate()
        return generate_success_response(f"Mode '{mode}' created with {len(app_paths)} apps.")
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
        with open(CONFIG_FILE, "r+") as f:
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

    if not isinstance(apps, list) or not all(isinstance(p, str) for p in apps):
        return generate_failure_response("'apps' must be a list of strings.")
    app_paths = []

    for app in apps:
        app_path = get_app_path_by_name(app)
        if (app_path):
            app_paths.append(get_app_path_by_name(app))
        else:
            return generate_failure_response(f"app {app} is currently not running or not installed in your system")

    try:
        with open(CONFIG_FILE, "r+") as f:
            # gets json object
            modes = json.load(f)
            if mode not in modes:
                return generate_failure_response(f"Mode '{mode}' does not exist.")
            for app_path in app_paths:
                if app_path not in modes[mode]:
                    modes[mode].append(app_path)
            
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

    if not isinstance(apps, list) or not all(isinstance(p, str) for p in apps):
        return generate_failure_response("'apps' must be a list of strings.")

    try:
        with open(CONFIG_FILE, "r+") as f:
            # gets json object
            modes = json.load(f)
            if mode not in modes:
                return generate_failure_response(f"Mode '{mode}' does not exist.")
            new_apps = []
            for app_path in modes[mode]:
                keep = True
                for app in apps:
                    if (app.lower() in os.path.basename(app_path).lower().replace('.exe', '')):
                        keep = False
                        break
                if keep:
                    new_apps.append(app_path)
            modes[mode] = new_apps
            
            # dumps new json object in modes.json
            f.seek(0)
            json.dump(modes, f, indent=4)
            f.truncate()
        return generate_success_response(f"apps {apps} successfully deleted from Mode '{mode}'")
    except Exception as e:
        logging.error(f"Failed to delete apps {apps} from mode '{mode}': {str(e)}")
        return generate_failure_response("Failed to write to modes config.")
    
#test

if __name__ == '__main__':
    # # main()

    # testing launching a mode
    # print("Manual test starting...")
    # test_params = {"mode": "gaming"}  # "development" or "work" or "test"
    # result = launch_mode_command(test_params)
    # print(result)

    #testing closing a mode
    test_params = {"mode": "gaming"}  # "development" or "work" or "test"
    resultc = close_mode_command(test_params)
    print(resultc)


    # #testing get_modes

    # modes = get_modes_command()
    # print(modes)

    #testing add mode command
    # test_params = {"mode" : "gaming", "apps": ["Notepad", "Steam"]}
    # result2 = add_mode_command(test_params)
    # print(result2)

    #testing delete mode
    # test_params = {"mode" : "gaming"}
    # result3 = delete_mode_command(test_params)
    # print(result3)

    #testing add app to mode
    # test_params = {"mode" : "gaming", "apps": ["steam", "Marvelrivals_launcher"]}
    # result4 = add_apps_to_mode_command(test_params)
    # print(result4)

    #testing remove app from mode
    # test_params = {"mode" : "gaming", "apps": ["chrome"]}
    # result5 = remove_apps_from_mode_command(test_params)
    # print(result5)
