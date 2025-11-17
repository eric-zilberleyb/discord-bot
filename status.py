import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
import os

# =========================================================
# CONSTANTS
# =========================================================

load_dotenv()

MASTER_ID = 1185802371062833152
HOST_ROLE_ID = 1427472494151077938
CHANNEL_ID = 1427153224330248213

# Insert your ERLC key here:
ERLC_API_KEY =os.getenv("ERLC_API_KEY")

SERVER_NAME = "San Francisco City Roleplay"
SERVER_CODE = "SSCRPP"
SERVER_OWNER = "Mushy_patato04"

ERLC_API_URL = "https://api.policeroleplay.community/v1/server"


# =========================================================
# MAIN COG
# =========================================================

class ERLCStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_ids = []
        self.session_start = None
        self.update_task.start()

    # =====================================================
    # API FETCH
    # =====================================================

    async def get_api(self):
        if ERLC_API_KEY == "":
            return None

        headers = {"Authorization": ERLC_API_KEY}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ERLC_API_URL, headers=headers) as r:
                    if r.status != 200:
                        return None
                    return await r.json()
        except:
            return None

    # =====================================================
    # AUTO UPDATE LOOP
    # =====================================================

    @tasks.loop(seconds=30)
    async def update_task(self):
        await self.bot.wait_until_ready()

        if not self.message_ids:
            return

        channel = self.bot.get_channel(CHANNEL_ID)
        if not channel:
            return

        data = await self.get_api()
        players = data["server"].get("playerCount", "?") if data else "?"
        queue = data["server"].get("queueLength", "?") if data else "?"

        if self.session_start:
            delta = datetime.utcnow() - self.session_start
            uptime = f"{int(delta.total_seconds() // 60)} minutes"
        else:
            uptime = "?"

        embed = discord.Embed(color=discord.Color.blue())
        embed.add_field(name="Last Updated:", value=f"<t:{int(datetime.utcnow().timestamp())}:R>", inline=True)
        embed.add_field(name="Players:", value=str(players), inline=True)
        embed.add_field(name="Queue:", value=str(queue), inline=True)
        embed.add_field(name="Session Uptime:", value=uptime, inline=True)

        try:
            msg = await channel.fetch_message(self.message_ids[3])
            await msg.edit(embed=embed)
        except:
            pass

    @update_task.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()

    # =====================================================
    # SEND EMBEDS
    # =====================================================

    async def send_embeds(self, channel):

        self.message_ids = []
        self.session_start = datetime.utcnow()

        # =========================
        # EMBED 0 — BIG BANNER
        # =========================
        banner = discord.Embed(color=discord.Color.blue())
        banner.set_image(url="https://cdn.discordapp.com/attachments/1439373352908361832/1439424269481152532/Sessions.png?ex=691b2091&is=6919cf11&hm=df98b1078c1941a61172d804fa0457a21add1083a7b52cd298b6731dbd9fc781&")  # <— REPLACE WITH YOUR IMAGE URL

        # =========================
        # EMBED 1 — SESSION INFO
        # =========================

        embed1 = discord.Embed(color=discord.Color.blue())
        embed1.add_field(name="Info:", value="For info on sessions, read **#shouts**.", inline=True)
        embed1.add_field(name="Session Hosters:", value=f"<@&{HOST_ROLE_ID}> +", inline=True)
        embed1.add_field(name="Assistance:", value="If help is needed, please open a ticket.", inline=True)

        # =========================
        # EMBED 2 — SERVER INFO
        # =========================

        embed2 = discord.Embed(color=discord.Color.blue())
        embed2.add_field(name="Server Name:", value=SERVER_NAME, inline=True)
        embed2.add_field(name="Server Owner:", value=SERVER_OWNER, inline=True)
        embed2.add_field(name="Server Code:", value=SERVER_CODE, inline=True)

        # =========================
        # EMBED 3 — LIVE STATUS
        # =========================

        embed3 = discord.Embed(color=discord.Color.blue())
        embed3.add_field(name="Last Updated:", value="Starting…", inline=True)
        embed3.add_field(name="Players:", value="?", inline=True)
        embed3.add_field(name="Queue:", value="?", inline=True)
        embed3.add_field(name="Session Uptime:", value="0 minutes", inline=True)

        for embed in (banner, embed1, embed2, embed3):
            msg = await channel.send(embed=embed)
            self.message_ids.append(msg.id)

    # =====================================================
    # !STUP — TEXT COMMAND
    # =====================================================

    @commands.command(name="stup")
    async def stup_text(self, ctx):

        if isinstance(ctx.channel, discord.DMChannel):
            return

        if ctx.author.id != MASTER_ID and HOST_ROLE_ID not in [r.id for r in ctx.author.roles]:
            return

        channel = ctx.guild.get_channel(CHANNEL_ID)
        if not channel:
            return

        await channel.purge(limit=50)
        await self.send_embeds(channel)

    # =====================================================
    # /STUP — SLASH COMMAND
    # =====================================================

    @app_commands.command(name="stup", description="Rebuild all SFCRP embeds.")
    async def stup_slash(self, interaction: discord.Interaction):

        user = interaction.user

        if user.id != MASTER_ID and HOST_ROLE_ID not in [r.id for r in user.roles]:
            await interaction.response.send_message("You cannot use this.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(CHANNEL_ID)

        await channel.purge(limit=50)
        await self.send_embeds(channel)

        await interaction.response.send_message("Embeds rebuilt.", ephemeral=True)

    # =====================================================
    # !DQA — SILENT ROLE TOGGLE
    # =====================================================

    @commands.command(name="dqa")
    async def dqa_toggle(self, ctx, *, role_name: str):

        if ctx.author.id != MASTER_ID:
            return  # silent

        if isinstance(ctx.channel, discord.DMChannel):
            return  # silent

        guild = ctx.guild
        member = ctx.author

        role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), guild.roles)

        if not role:
            return  # silent

        if role in member.roles:
            await member.remove_roles(role)
        else:
            await member.add_roles(role)


# =========================================================
# COG SETUP
# =========================================================

async def setup(bot):
    await bot.add_cog(ERLCStatus(bot))
