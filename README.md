# LaunchPad G-Assist Plugin

<p align="center">
  <a href="https://www.youtube.com/watch?v=8hIFAeJRz9o">
    <img src="https://img.youtube.com/vi/8hIFAeJRz9o/0.jpg" alt="LaunchPad Demo" width="48%">
  </a>
  <img src="launchpad-photo.png" alt="LaunchPad Screenshot" width="48%">
</p>



**LaunchPad** is a G-Assist plugin that enables you to instantly switch between custom modes, for which you can configure with groups of applications. LaunchPad allows you to open sets of apps with a single voice or text command, streamlining your workflow and productivity.

For example, say “start development mode” to automatically launch VSCode, Chrome, and Postman, or “start gaming mode” to open your game, Twitch, and Spotify. All modes are fully customizable, can be edited dynamically, and are stored locally for quick access.

---

## What Can It Do?
- Create new modes based on currently running apps
- Launch your configured modes (like `development`, `gaming`, `focus`)
- Add/remove apps from existing modes
- Delete modes
- Mode configuration saved in `modes.json`
- Voice/text input supported via G-Assist

## Requirements

- Windows PC
- Python 3.7+ (for development/building)
- G-Assist installed
- Plugin dependencies listed in `requirements.txt`
- Applications to launch must have known absolute paths


## Installation Guide

### Step 1: Download the code
```bash
git clone --recurse-submodules <repository-url>
cd LaunchPad
```
This downloads all the code to your computer

### Step 2: Set Up Python Environment
```bash
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```
This creates a clean environment and installs all required packages.

### Step 3: Setup and Build
First run the setup script:
```bash
.\setup.bat
```
This will install all required python packages. Then run the build script:

```bash
.\build.bat
```

### Step 4: Install to G-Assist

First open the dist folder created by running the build script.
Then copy the folder named "launchpad" to:
```bash
%PROGRAMDATA%\NVIDIA Corporation\nvtopps\rise\plugins
```
Restart G-Assist to detect the Plug-in.

## How to Use

Try these commands to use the various capabilities of launchpad

Create a New Mode from Running Apps


Say or type:

```text
hey launchpad, create mode called gaming for apps steam, chrome, and discord
```

G-Assist will create a new "gaming" mode using the currently running Steam, Chrome, and Discord. Make sure these apps are already running when you do this command otherwise it will not work.

Launch a Mode

Say or type:

```text
hey launchpad, launch gaming mode
```

G-Assist will launch all apps configured for the "gaming" mode.

Close a Mode

Say or type:

```text
hey launchpad, close gaming mode
```

G-Assist will close all apps in the "gaming" mode.

List Available Modes

Say or type:

```text
hey launchpad, list modes
```

G-Assist will show all configured modes.

Remove Apps from a Mode

Say or type:

```text
hey launchpad, remove apps chrome, discord from gaming mode
```

G-Assist will remove Notepad and Discord from the "gaming" mode.

Add Apps to an Existing Mode

Say or type:

```text
hey launchpad, add apps notepad, chrome to gaming mode
```

G-Assist will add Notepad and Chrome to the "work" mode.



Tip: You can use voice or text commands. Mode and app names are case-insensitive and should match the names of running applications. If you are unsure about the app name you can open task manager to find it. Note that you can also manually add and modify application paths by opening modes.json.


## Troubleshooting
The plugic automatically logs all activity to 
```bash
%USERPROFILE%\LaunchPad_plugin.log
```

It tracks:
- Plugin startup and shutdown
- Command reception and processing
- Error conditions
- Function execution details

## Developer Documentation

### Plugin Architecture
The LaunchPad plugin is a Python-based G-Assist extension that stores user-created modes in a JSON file, mapping each mode to a list of application executable paths. It uses a command-driven architecture, continuously listening for commands from G-Assist and executing the appropriate actions to manage and launch application groups.

### Core Components

#### Command Handling
- `read_command()`: Reads JSON-formatted commands from G-Assist's input pipe
  - Uses Windows API to read from STDIN
  - Returns parsed JSON command or None if invalid
  - Handles chunked input for large messages

- `write_response()`: Sends JSON-formatted responses back to G-Assist
  - Uses Windows API to write to STDOUT
  - Appends `<<END>>` marker to indicate message completion
  - Response format: `{"success": bool, "message": Optional[str]}`

### Modes

Modes are stored in the `modes.json` file as a dictionary, where each key is a mode name and the value is a list of absolute executable paths for the applications associated with that mode.

Example structure:

```json
{
  "gaming": ["C:/Program Files/Steam/steam.exe", "C:/Program Files/Discord/discord.exe"],
  "work": ["C:/Program Files/VSCode/Code.exe", "C:/Program Files/Chrome/Application/chrome.exe"]
}
```

### Available Commands

### `initialize`
Initializes the plugin and sets up the environment.
- No parameters required
- Returns success response with initialization status

### `shutdown`
Gracefully shuts down the plugin.
- No parameters required
- Returns success response with shutdown status

### `launch_mode_command`
Launches all applications configured for a specified mode by starting each app using its saved executable path.

**Parameters:**
- `mode` (string): The name of the mode to launch (e.g., "gaming", "work").

The command retrieves the list of apps associated with the given mode from `modes.json` and attempts to launch each one. If any app fails to start, the response will include the names of those apps.

Returns a success response if all apps launch successfully, or a failure response listing any apps that could not be started.

### `get_modes_command`
Retrieves a list of all modes currently configured in the plugin. Returns the names of each mode as stored in modes.json.
- No parameters required
- Returns success response with listed modes

### `add_mode_command`
Creates a new mode by capturing the executable paths of currently running applications.

**Parameters:**
- `mode` (string): The name of the mode to create (e.g., "gaming", "work").
- `apps` (list or string): The list of app names to include in the mode. If provided as a string (e.g., "['steam', 'discord']"), it will be parsed into a list automatically. Aditionally, if provided as a string composed of a string (e.g., "'Steam'") or just as a string (e.g., "Steam"), it will be parsed into a list -> (["Steam"])

The command checks which of the specified apps are currently running, retrieves their executable paths, and saves them under the new mode in `modes.json`. Requires the apps being added to be currently running. If any app is not running, the mode will not be created and an error will be returned.

Returns a success response if the mode is created, or a failure response if the mode already exists or if any specified app is not currently running.

### `delete_mode_command`
Deletes an existing mode and all its associated applications from the configuration.

**Parameters:**
- `mode` (string): The name of the mode to delete (e.g., "gaming", "work").

The command removes the specified mode and its app list from `modes.json`. Neither the mode nor any of its apps need to be running for deletion to succeed.

Returns a success response if the mode is deleted, or a failure response if the mode does not exist.

### `app_apps_to_mode_command`
Adds one or more currently running applications to an existing mode by capturing their executable paths and updating `modes.json`.

**Parameters:**
- `mode` (string): The name of the mode to update (e.g., "gaming", "work").
- `apps` (list or string): The app names to add. If provided as a string (e.g., "['steam', 'discord']"), it will be parsed into a list automatically. If given as a quoted string (e.g., "'Steam'") or a plain string (e.g., "Steam"), it will be converted to a list (["Steam"]).

The command verifies which of the specified apps are currently running, retrieves their executable paths, and adds them to the selected mode in `modes.json`. All apps being added must be running; if any are not, the operation fails and returns an error.

Returns a success response if the apps are added to the mode, or a failure response if the mode does not exist or if any specified app is not currently running. Apps that already exist in the mode are skipped to prevent duplicates and do not cause an error.

### `remove_apps_from_mode_command`
Removes one or more applications from an existing mode by updating `modes.json`. The apps do not need to be running to be removed.

**Parameters:**
- `mode` (string): The name of the mode to update (e.g., "gaming", "work").
- `apps` (list or string): The names of the apps to remove. If provided as a string (e.g., "['steam', 'discord']"), it will be parsed into a list automatically. If given as a quoted string (e.g., "'Steam'") or a plain string (e.g., "Steam"), it will be converted to a list (["Steam"]).

The command checks which of the specified apps are present in the selected mode within `modes.json` and removes any that exist.

Returns a success response if the apps are removed from the mode, or a failure response if the mode does not exist. Apps that are not present in the mode are ignored and do not result in an error.

### `close_mode_command`
Closes all applications configured for a specified mode by terminating each app using its saved executable path.

**Parameters:**
- `mode` (string): The name of the mode to close (e.g., "gaming", "work").

The command retrieves the list of apps associated with the given mode from `modes.json` and attempts to close each one. If any app cannot be closed (for example, if it is not running), the others are still closed, and a failure response is returned listing the apps that could not be closed.

Returns a success response if all apps are closed successfully, or a failure response listing any apps that could not be closed.


#### Logging
- Log file location: `%USERPROFILE%\LaunchPad_plugin.log`
- Logging level: INFO
- Format: `%(asctime)s - %(levelname)s - %(message)s`

### Error Handling
- All operations are wrapped in try-except blocks
- Errors are logged to the log file
- Failed operations return a failure response with an error message

### Dependencies
### Dependencies
- Python 3.7+
- Required Python packages:
  - psutil: For process management and app detection
  - Standard library modules: json, logging, os, ast

### Command Processing
The plugin processes commands through a JSON-based protocol:

1. Input Format:
```json
{
    "tool_calls": [
        {
            "func": "command_name",
            "params": {
                "param1": "value1",
                "param2": "value2"
            }
        }
    ]
}
```

2. Output Format:
```json
{
    "success": true|false,
    "message": "Optional message"
}
```

### Adding New Commands
To add a new command:
1. Implement command function with signature: `def new_command(params: dict = None, context: dict = None, system_info: dict = None) -> dict`
2. Add command to `commands` dictionary in `main()`
3. Implement proper error handling and logging
4. Return standardized response using `generate_success_response()` or `generate_failure_response()`
5. Add the function to the `functions` list in `manifest.json` file: 
   ```json
   {
      "name": "new_command",
      "description": "Description of what the command does",
      "tags": ["relevant", "tags"],
      "properties": {
      "parameter_name": {
         "type": "string",
         "description": "Description of the parameter"
      }
      }
   }
   ```
6. Manually test the function:

   First, run the script:
   ``` bash
   python plugin.py
   ```

   Run the initialize command: 
      ``` json
      {
         "tool_calls" : "initialize"
      }
      ```
   Run the new command:
      ``` json
      {
         "tool_calls" : "new_command", 
         "params": {
            "parameter_name": "parameter_value"
         }
      }
      ```
7. Run the setup & build scripts as outlined above, install the plugin by placing the files in the proper location and test your updated plugin. Use variations of standard user messages to make sure the function is adequately documented in the `manifest.json`


## Want to Contribute?


All contributions are welcome.

How to contribute:

- Fork this repository.
- Create a branch:
  ```bash
  git checkout -b feature/my-feature
  ```
- Commit your changes (please sign off your commits to certify your contribution):
  ```bash
  git commit -s -m "Add feature"
  ```
  This adds a "Signed-off-by" line to your commit message, as required by the Developer Certificate of Origin (DCO).
- Push your branch:
  ```bash
  git push origin feature/my-feature
  ```
- Open a Pull Request. Please keep your PR as a draft until you are ready for it to be reviewed.

For more details, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License
This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.