#!/usr/bin/env python3
"""
Chronicles - Personal Activity Logger
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

from pynput import keyboard
from AppKit import (NSWorkspace, NSPasteboard, NSApplication, NSMenu, NSMenuItem,
                    NSStatusBar, NSVariableStatusItemLength, NSImage, NSApp)
from Foundation import NSObject, NSLog
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
import Quartz.CoreGraphics as CG
from PIL import Image

# Configuration
CHRONICLES_DIR = Path.home() / "chronicles"
LOG_FILE = CHRONICLES_DIR / f"log_{datetime.now().strftime('%Y-%m-%d')}.md"
SCREENSHOT_DIR = CHRONICLES_DIR / "screenshots"
SCREENSHOT_INTERVAL = 600  # 10 minutes

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

    # Create log file with header if it doesn't exist
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"# Activity Log - {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write("This file contains a chronological log of keyboard activity, clipboard events, and screenshots.\n\n")


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


def save_session():
    """Save the current session to log file in simplified markdown format"""
    global current_session

    if not current_session["app"]:
        return

    with data_lock:
        timestamp_start = datetime.fromisoformat(current_session["start_time"])

        # Write simplified markdown format
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"# {current_session['app']} - ({timestamp_start.strftime('%H:%M:%S')})\n")

            # Write typed content if any
            typed_content = "".join(current_session["typed"])
            if typed_content.strip():
                f.write(f"{typed_content}\n")

            f.write("\n")


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

    # Log application focus event
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime('%H:%M:%S')
        f.write(f"**[{timestamp}] Focused: {app_name}**\n\n")


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
                if cmd_pressed:
                    # CMD+Backspace - skip recording this combination
                    pass
                else:
                    # Regular backspace
                    if current_session["typed"]:
                        current_session["typed"].pop()
        except Exception as e:
            pass


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
            capture_output=True
        )

        if result.returncode == 0 and filename.exists():
            return filename
        else:
            return None
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None


def screenshot_loop():
    """Periodic screenshot capture"""
    global last_screenshot_time

    while running:
        current_time = time.time()
        if current_time - last_screenshot_time >= SCREENSHOT_INTERVAL:
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
        time.sleep(10)  # Check every 10 seconds


def commit_to_git():
    """Periodically commit logs to git"""
    while running:
        time.sleep(5)  # Commit every 5 seconds
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
class ChroniclesMenuBar(NSObject):
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

        # Open Chronicles folder
        open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Open Chronicles",
            "openChronicles:",
            ""
        )
        open_item.setTarget_(self)
        menu.addItem_(open_item)

        # Separator
        menu.addItem_(NSMenuItem.separatorItem())

        # Quit item
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit Chronicles",
            "terminate:",
            ""
        )
        menu.addItem_(quit_item)

        self.statusItem.setMenu_(menu)

        # Start logging threads
        setup_chronicles_dir()

        clipboard_thread = Thread(target=monitor_clipboard, daemon=True)
        screenshot_thread = Thread(target=screenshot_loop, daemon=True)
        git_thread = Thread(target=commit_to_git, daemon=True)

        clipboard_thread.start()
        screenshot_thread.start()
        git_thread.start()

        # Start keyboard listener in separate thread
        def start_keyboard():
            try:
                with keyboard.Listener(on_press=on_key_press, on_release=on_key_release) as listener:
                    self.keyboard_listener = listener
                    listener.join()
            except Exception as e:
                NSLog(f"Keyboard listener error: {e}")

        keyboard_thread = Thread(target=start_keyboard, daemon=True)
        keyboard_thread.start()

        print("Chronicles started")
        NSLog("Chronicles started")

    def openChronicles_(self, sender):
        """Open Chronicles folder in Finder"""
        subprocess.run(["open", str(CHRONICLES_DIR)])

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


def main():
    """Main entry point"""

    # Create app first
    app = NSApplication.sharedApplication()
    delegate = ChroniclesMenuBar.alloc().init()
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
