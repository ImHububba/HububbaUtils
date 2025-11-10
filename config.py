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

# ===== CHANNELS =====
TICKET_PANEL_CHANNEL_ID = 1430723770401685684
LOG_CHANNEL_ID          = 1430727570365874346

# ===== CATEGORIES =====
SUPPORT_CATEGORY_NAME    = "Support Tickets"
COMMISSION_CATEGORY_NAME = "Commission Tickets"
COMPLAINT_CATEGORY_NAME  = "Complaint Tickets"
ARCHIVE_CATEGORY_NAME    = "Ticket Archive"

# ===== FILE PATHS =====
DATA_DIR    = "/home/HububbaUtils/data"
ORDERS_FILE = f"{DATA_DIR}/orders.json"

# ===== PAYPAL API (LIVE) =====
PAYPAL_CLIENT_ID = "AS0qFdttt_myK3fnb-LYNg-Zc_CBE1M8L8qG1z9MSamWqisNlCyHoST7yaNzal0CSqM9Mns-UBrc0qFw"
PAYPAL_SECRET    = "ECOFuVgXVUSqCtEOPiGe8gPyMEXtg6w_Mr5V3OS-WivGvia2qVQJbBxs1dgEarRT0RcTGcP8BKfkw3T0"

PAYPAL_OAUTH_URL   = "https://api-m.paypal.com/v1/oauth2/token"
PAYPAL_INVOICE_URL = "https://api-m.paypal.com/v2/invoicing/invoices"

# ===== ALLOWED GUILDS =====
ALLOWED_GUILDS = [HUBUBBA_GUILD_ID, PROJECT_INFINITE_ID]
