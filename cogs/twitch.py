# cogs/twitch.py
import aiohttp
import discord
from discord.ext import commands, tasks
import time

import config

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_STREAMS_URL = "https://api.twitch.tv/helix/streams"
TWITCH_PURPLE = 0x9146FF  # Twitch brand purple

HEARTBEAT_EVERY_POLLS = 5  # send a lightweight "searching..." heartbeat every N polls to Bot Logs

class TwitchCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._session: aiohttp.ClientSession | None = None
        self._app_access_token: str | None = None
        self._token_expiry: float = 0.0
        self._was_live = False
        self._warned_missing_creds = False
        self._poll_counter = 0
        self.poll_twitch.start()

    def cog_unload(self):
        self.poll_twitch.cancel()

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

    async def _log_bot(self, message: str):
        """Log to the Bot Logs channel."""
        chan = self.bot.get_channel(config.BOT_LOGS_CHANNEL_ID)
        if isinstance(chan, discord.TextChannel):
            await chan.send(message)

    async def _get_app_access_token(self) -> str | None:
        # Return cached if still valid
        if self._app_access_token and time.time() < self._token_expiry - 60:
            return self._app_access_token

        cid = (getattr(config, "TWITCH_CLIENT_ID", "") or "").strip()
        secret = (getattr(config, "TWITCH_CLIENT_SECRET", "") or "").strip()
        if not cid or not secret:
            return None

        await self._ensure_session()
        await self._log_bot("🔐 Refreshing Twitch app access token…")
        async with self._session.post(
            TWITCH_TOKEN_URL,
            params={"client_id": cid, "client_secret": secret, "grant_type": "client_credentials"},
        ) as resp:
            if resp.status != 200:
                await self._log_bot(f"❌ Token request failed (HTTP {resp.status}).")
                return None
            data = await resp.json()
            self._app_access_token = data.get("access_token")
            self._token_expiry = time.time() + data.get("expires_in", 0)
            await self._log_bot("✅ Token acquired.")
            return self._app_access_token

    async def _is_live(self) -> tuple[bool, dict]:
        """
        Returns (is_live, data). If live, data includes: title, game_name, thumbnail_url.
        """
        username = (getattr(config, "TWITCH_USERNAME", "") or "").lower().strip()
        if not username:
            return (False, {})

        token = await self._get_app_access_token()
        if not token:
            return (False, {})

        await self._ensure_session()
        headers = {
            "Client-ID": config.TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {token}",
        }
        params = {"user_login": username}
        async with self._session.get(TWITCH_STREAMS_URL, headers=headers, params=params) as resp:
            if resp.status != 200:
                await self._log_bot(f"❌ Helix /streams failed (HTTP {resp.status}).")
                return (False, {})
            payload = await resp.json()
            streams = payload.get("data", [])
            if not streams:
                return (False, {})
            s = streams[0]
            data = {
                "title": s.get("title", ""),
                "game_name": s.get("game_name", "") or s.get("game_id", ""),
                "thumbnail_url": s.get("thumbnail_url", ""),  # contains {width}x{height}
            }
            return (True, data)

    @tasks.loop(seconds=getattr(config, "TWITCH_POLL_SECONDS", 60))
    async def poll_twitch(self):
        # Heartbeat (throttled) so you can see it's actively searching
        self._poll_counter += 1
        if self._poll_counter % HEARTBEAT_EVERY_POLLS == 1:  # 1, 6, 11, …
            await self._log_bot("🔎 Polling Twitch for live status…")

        # If creds are missing, warn once and keep looping (so it self-heals after you add creds)
        if not (getattr(config, "TWITCH_CLIENT_ID", "") and getattr(config, "TWITCH_CLIENT_SECRET", "") and getattr(config, "TWITCH_USERNAME", "")):
            if not self._warned_missing_creds:
                await self._log_bot("⚠️ Twitch notifications disabled: set TWITCH_CLIENT_ID/SECRET/USERNAME in config.py")
                self._warned_missing_creds = True
            return

        try:
            is_live, data = await self._is_live()
            # Processing log (title/game shown if live)
            if is_live:
                await self._log_bot(f"🟣 Processing: LIVE detected — title='{data.get('title','')}', game='{data.get('game_name','')}'.")
            else:
                if self._poll_counter % HEARTBEAT_EVERY_POLLS == 1:
                    await self._log_bot("🟡 Processing: still offline.")

            # Post when it goes offline → live (and on first detection after startup)
            if is_live and not self._was_live:
                await self._log_bot("📣 Announcing go-live…")
                await self._announce_live(data)
                await self._log_bot("✅ Go-live announcement sent.")
            self._was_live = is_live

        except Exception as e:
            await self._log_bot(f"❌ Twitch poll error: `{e}`")

    async def _announce_live(self, data: dict):
        username = config.TWITCH_USERNAME.lower()
        url = f"https://www.twitch.tv/{username}"

        title = data.get("title") or "Streaming on Twitch!"
        game = data.get("game_name") or "—"
        thumb = data.get("thumbnail_url") or ""
        # Replace {width}x{height} with actual size to get a preview image.
        if "{width}" in thumb and "{height}" in thumb:
            thumb = thumb.replace("{width}", "1280").replace("{height}", "720")

        embed = discord.Embed(
            title="🔴 LIVE NOW",
            description=f"**{title}**",
            color=TWITCH_PURPLE
        )
        embed.add_field(name="Game", value=game, inline=True)
        embed.add_field(name="Watch", value=f"[twitch.tv/{username}]({url})", inline=True)
        embed.set_image(url=thumb)
        embed.set_footer(text="Twitch", icon_url="https://static.twitchcdn.net/assets/favicon-32-e29e246c157142c94346.png")

        ann = self.bot.get_channel(config.ANNOUNCEMENT_CHANNEL_ID)
        if not isinstance(ann, discord.TextChannel):
            await self._log_bot("❌ Announcement channel not found or not a text channel.")
            return

        # Role ping: "Stream Notis"
        role_name = getattr(config, "STREAM_NOTIS_ROLE_NAME", "Stream Notis")
        role = discord.utils.get(ann.guild.roles, name=role_name)
        content = role.mention if role else None
        if role is None:
            await self._log_bot(f"⚠️ Role '{role_name}' not found; sending announcement without a ping.")

        await ann.send(
            content=content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

        gl = self.bot.get_channel(config.GENERAL_LOGS_CHANNEL_ID)
        if isinstance(gl, discord.TextChannel):
            await gl.send("📺 Detected **live** on Twitch (offline → live).")

    @poll_twitch.before_loop
    async def before_poll(self):
        await self.bot.wait_until_ready()
        await self._log_bot("🟢 Twitch polling task started.")

async def setup(bot: commands.Bot):
    await bot.add_cog(TwitchCog(bot))
