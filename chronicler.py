#!/usr/bin/env python3
"""
Chronicler - Personal Activity Logger
Logs keyboard input, clipboard, app activity, and screenshots to ~/chronicles
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path
from threading import Thread, Lock
import signal
import objc
import ctypes
import ctypes.util

from pynput import keyboard
from AppKit import (NSWorkspace, NSPasteboard, NSApplication, NSMenu, NSMenuItem,
                    NSStatusBar, NSVariableStatusItemLength, NSImage, NSApp)
from Foundation import NSObject, NSLog
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
import Quartz.CoreGraphics as CG
from PIL import Image
from markwhen_parser import MarkwhenParser

# Configuration
CHRONICLES_DIR = Path.home() / "chronicles"
SCREENSHOT_DIR = CHRONICLES_DIR / "screenshots"
SCREENSHOT_INTERVAL = 600  # 10 minutes
FLUSH_INTERVAL = 30  # Flush logs every 30 seconds

# Password-related apps to skip
SENSITIVE_APPS = {
    "1Password", "LastPass", "Bitwarden", "KeePassXC", "Keeper",
    "Dashlane", "Password", "Keychain Access", "ssh", "sudo"
}

# Global state
current_session = {
    "app": None,
    "window": None,
    "start_time": None,
    "typed": [],
    "clipboard_items": []
}
last_clipboard = ""
last_screenshot_time = 0
data_lock = Lock()
running = True
cmd_pressed = False

# Markwhen parser instance
markwhen_parser = MarkwhenParser()


def get_log_file():
    """Get the log file for the current day (dynamic)"""
    return CHRONICLES_DIR / f"log_{datetime.now().strftime('%Y-%m-%d')}.md"


def ensure_log_file_frontmatter(log_file):
    """Ensure log file exists with markwhen frontmatter"""
    today = datetime.now()
    title = f"Activity Log - {today.strftime('%Y-%m-%d')}"
    date = today.strftime('%Y-%m-%d')
    markwhen_parser.ensure_frontmatter(log_file, title=title, date=date)


def parse_last_event(log_file):
    """Parse the last event from the log file to get the focused program"""
    try:
        return markwhen_parser.parse_last_event(log_file)
    except Exception as e:
        NSLog(f"Error parsing last event: {e}")
        return None


def setup_chronicles_dir():
    """Set up the chronicles directory and git repo"""
    CHRONICLES_DIR.mkdir(exist_ok=True)
    SCREENSHOT_DIR.mkdir(exist_ok=True)

    # Initialize git repo if not exists
    if not (CHRONICLES_DIR / ".git").exists():
        subprocess.run(["git", "init"], cwd=CHRONICLES_DIR, capture_output=True)
        gitignore = CHRONICLES_DIR / ".gitignore"
        gitignore.write_text("*.pyc\n__pycache__/\n.DS_Store\n")
        subprocess.run(["git", "add", ".gitignore"], cwd=CHRONICLES_DIR, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=CHRONICLES_DIR, capture_output=True)

    # Ensure log file exists with frontmatter
    log_file = get_log_file()
    ensure_log_file_frontmatter(log_file)


def get_active_app():
    """Get the currently active application and window title"""
    workspace = NSWorkspace.sharedWorkspace()
    active_app = workspace.activeApplication()
    app_name = active_app.get('NSApplicationName', 'Unknown')

    # Get window title using Quartz
    window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    for window in window_list:
        if window.get('kCGWindowOwnerName') == app_name and window.get('kCGWindowLayer') == 0:
            window_title = window.get('kCGWindowName', '')
            return app_name, window_title

    return app_name, ''


def is_sensitive_context():
    """Check if we're in a sensitive context (password fields, etc.)"""
    app_name, _ = get_active_app()

    # Check if app is in sensitive list
    for sensitive in SENSITIVE_APPS:
        if sensitive.lower() in app_name.lower():
            return True

    return False


def is_system_sleeping():
    """Check if the system is sleeping or idle using IOKit"""
    try:
        # Load IOKit framework
        iokit = ctypes.cdll.LoadLibrary(ctypes.util.find_library('IOKit'))

        # Get IOKit registry entry for power management
        # Function signatures
        iokit.IOServiceGetMatchingService.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        iokit.IOServiceGetMatchingService.restype = ctypes.c_void_p
        iokit.IOServiceMatching.argtypes = [ctypes.c_char_p]
        iokit.IOServiceMatching.restype = ctypes.c_void_p
        iokit.IORegistryEntryCreateCFProperty.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]
        iokit.IORegistryEntryCreateCFProperty.restype = ctypes.c_void_p
        iokit.IOObjectRelease.argtypes = [ctypes.c_void_p]

        # Alternative approach: Check system idle time using CG
        idle_time = CG.CGEventSourceSecondsSinceLastEventType(
            CG.kCGEventSourceStateHIDSystemState,
            CG.kCGAnyInputEventType
        )

        # If system has been idle for more than 5 minutes, consider it sleeping/idle
        # This threshold can be adjusted based on preference
        IDLE_THRESHOLD = 300  # 5 minutes in seconds

        if idle_time > IDLE_THRESHOLD:
            NSLog(f"System idle for {idle_time:.0f} seconds - skipping screenshot")
            return True

        return False

    except Exception as e:
        NSLog(f"Error checking system sleep state: {e}")
        # If we can't determine, assume system is awake (fail-safe)
        return False


def append_or_create_event(app_name, typed_content, timestamp):
    """Append to last event if same app, otherwise create new entry.
    Always uses the current day's log file."""
    # Always get the current day's file (handles day transitions)
    log_file = get_log_file()
    try:
        markwhen_parser.append_event(log_file, app_name, timestamp, typed_content)
    except Exception as e:
        NSLog(f"Error writing to log file {log_file}: {e}")


def save_session(flush_typed=True):
    """Save the current session to log file in markwhen format"""
    global current_session

    if not current_session["app"]:
        return

    # Always get the current day's log file (handles day transitions)
    log_file = get_log_file()
    ensure_log_file_frontmatter(log_file)

    with data_lock:
        timestamp_start = datetime.fromisoformat(current_session["start_time"])
        
        # Check if day has changed - if so, start new session
        current_day = datetime.now().strftime('%Y-%m-%d')
        session_day = timestamp_start.strftime('%Y-%m-%d')
        
        if current_day != session_day:
            # Day changed, start fresh session for new day
            current_session = {
                "app": current_session["app"],  # Keep current app
                "window": current_session.get("window"),
                "start_time": datetime.now().isoformat(),
                "typed": current_session["typed"],  # Keep any pending typed content
                "clipboard_items": []
            }
            timestamp_start = datetime.now()
        
        # Get typed content
        typed_content = "".join(current_session["typed"])
        
        if flush_typed and typed_content:
            # Append or create event (always uses current day's file)
            append_or_create_event(current_session["app"], typed_content, timestamp_start)
            # Clear typed content after flushing
            current_session["typed"] = []


def start_new_session(app_name, window_title):
    """Start a new logging session"""
    global current_session

    save_session()  # Save previous session

    current_session = {
        "app": app_name,
        "window": window_title,
        "start_time": datetime.now().isoformat(),
        "typed": [],
        "clipboard_items": []
    }


def on_key_press(key):
    """Handle keyboard events"""
    global cmd_pressed

    if is_sensitive_context():
        return

    app_name, window_title = get_active_app()

    # Start new session if app changed
    if current_session["app"] != app_name:
        start_new_session(app_name, window_title)

    with data_lock:
        try:
            # Track CMD key state
            if key == keyboard.Key.cmd or key == keyboard.Key.cmd_r:
                cmd_pressed = True
                return

            if hasattr(key, 'char') and key.char:
                current_session["typed"].append(key.char)
            elif key == keyboard.Key.space:
                current_session["typed"].append(" ")
            elif key == keyboard.Key.enter:
                current_session["typed"].append("\n")
            elif key == keyboard.Key.tab:
                current_session["typed"].append("\t")
            elif key == keyboard.Key.backspace:
                # Log backspace as arrow symbol instead of removing characters
                current_session["typed"].append("←")
            elif key == keyboard.Key.delete:
                # Log delete key
                current_session["typed"].append("⌦")
            elif key == keyboard.Key.left:
                current_session["typed"].append("◀")
            elif key == keyboard.Key.right:
                current_session["typed"].append("▶")
            elif key == keyboard.Key.up:
                current_session["typed"].append("▲")
            elif key == keyboard.Key.down:
                current_session["typed"].append("▼")
        except Exception as e:
            NSLog(f"Error in on_key_press: {e}")


def on_key_release(key):
    """Handle key release events"""
    global cmd_pressed

    try:
        # Track CMD key release
        if key == keyboard.Key.cmd or key == keyboard.Key.cmd_r:
            cmd_pressed = False
    except Exception as e:
        pass


def monitor_clipboard():
    """Monitor clipboard for changes"""
    global last_clipboard

    pasteboard = NSPasteboard.generalPasteboard()

    while running:
        try:
            # Get clipboard content
            content = pasteboard.stringForType_("public.utf8-plain-text")

            if content and content != last_clipboard:
                last_clipboard = content

                if not is_sensitive_context():
                    with data_lock:
                        if current_session["app"]:
                            current_session["clipboard_items"].append({
                                "timestamp": datetime.now().isoformat(),
                                "content": content[:500]  # Limit length
                            })

            time.sleep(1)
        except Exception as e:
            time.sleep(1)


def take_screenshot():
    """Take a screenshot and save to screenshots directory"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = SCREENSHOT_DIR / f"screenshot_{timestamp}.png"

        # Use screencapture command for better quality
        result = subprocess.run(
            ['screencapture', '-x', '-C', str(filename)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and filename.exists():
            print(f"Screenshot saved: {filename}")
            return filename
        else:
            print(f"Screenshot failed: returncode={result.returncode}, stderr={result.stderr}")
            NSLog(f"Screenshot failed: returncode={result.returncode}, stderr={result.stderr}")
            return None
    except Exception as e:
        print(f"Screenshot error: {e}")
        NSLog(f"Screenshot error: {e}")
        return None


def screenshot_loop():
    """Periodic screenshot capture"""
    global last_screenshot_time

    while running:
        current_time = time.time()
        if current_time - last_screenshot_time >= SCREENSHOT_INTERVAL:
            # Check if system is sleeping/idle before taking screenshot
            if not is_system_sleeping():
                filename = take_screenshot()
                if filename:
                    last_screenshot_time = current_time
                    # Log screenshot in current session
                    with data_lock:
                        if current_session["app"]:
                            current_session["clipboard_items"].append({
                                "timestamp": datetime.now().isoformat(),
                                "screenshot": str(filename)
                            })
            else:
                # System is sleeping/idle, skip screenshot but reset timer to check again soon
                NSLog("Skipping screenshot - system is idle/sleeping")
                print("Skipping screenshot - system is idle/sleeping")
                last_screenshot_time = current_time
        time.sleep(10)  # Check every 10 seconds


def flush_logs():
    """Periodically flush logs to ensure continuous writing"""
    while running:
        time.sleep(FLUSH_INTERVAL)
        try:
            save_session(flush_typed=True)
        except Exception as e:
            NSLog(f"Error flushing logs: {e}")


def commit_to_git():
    """Periodically commit logs to git"""
    while running:
        time.sleep(300)  # Commit every 5 minutes (less frequent)
        try:
            subprocess.run(["git", "add", "."], cwd=CHRONICLES_DIR, capture_output=True)
            commit_msg = f"Chronicle update {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=CHRONICLES_DIR,
                capture_output=True,
                text=True
            )
        except Exception as e:
            pass


def signal_handler(sig, frame):
    """Handle shutdown gracefully"""
    global running
    print("\nShutting down chronicler...")
    running = False
    save_session()
    # Force exit for NSApplication
    os._exit(0)


# Menu bar app delegate
class ChroniclerMenuBar(NSObject):
    statusbar = None
    keyboard_listener = None

    def applicationDidFinishLaunching_(self, notification):
        """Set up the menu bar when app launches"""
        # Create menu bar item
        self.statusbar = NSStatusBar.systemStatusBar()
        self.statusItem = self.statusbar.statusItemWithLength_(NSVariableStatusItemLength)
        self.statusItem.setTitle_("⏺")  # Record symbol

        # Create menu
        menu = NSMenu.alloc().init()

        # Open Chronicler folder
        open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Open Chronicler",
            "openChronicler:",
            ""
        )
        open_item.setTarget_(self)
        menu.addItem_(open_item)

        # Open System Settings for Input Monitoring
        settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Setup Permissions",
            "openPermissions:",
            ""
        )
        settings_item.setTarget_(self)
        menu.addItem_(settings_item)

        # Separator
        menu.addItem_(NSMenuItem.separatorItem())

        # Quit item
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit Chronicler",
            "terminate:",
            ""
        )
        menu.addItem_(quit_item)

        self.statusItem.setMenu_(menu)

        # Start logging threads
        setup_chronicles_dir()

        # Take initial screenshot to confirm app is working
        global last_screenshot_time
        print("Taking initial screenshot...")
        NSLog("Taking initial screenshot...")
        initial_screenshot = take_screenshot()
        if initial_screenshot:
            last_screenshot_time = time.time()
            print(f"Initial screenshot saved: {initial_screenshot}")
            NSLog(f"Initial screenshot saved: {initial_screenshot}")
        else:
            print("Initial screenshot failed - check Screen Recording permissions")
            NSLog("Initial screenshot failed - check Screen Recording permissions")

        clipboard_thread = Thread(target=monitor_clipboard, daemon=True)
        screenshot_thread = Thread(target=screenshot_loop, daemon=True)
        git_thread = Thread(target=commit_to_git, daemon=True)
        flush_thread = Thread(target=flush_logs, daemon=True)

        clipboard_thread.start()
        screenshot_thread.start()
        git_thread.start()
        flush_thread.start()

        # Start keyboard listener with error recovery
        def start_keyboard():
            retry_count = 0
            max_retries = 10
            
            while running and retry_count < max_retries:
                try:
                    print("Starting keyboard listener...")
                    NSLog("Starting keyboard listener...")

                    # Create listener
                    listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
                    self.keyboard_listener = listener
                    listener.start()

                    print("Keyboard listener started")
                    NSLog("Keyboard listener started")

                    # The listener will now run until it fails or app quits
                    listener.join()
                    
                    # If we get here, listener stopped
                    if running:
                        retry_count += 1
                        error_msg = f"Keyboard listener stopped unexpectedly (attempt {retry_count}/{max_retries})"
                        NSLog(error_msg)
                        print(error_msg)
                        
                        if retry_count < max_retries:
                            # Wait before retrying
                            time.sleep(5)
                        else:
                            # Show alert after max retries
                            from AppKit import NSAlert
                            alert = NSAlert.alloc().init()
                            alert.setMessageText_("Keyboard Logging Failed")
                            alert.setInformativeText_("Keyboard listener stopped multiple times. Please check Input Monitoring permissions in System Settings.")
                            alert.runModal()
                            break

                except Exception as e:
                    retry_count += 1
                    error_msg = f"Keyboard listener FAILED (attempt {retry_count}/{max_retries}): {e}"
                    NSLog(error_msg)
                    print(error_msg)
                    import traceback
                    tb = traceback.format_exc()
                    NSLog(f"Traceback: {tb}")
                    print(f"Traceback: {tb}")

                    if retry_count >= max_retries:
                        # Show alert to user
                        from AppKit import NSAlert
                        alert = NSAlert.alloc().init()
                        alert.setMessageText_("Keyboard Logging Failed")
                        alert.setInformativeText_(f"Error: {e}\n\nPlease grant Input Monitoring permission in System Settings → Privacy & Security → Input Monitoring")
                        alert.runModal()
                        break
                    else:
                        # Wait before retrying
                        time.sleep(5)

        keyboard_thread = Thread(target=start_keyboard, daemon=True)
        keyboard_thread.start()

        print("Chronicler started")
        NSLog("Chronicler started")

    def openChronicler_(self, sender):
        """Open Chronicler folder in Finder"""
        subprocess.run(["open", str(CHRONICLES_DIR)])

    def openPermissions_(self, sender):
        """Open System Settings to Input Monitoring"""
        subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"])

    def applicationWillTerminate_(self, notification):
        """Clean up on quit"""
        global running
        running = False
        save_session()
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
            except:
                pass

    def dummyCallback_(self, timer):
        """Dummy callback to allow Python signal processing"""
        pass


def check_accessibility_permission():
    """Check if we have accessibility/input monitoring permission"""
    try:
        from ApplicationServices import (
            AXIsProcessTrusted,
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt
        )
        from CoreFoundation import CFDictionaryCreate, kCFBooleanTrue

        # Check if we're trusted (have accessibility permission)
        trusted = AXIsProcessTrusted()

        if not trusted:
            print("App does not have Accessibility permission")
            NSLog("App does not have Accessibility permission - requesting...")

            # Request permission (this will show the system prompt)
            options = CFDictionaryCreate(
                None,
                [kAXTrustedCheckOptionPrompt],
                [kCFBooleanTrue],
                1,
                None,
                None
            )
            AXIsProcessTrustedWithOptions(options)
            return False
        else:
            print("App has Accessibility permission")
            NSLog("App has Accessibility permission")
            return True
    except Exception as e:
        print(f"Error checking accessibility permission: {e}")
        NSLog(f"Error checking accessibility permission: {e}")
        return False


def main():
    """Main entry point"""

    # Check permissions BEFORE creating the app
    print("Checking accessibility permission...")
    has_permission = check_accessibility_permission()

    if not has_permission:
        print("\n" + "="*60)
        print("PERMISSION REQUIRED")
        print("="*60)
        print("\nChronicler needs Accessibility permission to log keyboard input.")
        print("\nA system dialog should have appeared asking for permission.")
        print("If not, please:")
        print("  1. Go to System Settings → Privacy & Security → Accessibility")
        print("  2. Click the '+' button")
        print("  3. Navigate to and select: Chronicler.app")
        print("  4. Toggle it ON")
        print("  5. Restart Chronicler")
        print("\n" + "="*60 + "\n")

    # Create app first
    app = NSApplication.sharedApplication()
    delegate = ChroniclerMenuBar.alloc().init()
    app.setDelegate_(delegate)

    # Install signal handlers that actually work with NSApplication
    def sigint_handler(sig, frame):
        """Handle SIGINT (Ctrl-C) by terminating the NSApplication"""
        print("\nReceived interrupt, shutting down...")
        global running
        running = False
        save_session()
        # Terminate the NSApplication event loop
        app.terminate_(None)

    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigint_handler)

    # Make Python check for signals by installing a dummy timer
    # This is needed because NSApplication.run() blocks signal delivery
    from Foundation import NSTimer
    def dummy_callback_(timer):
        # Just exists to let Python process signals
        pass

    # Create a repeating timer to allow signal processing
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        0.5,  # Check every 0.5 seconds
        delegate,
        'dummyCallback:',
        None,
        True
    )

    # Run app
    app.run()


if __name__ == "__main__":
    main()
