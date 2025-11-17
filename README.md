# Chronicler - Personal Activity Logger

A simple background service that chronicles your work by logging keyboard input, clipboard content, application usage, and periodic screenshots. All data is stored in `~/chronicles` as a git repository in human-readable markdown format.

## Why Chronicle Your Digital Life?

> "I have run a keyboard logger, what is the active window and take a screenshot of a window of my machine every 10 minutes, and archive this going on 15 years now... I would never imagined this ends up being as valuable as it is."
>
> — Tobi Lütke, CEO of Shopify ([Acquired Podcast](https://www.acquired.fm/episodes/how-to-live-in-everyone-elses-future-with-shopify-ceo-tobi-lutke))

Tobi Lütke has been logging his digital activity for over 15 years, creating an unprecedented personal archive. This practice has proven invaluable for:

- **Understanding how you spend your time** - Tracking transitions between activities (programming → fundraising → strategic work)
- **Observing belief evolution** - Seeing how your thinking changes over time on key issues
- **Creating a source of truth** - A moment-by-moment archive of how decisions were actually made
- **AI-powered insights** - Modern AI can analyze this data to create clean timelines and patterns
- **Overcoming narrative bias** - The brain optimizes for narrative consistency rather than chronological accuracy; having raw data helps you see what actually happened

As AI tools improve, having a comprehensive personal archive becomes increasingly valuable. You can use it to train AI models on your working style, recover context from years past, and create a genuine historical record of your personal and professional development.

This tool makes it easy to start building your own chronicle.

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
