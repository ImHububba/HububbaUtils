# config.py
# Fill in IDs and settings. All IDs are integers.

# =========================
# HUBUBBA'S CODING WORLD
# =========================
HUBUBBA_GUILD_ID = 1416292142959165545  # Hububba's Coding World (home guild)

HUBUBBA_LOGS = {
    "WELCOME": 1416308689203367946,   # Welcome messages
    "GENERAL": 1416295990075592775,   # Message edits/deletions, bans, kicks, locks, etc.
    "BOT": 1416296007196610600        # Bot startup, command usage, errors
}

# =========================
# PROJECT INFINITE
# =========================
PROJECT_INFINITE_ID = 1433773040734437460  # Project Infinite ∞

INFINITE_LOGS = {
    "WELCOME": 1435592716590256240,   # Welcome messages
    "GENERAL": 1435592829526212638,   # Server logs
    "BOT": 1435592888611377212        # Bot logs
}

# Unified map for quick lookup
LOG_CHANNELS = {
    HUBUBBA_GUILD_ID: HUBUBBA_LOGS,
    PROJECT_INFINITE_ID: INFINITE_LOGS,
}

# =========================
# Roles / Permission hierarchy
# =========================
STAFF_ROLE_NAME = "Staff Perms Role"       # Kick, Purge, Timeout, Untimeout
ADMIN_ROLE_NAME = "Admin+ Perms"           # Kick, Purge, Lock, Unlock, Ban, Ping
SUPER_ROLE_NAME = "The One And Only"       # All perms (always allowed)
AUTO_ROLE_NAME = "Member"                  # Auto-assigned on join
STREAM_NOTIS_ROLE_NAME = "Stream Notis"    # Role to ping on go-live

# =========================
# Twitch (optional)
# =========================
TWITCH_CLIENT_ID = "jk88zsgw5gzjqkq0o8hkvh35xi28b9"
TWITCH_CLIENT_SECRET = "qri0o0b14cmmlppqte0b1i0a9qn5if"
TWITCH_USERNAME = "imhububba"  # your Twitch channel name (lowercase)
TWITCH_POLL_SECONDS = 60

# =========================
# Bot presence
# =========================
BOT_STATUS_TEXT = "Hububba Utilities Online"

# =========================
# Logging config
# =========================
LOG_FILE_PATH = "logs/bot.log"
LOG_MAX_BYTES = 2_000_000
LOG_BACKUP_COUNT = 5
