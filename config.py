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

# Roles
HUBUBBA_ROLES = {
    "STAFF": "Staff Perms Role",       # Kick, Purge, Timeout, Untimeout
    "ADMIN": "Admin+ Perms",           # Kick, Purge, Lock, Unlock, Ban, Ping
    "SUPER": "The One And Only",       # All perms (always allowed)
    "AUTO": "Member",                  # Auto-assigned on join
    "STREAM_NOTIS": "Stream Notis"     # Role to ping on go-live
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

# Roles (by ID)
INFINITE_ROLES = {
    "STAFF": 1433773953528234097,     # Mod role
    "ADMIN": 1433774200749031434,     # Admin+ role
    "AUTO": 1433773858607071405       # Default role on join
}

# Unified log + role maps
LOG_CHANNELS = {
    HUBUBBA_GUILD_ID: HUBUBBA_LOGS,
    PROJECT_INFINITE_ID: INFINITE_LOGS,
}

ROLE_MAP = {
    HUBUBBA_GUILD_ID: HUBUBBA_ROLES,
    PROJECT_INFINITE_ID: INFINITE_ROLES,
}

# =========================
# GUILD SYNC + ACCESS
# =========================
ALLOWED_GUILDS = [HUBUBBA_GUILD_ID, PROJECT_INFINITE_ID]

# =========================
# Twitch (optional)
# =========================
TWITCH_CLIENT_ID = "jk88zsgw5gzjqkq0o8hkvh35xi28b9"
TWITCH_CLIENT_SECRET = "qri0o0b14cmmlppqte0b1i0a9qn5if"
TWITCH_USERNAME = "imhububba"
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
