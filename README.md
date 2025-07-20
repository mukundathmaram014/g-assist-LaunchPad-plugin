# LaunchPad G-Assist Plugin

**LaunchPad** is a G-Assist plugin that lets you instantly switch between various different modes that you can configure with different apps by launching groups of apps with a single voice or text command.

Say “start development mode” and it’ll open VSCode, Chrome, Postman — or say “start gaming mode” and it’ll launch your game, Twitch, and Spotify. All modes are customizable, dynamically editable, and stored locally.

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
- Python 3.12+ (for development/building)
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

- hey launchpad,  create mode called gaming for apps steam, chrome, and discord

G-Assist will create a new "gaming" mode using the currently running Steam, Chrome, and Discord. Make sure these apps are already running when you do this command otherwise it will not work

Launch a Mode
Say or type:

- hey launchpad, launch gaming mode

G-Assist will launch all apps configured for the "gaming" mode.

Close a Mode
Say or type:

- hey launchpad, close gaming mode

G-Assist will close all apps in the "gaming" mode.

List Available Modes
Say or type:

- hey launchpad, list modes

G-Assist will show all configured modes.


Remove Apps from a Mode
Say or type:

- hey launchpad, remove apps chrome, discord from gaming mode

G-Assist will remove Notepad and Discord from the "gaming" mode.


Add Apps to an Existing Mode
Say or type:

- hey launchpad, add apps notepad, chrome to gaming mode

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


## Want to Contribute?

All contributions are welcome. 

How to contribute :

- Fork this repository.
- Create a branch 
```bash
(git checkout -b feature/my-feature).
```
- Commit your changes 
```bash
(git commit -m ‘Add feature’).
```

- Push your branch 
```bash
(git push origin feature/my-feature).
```

- Open a Pull Request.

## License
This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.