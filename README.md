# Chronicler - Personal Activity Logger

A simple background service that chronicles your work by logging keyboard input, clipboard content, application usage, and periodic screenshots. All data is stored in `~/chronicles` as a git repository in human-readable markdown format.

## Features

- Global keyboard input logging (intercepts all keypresses)
- Clipboard monitoring
- Active application tracking
- Screenshots every 10 minutes
- Auto-commits to git repository
- Human-readable markdown log files
- Filters password fields and sensitive apps

## Setup

1. Create and activate virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Build the macOS app:

```bash
./build_app.sh
```

3. Grant permissions:

   - System Settings → Privacy & Security → Accessibility (add Chronicler.app)
   - System Settings → Privacy & Security → Screen Recording (add Chronicler.app)

4. Run the app:

```bash
open dist/Chronicler.app
```

## Add to Startup Items

1. Open System Settings → General → Login Items
2. Click '+' and add: `dist/Chronicler.app`
3. Chronicler will now start automatically on login

## View Logs

```bash
source venv/bin/activate
python viewer.py
```

## Data Location

All logs stored in: `~/chronicles/`

- Daily log files: `log_YYYY-MM-DD.md`
- Screenshots: `screenshots/screenshot_YYYYMMDD_HHMMSS.png`

## Log Format

Logs are stored in simple, human-readable markdown format:

```markdown
# Application Name - (HH:MM:SS)

typed content here

# Another App - (HH:MM:SS)

more content here
```

## Privacy

- Automatically skips logging in password managers and similar apps
- Filters password field inputs
- All data stored locally only
- Logs are human-readable markdown files
