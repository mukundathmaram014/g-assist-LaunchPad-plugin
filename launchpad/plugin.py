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

"""G-Assist LaunchPad Plugin (Protocol V2)

A plugin that manages application modes - groups of apps that can be
launched or closed together with a single command.
"""

import json
import logging
import os
import sys
import ast
import psutil
import win32gui
import win32process
import win32api

# SDK import
_plugin_dir = os.path.dirname(os.path.abspath(__file__))
_libs_path = os.path.join(_plugin_dir, "libs")
if os.path.exists(_libs_path) and _libs_path not in sys.path:
    sys.path.insert(0, _libs_path)

try:
    from gassist_sdk import Plugin, Context
except ImportError as e:
    # Fatal error - write to stderr (not stdout!) and exit
    sys.stderr.write(f"FATAL: Cannot import gassist_sdk: {e}\n")
    sys.stderr.write("Ensure gassist_sdk is in the libs/ folder.\n")
    sys.stderr.flush()
    sys.exit(1)

# =============================================================================
# CONFIGURATION
# =============================================================================

PLUGIN_NAME = "launchpad"
PLUGIN_DIR = os.path.join(
    os.environ.get("PROGRAMDATA", "."), 
    "NVIDIA Corporation", "nvtopps", "rise", "plugins", PLUGIN_NAME
)

LOG_FILE = os.path.join(PLUGIN_DIR, f"{PLUGIN_NAME}.log")

MODES_FILE = os.path.join(PLUGIN_DIR, "modes.json")

os.makedirs(PLUGIN_DIR, exist_ok=True)

# Logging setup
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# =============================================================================
# PLUGIN DEFINITION
# =============================================================================

plugin = Plugin(
    name=PLUGIN_NAME,
    version="2.0.0",
    description="A plugin that launches custom sets of applications based on user-defined modes."
)

# =============================================================================
# APP ALIASES
# =============================================================================

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

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def read_modes_config() -> dict:
    """Read modes from modes.json."""
    try:
        with open(MODES_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read modes config: {str(e)}")
        return {}


def write_modes_config(modes: dict) -> bool:
    """Write modes to modes.json."""
    try:
        with open(MODES_FILE, "w") as f:
            json.dump(modes, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Failed to write modes config: {str(e)}")
        return False


def launch_apps(apps: list[dict]) -> list[str]:
    """Launch apps from list of {"name": str, "path": str} dicts."""
    failed = []
    for app in apps:
        path = app["path"]
        name = app["name"]
        try:
            os.startfile(path)
        except Exception as e:
            logger.error(f"Failed to launch {name} ({path}): {str(e)}")
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
        for proc in psutil.process_iter(["exe"]):
            try:
                if proc.info["exe"] and (os.path.normcase(proc.info["exe"]) == os.path.normcase(path)):
                    proc.terminate()
                    closed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if not closed:
            failed.append(name)
    return failed


def parse_apps_param(apps) -> list[str] | None:
    """Parse the 'apps' parameter which can be a list or string."""
    if isinstance(apps, list):
        if all(isinstance(p, str) for p in apps):
            return apps
        return None
    
    if isinstance(apps, str):
        try:
            parsed = ast.literal_eval(apps)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, str):
                return [parsed]
        except Exception:
            return [apps]
    
    return None


# =============================================================================
# APP MATCHING FUNCTIONS
# =============================================================================

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
    
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            name = proc.info["name"]
            if not name:
                continue
            name_lower = name.lower()
            name_without_ext = name_lower[:-4] if name_lower.endswith(".exe") else name_lower
            
            if name_without_ext == search_lower:
                return proc.info["exe"]
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return None


def match_by_process_name_fuzzy(app_name: str) -> str | None:
    """Find app by partial/fuzzy process name match."""
    search_lower = app_name.lower()
    
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            name = proc.info["name"]
            if not name:
                continue
            name_lower = name.lower()
            name_without_ext = name_lower[:-4] if name_lower.endswith(".exe") else name_lower
            
            # Check if search term is contained in process name
            if search_lower in name_without_ext:
                return proc.info["exe"]
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
    
    for proc in psutil.process_iter(["exe"]):
        try:
            exe_path = proc.info["exe"]
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
    logger.info(f"Searching for app: {app_name}")
    
    # 1. Try alias mapping first
    aliased_name = APP_ALIASES.get(app_name.lower())
    if aliased_name:
        logger.info(f"Found alias: {app_name} -> {aliased_name}")
        result = match_by_process_name_exact(aliased_name)
        if result:
            logger.info(f"Matched via alias: {result}")
            return result
    
    # 2. Try exact process name match
    result = match_by_process_name_exact(app_name)
    if result:
        logger.info(f"Matched via exact process name: {result}")
        return result
    
    # 3. Try fuzzy/partial process name match
    result = match_by_process_name_fuzzy(app_name)
    if result:
        logger.info(f"Matched via fuzzy process name: {result}")
        return result
    
    # 4. Try window title matching
    result = match_by_window_title(app_name)
    if result:
        logger.info(f"Matched via window title: {result}")
        return result
    
    # 5. Try executable metadata
    result = match_by_exe_metadata(app_name)
    if result:
        logger.info(f"Matched via exe metadata: {result}")
        return result
    
    logger.warning(f"No match found for app: {app_name}")
    return None




# =============================================================================
# COMMAND HANDLERS
# =============================================================================

@plugin.command("launch_mode_command")
def launch_mode_command(mode: str = None):
    """Launches all applications for a given mode."""
    logger.info(f"Executing launch_mode_command with mode: {mode}")
    
    if not mode:
        return "Missing 'mode' parameter."
    
    modes = read_modes_config()
    if mode not in modes:
        return f"Mode '{mode}' not found."
    
    failed = launch_apps(modes[mode])
    
    if failed:
        return f"Some apps failed to launch: {failed}"
    return f"Mode '{mode}' launched."


@plugin.command("close_mode_command")
def close_mode_command(mode: str = None):
    """Closes all applications associated with a specified mode."""
    logger.info(f"Executing close_mode_command with mode: {mode}")
    
    if not mode:
        return "Missing 'mode' parameter."
    
    modes = read_modes_config()
    if mode not in modes:
        return f"Mode '{mode}' not found."
    
    failed = close_apps(modes[mode])
    
    if failed:
        return f"Some apps failed to close: {failed}"
    return f"Mode '{mode}' closed."


@plugin.command("get_modes_command")
def get_modes_command():
    """Returns a list of all currently available modes."""
    logger.info("Executing get_modes_command")
    
    modes = read_modes_config()
    return f"Available modes: {list(modes.keys())}"


@plugin.command("add_mode_command")
def add_mode_command(mode: str = None, apps = None):
    """Adds a new mode with a list of application names."""
    logger.info(f"Executing add_mode_command with mode: {mode}, apps: {apps}")
    
    if not mode or apps is None:
        return "Missing 'mode' or 'apps'."
    
    apps_list = parse_apps_param(apps)
    if apps_list is None:
        return "'apps' must be a list of strings."
    
    app_entries = []
    for app in apps_list:
        app_path = get_app_path_by_name(app)
        if app_path:
            app_entries.append({"name": app, "path": app_path})
        else:
            return f"App '{app}' is currently not running or not installed in your system."
    
    modes = read_modes_config()
    if mode in modes:
        return f"Mode '{mode}' already exists."
    
    modes[mode] = app_entries
    
    if not write_modes_config(modes):
        return "Failed to write to modes config."
    
    return f"Mode '{mode}' created with {len(app_entries)} apps."


@plugin.command("delete_mode_command")
def delete_mode_command(mode: str = None):
    """Deletes an entire mode by name."""
    logger.info(f"Executing delete_mode_command with mode: {mode}")
    
    if not mode:
        return "Missing 'mode'."
    
    modes = read_modes_config()
    if mode not in modes:
        return f"Mode '{mode}' does not exist."
    
    del modes[mode]
    
    if not write_modes_config(modes):
        return "Failed to write to modes config."
    
    return f"Mode '{mode}' successfully deleted."


@plugin.command("add_apps_to_mode_command")
def add_apps_to_mode_command(mode: str = None, apps = None):
    """Adds a new list of applications to an existing mode."""
    logger.info(f"Executing add_apps_to_mode_command with mode: {mode}, apps: {apps}")
    
    if not mode or apps is None:
        return "Missing 'mode' or 'apps'."
    
    apps_list = parse_apps_param(apps)
    if apps_list is None:
        return "'apps' must be a list of strings."
    
    app_entries = []
    for app in apps_list:
        app_path = get_app_path_by_name(app)
        if app_path:
            app_entries.append({"name": app, "path": app_path})
        else:
            return f"App '{app}' is currently not running or not installed in your system."
    
    modes = read_modes_config()
    if mode not in modes:
        return f"Mode '{mode}' does not exist."
    
    existing_paths = [entry["path"] for entry in modes[mode]]
    for entry in app_entries:
        if entry["path"] not in existing_paths:
            modes[mode].append(entry)
    
    if not write_modes_config(modes):
        return "Failed to write to modes config."
    
    return f"Apps {apps_list} successfully added to Mode '{mode}'."


@plugin.command("remove_apps_from_mode_command")
def remove_apps_from_mode_command(mode: str = None, apps = None):
    """Removes a list of applications from an existing mode."""
    logger.info(f"Executing remove_apps_from_mode_command with mode: {mode}, apps: {apps}")
    
    if not mode or apps is None:
        return "Missing 'mode' or 'apps'."
    
    apps_list = parse_apps_param(apps)
    if apps_list is None:
        return "'apps' must be a list of strings."
    
    modes = read_modes_config()
    if mode not in modes:
        return f"Mode '{mode}' does not exist."
    
    new_apps = []
    for entry in modes[mode]:
        keep = True
        for app in apps_list:
            if app.lower() == entry["name"].lower():
                keep = False
                break
        if keep:
            new_apps.append(entry)
    
    modes[mode] = new_apps
    
    if not write_modes_config(modes):
        return "Failed to write to modes config."
    
    return f"Apps {apps_list} successfully deleted from Mode '{mode}'."


@plugin.command("list_apps_in_mode_command")
def list_apps_in_mode_command(mode: str = None):
    """Returns a list of all apps stored in a specific mode."""
    logger.info(f"Executing list_apps_in_mode_command with mode: {mode}")
    
    if not mode:
        return "Missing 'mode'."
    
    modes = read_modes_config()
    if mode not in modes:
        return f"Mode '{mode}' does not exist."
    
    app_names = [entry["name"] for entry in modes[mode]]
    return f"Apps in mode '{mode}': {app_names}"


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    logger.info(f"Starting {PLUGIN_NAME} plugin (SDK version)...")
    plugin.run()