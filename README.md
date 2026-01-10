# LaunchPad G-Assist Plugin

<p align="center">
  <a href="https://www.youtube.com/watch?v=8hIFAeJRz9o">
    <img src="https://img.youtube.com/vi/8hIFAeJRz9o/0.jpg" alt="LaunchPad Demo" width="48%">
  </a>
  <img src="launchpad-photo.png" alt="LaunchPad Screenshot" width="48%">
</p>

<p align="center" style="font-size: 0.9em; color: gray;">
  Click on the image above to watch the demo video
</p>

**LaunchPad** is a G-Assist plugin that enables you to instantly switch between custom modes, for which you can configure with groups of applications. LaunchPad allows you to open sets of apps with a single voice or text command, streamlining your workflow and productivity.

For example, say “start development mode” to automatically launch VSCode, Chrome, and Postman, or “start gaming mode” to open your game, Twitch, and Spotify. All modes are fully customizable, can be edited dynamically, and are stored locally for quick access.

---

## What Can It Do?
- Create new modes based on currently running apps
- Launch your configured modes (like `development`, `gaming`, `focus`)
- Add/remove apps from existing modes
- List apps in a specific mode
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

List Apps in a Mode

Say or type:

```text
hey launchpad, list apps in gaming mode
```

G-Assist will show all apps configured for the "gaming" mode by their names.

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
The plugin automatically logs all activity to:
```bash
%PROGRAMDATA%\NVIDIA Corporation\nvtopps\rise\plugins\launchpad\launchpad.log
```

It tracks:
- Plugin startup and shutdown
- Command reception and processing
- Error conditions
- Function execution details

## Developer Documentation

### Plugin Architecture
The LaunchPad plugin is a Python-based G-Assist extension built on **Protocol V2** using the `gassist_sdk`. It uses a decorator-based command system where commands are registered with `@plugin.command()`. The SDK handles all communication with G-Assist, including JSON message parsing and response formatting.

**Key V2 differences from V1:**
- Uses `gassist_sdk.Plugin` class instead of manual stdin/stdout handling
- Commands are decorated functions rather than dictionary entries
- No manual `read_command()` / `write_response()` functions needed
- Plugin lifecycle managed by `plugin.run()`
- Configuration files stored in `%PROGRAMDATA%\NVIDIA Corporation\nvtopps\rise\plugins\launchpad\`

### Modes

Modes are stored in the `modes.json` file as a dictionary, where each key is a mode name and the value is a list of application entries. Each entry contains both the user-friendly app name and the executable path.

Example structure:

```json
{
  "gaming": [
    {"name": "Steam", "path": "C:/Program Files/Steam/steam.exe"},
    {"name": "Discord", "path": "C:/Program Files/Discord/discord.exe"}
  ],
  "work": [
    {"name": "vscode", "path": "C:/Program Files/VSCode/Code.exe"},
    {"name": "Chrome", "path": "C:/Program Files/Chrome/Application/chrome.exe"}
  ]
}
```

This structure preserves the original app name you used when creating the mode, making it easier to manage and display apps.

### App Aliases

LaunchPad includes a built-in alias system to help match common app names to their actual process names. This allows you to use friendly names like "vscode" instead of needing to know the actual process name "code".

Current aliases include:

| User-Friendly Name | Process Name |
|--------------------|-------------|
| `edge`, `microsoft edge` | `msedge` |
| `google chrome` | `chrome` |
| `vscode`, `vs code`, `visual studio code` | `code` |
| `teams`, `microsoft teams` | `ms-teams` |
| `epic games`, `epic` | `epicgameslauncher` |
| `file explorer` | `explorer` |

**Adding Custom Aliases:**

If you find an app that isn't being detected properly, you can add your own alias by editing the `APP_ALIASES` dictionary in `plugin.py`:

```python
APP_ALIASES = {
    # Add your custom alias here
    "my app name": "actualprocessname",
    # existing aliases...
}
```

To find the actual process name, open Task Manager, go to the "Details" tab, and look for the `.exe` name (without the extension).

**Contribute Your Alias:**

If you add a useful alias, please consider submitting a pull request to add it to the main project! This helps others who may face the same issue in the future. See the [Contributing](#want-to-contribute) section for how to submit a PR.

### Available Commands

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

### `list_apps_in_mode_command`
Lists all applications configured for a specified mode, displaying their user-friendly names.

**Parameters:**
- `mode` (string): The name of the mode to list apps for (e.g., "gaming", "work").

The command retrieves the list of apps associated with the given mode from `modes.json` and returns their names (not the full executable paths). This provides a clean, readable list of what apps are in a mode.

Returns a success response with the list of app names, or a failure response if the mode does not exist.

#### Logging
- Log file location: `%PROGRAMDATA%\NVIDIA Corporation\nvtopps\rise\plugins\launchpad\launchpad.log`
- Logging level: INFO
- Format: `%(asctime)s - %(levelname)s - %(message)s`

### Error Handling
- All operations are wrapped in try-except blocks
- Errors are logged to the log file
- Failed operations return a failure response with an error message

### Dependencies
- Python 3.7+
- Required Python packages:
  - gassist_sdk: G-Assist SDK for Protocol V2 communication
  - psutil: For process management and app detection
  - pywin32: For Windows API access (win32gui, win32process, win32api)
  - Standard library modules: json, logging, os, ast

### Command Processing
The plugin uses the `gassist_sdk` for Protocol V2 communication. Commands are registered using the `@plugin.command()` decorator:

```python
@plugin.command("command_name")
def command_name(param1: str = None, param2: str = None):
    """Command description."""
    # Implementation
    return "Response message"
```

The SDK handles all JSON parsing and response formatting automatically. Commands simply return a string message.

### Adding New Commands
To add a new command:

1. Add a new decorated function in `plugin.py`:
   ```python
   @plugin.command("new_command")
   def new_command(param1: str = None):
       """Description of what the command does."""
       logger.info(f"Executing new_command with param1: {param1}")
       
       # Your implementation here
       
       return "Success message"
   ```

2. Add the function to the `functions` list in `manifest.json`:
   ```json
   {
      "name": "new_command",
      "description": "Description of what the command does",
      "tags": ["relevant", "tags"],
      "properties": {
         "param1": {
            "type": "string",
            "description": "Description of the parameter"
         }
      }
   }
   ```

3. Test the plugin by running:
   ```bash
   .\setup.bat launchpad -deploy
   ```
   Then restart G-Assist and test your command with voice or text input.


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