# ======================================================
# Hububba Utils - Configuration
# ======================================================

# ===== BOT / GUILDS =====
HUBUBBA_GUILD_ID = 1416292142959165545
PROJECT_INFINITE_ID = 1433773040734437460

BOT_STATUS_TEXT = "Hububba Utilities ∞"

# ===== LOGGING =====
LOG_FILE_PATH = "/home/HububbaUtils/logs/bot.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

# ===== BRANDING / COLORS =====
BRAND_COLOR = 0x9B59B6
EMBED_COLOR = 0x9B59B6  # consistency alias for embeds

# ===== CHANNELS =====
# Ticket panel + log channels
TICKET_PANEL_CHANNEL_ID = 1430723770401685684
LOG_CHANNEL_ID = 1430727570365874346

# ===== CATEGORIES =====
SUPPORT_CATEGORY_NAME    = "Support Tickets"
COMMISSION_CATEGORY_NAME = "Commission Tickets"
COMPLAINT_CATEGORY_NAME  = "Complaint Tickets"
ARCHIVE_CATEGORY_NAME    = "Ticket Archive"

# ===== FILE PATHS =====
DATA_DIR = "/home/HububbaUtils/data"
ORDERS_FILE = f"{DATA_DIR}/orders.json"
ORDERS_CSV = "/home/HububbaUtils/orders.csv"   # fallback for CSV-based systems

# ===== PAYPAL API SETTINGS =====
# For LIVE environment
PAYPAL_CLIENT_ID = "AS0qFdttt_myK3fnb-LYNg-Zc_CBE1M8L8qG1z9MSamWqisNlCyHoST7yaNzal0CSqM9Mns-UBrc0qFw"
PAYPAL_CLIENT_SECRET = "ECOFuVgXVUSqCtEOPiGe8gPyMEXtg6w_Mr5V3OS-WivGvia2qVQJbBxs1dgEarRT0RcTGcP8BKfkw3T0"

# Optional: switch to sandbox for testing
PAYPAL_ENV = "live"  # "live" or "sandbox"

PAYPAL_OAUTH_URL   = "https://api-m.paypal.com/v1/oauth2/token" if PAYPAL_ENV == "live" else "https://api-m.sandbox.paypal.com/v1/oauth2/token"
PAYPAL_INVOICE_URL = "https://api-m.paypal.com/v2/invoicing/invoices" if PAYPAL_ENV == "live" else "https://api-m.sandbox.paypal.com/v2/invoicing/invoices"

# ===== TICKETS =====
# Default questions & messages (used by Ticket Modal prompts)
TICKET_QUESTIONS = {
    "Support": [
        "Describe the issue in detail.",
        "How urgent is this problem? (Low / Medium / High)"
    ],
    "Commission": [
        "What do you need built or coded?",
        "What’s your budget (USD)?",
        "Deadline (optional):",
        "Any extra notes?"
    ],
    "Complaint": [
        "Who or what is this complaint about?",
        "Describe the issue.",
        "Provide any proof or screenshots (optional)."
    ],
}

# Ticket footer and color branding
TICKET_FOOTER_TEXT = "Hububba Studios • Project Infinite ∞"
TICKET_COLOR = EMBED_COLOR

# ===== BEHAVIOR FLAGS =====
# Automatically purge ticket panel channel each restart and resend
PURGE_TICKET_PANEL_ON_STARTUP = True
# Automatically archive tickets on close command
AUTO_ARCHIVE_TICKETS = True
# Whether to auto-create missing categories
AUTO_CREATE_TICKET_CATEGORIES = True

# ===== ORDER SYSTEM =====
# Path to persistent order tracking
ORDERS_FILE_PATH = ORDERS_CSV
ORDER_STATUS_OPTIONS = [
    "Open",
    "Looking Into",
    "In Progress",
    "On Hold",
    "Completed",
    "Canceled"
]

# ===== ALLOWED GUILDS =====
ALLOWED_GUILDS = [HUBUBBA_GUILD_ID, PROJECT_INFINITE_ID]

# ===== OTHER OPTIONAL SETTINGS =====
# Logging channel name fallback if ID not found
LOG_CHANNEL_FALLBACK_NAME = "bot-logs"

# Debug flags (for verbose console output)
DEBUG_MODE = False
DEBUG_PAYPAL = False

# ===== END CONFIG =====
