# config.py
# Fill in IDs and settings. All IDs are integers.

GUILD_ID = 1416292142959165545  # Hububba's Coding world (home guild)

# Channels
ANNOUNCEMENT_CHANNEL_ID = 1416292813703745577   # Twitch announcements
GENERAL_LOGS_CHANNEL_ID = 1416295990075592775   # message edits/deletions, bans, kicks, locks, etc.
BOT_LOGS_CHANNEL_ID = 1416296007196610600       # bot startup, command usage, errors
WELCOME_CHANNEL_ID = 1416308689203367946        # welcome messages channel

# Roles / Permission hierarchy
STAFF_ROLE_NAME = "Staff Perms Role"            # Kick, Purge, Timeout, Untimeout
ADMIN_ROLE_NAME = "Admin+ Perms"                # Kick, Purge, Lock, Unlock, Ban, Ping
SUPER_ROLE_NAME = "The One And Only"            # All perms (always allowed)
AUTO_ROLE_NAME = "Member"                       # auto-assigned on join
STREAM_NOTIS_ROLE_NAME = "Stream Notis"         # role to ping on go-live

# Twitch (optional, required for live notifications)
TWITCH_CLIENT_ID = "jk88zsgw5gzjqkq0o8hkvh35xi28b9"          # e.g., "abcd1234..."
TWITCH_CLIENT_SECRET = "qri0o0b14cmmlppqte0b1i0a9qn5if"      # e.g., "xyz9876..."
TWITCH_USERNAME = "imhububba"  # your Twitch channel name (lowercase)
TWITCH_POLL_SECONDS = 60

# Bot presence
BOT_STATUS_TEXT = "Hububba Utilities Online"

# Logging config
LOG_FILE_PATH = "logs/bot.log"
LOG_MAX_BYTES = 2_000_000
LOG_BACKUP_COUNT = 5
