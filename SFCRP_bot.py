import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
import os
import logging
import sys
from dotenv import load_dotenv


load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------
# Logging Setup
# ------------------------
# Configure logging with UTF-8 encoding for Windows compatibility
file_handler = logging.FileHandler('bot.log', encoding='utf-8')
console_handler = logging.StreamHandler(sys.stdout)
console_handler.stream.reconfigure(encoding='utf-8') if hasattr(console_handler.stream, 'reconfigure') else None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger('discord_bot')

#test change

# ------------------------
# Constants
# ------------------------
GUILD_ID = 1427147442411012149

# Role IDs
ROLE_STAFF_ADMIN = 1427161909349843004
ROLE_STAFF_MODERATOR = 1427161368804589738
ROLE_RP_LOGGER = 1427472685499289670

# Channel IDs
CHANNEL_PROMOTIONS = 1427471492572119170
CHANNEL_INFRACTIONS = 1427471662881837139
CHANNEL_RP_LOGS = 1429695512910757961

# URLs
PROMOTION_BANNER_URL = "https://media.discordapp.net/attachments/1427516887427846204/1432044703905353871/SFCRP_Promo_banner.png?ex=68ff9f0f&is=68fe4d8f&hm=c6fc60cf07e0c8f9a290a374176762b1ec0d6733bbc59758fc931ca7d679143a&=&format=webp&quality=lossless"
INFRACTION_BANNER_URL = "https://media.discordapp.net/attachments/1427516887427846204/1432073959506968759/Infractions.png?ex=68ffba4e&is=68fe68ce&hm=808f9a7fc30d3e1d81ec79eea1e2d6323b4d47cab8773bc9a6c24c43862092d1&=&format=webp&quality=lossless"
ROLEPLAY_BANNER_URL= "https://media.discordapp.net/attachments/1427494059257233449/1432155262566793418/Game_log.png?ex=69000606&is=68feb486&hm=01bb72f8cea2e76f9ef49dd10b80d85ebde94f93228bf0b104da9bb46c82672c&=&format=webp&quality=lossless"
# API Keys
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ------------------------
# Helper Functions
# ------------------------
def has_staff_permission(user: discord.Member) -> bool:
    """Check if user has staff permissions"""
    allowed_roles = [ROLE_STAFF_ADMIN, ROLE_STAFF_MODERATOR]
    return any(role.id in allowed_roles for role in user.roles)

def require_staff_permission():
    """Decorator to check staff permission before executing command"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not has_staff_permission(interaction.user):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

async def send_dm_safe(member: discord.Member, content: str = None, embed: discord.Embed = None) -> bool:
    """
    Safely send a DM to a member. Returns True if successful, False otherwise.
    """
    try:
        if embed:
            await member.send(embed=embed)
        else:
            await member.send(content)
        logger.info(f"DM sent successfully to {member} (ID: {member.id})")
        return True
    except discord.Forbidden:
        logger.warning(f"Cannot DM {member} (ID: {member.id}) - DMs are disabled")
        return False
    except Exception as e:
        logger.error(f"Failed to DM {member} (ID: {member.id}): {e}", exc_info=True)
        return False

@bot.event
async def on_ready():
    """Bot startup event handler"""
    logger.info(f"Logged in as {bot.user}")
    logger.info("Starting command sync process...")
    
    try:
        # Sync commands to the guild
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        logger.info(f"Successfully synced {len(synced)} commands to guild {GUILD_ID}")
        
        # Log all synced commands
        for command in synced:
            logger.info(f"  - /{command.name}")
        
        logger.info("Bot is ready and all commands are synced!")
        
    except Exception as e:
        logger.error(f"Sync error: {e}", exc_info=True)
        logger.error("Bot may not function properly without synced commands!")
        # Don't exit, but make it clear there's an issue


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for all slash commands"""
    # Get command name safely
    command_name = interaction.command.name if interaction.command else "Unknown"
    
    if isinstance(error, app_commands.CheckFailure):
        # Permission errors are already handled by the decorator
        logger.warning(f"Permission check failed for {interaction.user} in command: {command_name}")
        return
    
    if isinstance(error, app_commands.CommandNotFound):
        logger.error(f"Command not found: {command_name}. Bot commands may need to be synced.")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ This command is not available. Please try resyncing bot commands.", ephemeral=True)
        except:
            pass
        return

    # Log the error with full traceback
    logger.error(f"Error in command '{command_name}' by {interaction.user} (ID: {interaction.user.id}): {error}", exc_info=error)

    # Send user-friendly error message
    try:
        if interaction.response.is_done():
            await interaction.followup.send("❌ An error occurred while processing your command. Please try again later.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ An error occurred while processing your command. Please try again later.", ephemeral=True)
    except Exception as e:
        logger.error(f"Failed to send error message to user: {e}", exc_info=True)

# ------------------------
# 📈 Promote Command
# ------------------------


# 🔹 /promote Command
@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="promote", description="Promote a member with notes")
@require_staff_permission()
@app_commands.describe( member="Member to promote", new_rank="New rank/title for the member", reason="Reason for promotion (optional)")
async def promote(interaction: discord.Interaction, member: discord.Member, new_rank: str, reason: str = "N/A"):
    banner_embed = discord.Embed(color=discord.Color.blue())
    banner_embed.set_image(url=PROMOTION_BANNER_URL)

    promo_embed = discord.Embed(title="📈 Staff Promotion",
        description=(f"**{member.mention}** has been promoted to **{new_rank}**!\n\n"
            f"Your commitment and hard work have earned you this role — congratulations!\n\n"
            "----------------------------\n"
            f"**👤 Member:** {member.mention}\n"
            f"**🏅 New Rank:** {new_rank}\n"
            f"🧾 **Reason:** {reason}\n"),
        color=discord.Color.blue())

    # Send DM to promoted member
    dm_embed = discord.Embed(title="🎉 You've been promoted!",
        description=(f"Congratulations {member.mention}!\n\n"
            f"You've been promoted to **{new_rank}**.\n"
            f"Reason: {reason}\n\n"
            "Keep up the great work!"),
        color=discord.Color.green())
    dm_sent = await send_dm_safe(member, embed=dm_embed)

    # Get promotion channel
    promo_channel = interaction.guild.get_channel(CHANNEL_PROMOTIONS)
    if not promo_channel:
        await interaction.response.send_message("❌ Promotion channel not found. Check the channel ID.", ephemeral=True)
        return

    # Send banner and promotion embed
    await promo_channel.send(embed=banner_embed)
    await promo_channel.send(embed=promo_embed)

    # Send confirmation response
    if dm_sent:
        await interaction.response.send_message(f"✅ Promotion for {member.mention} logged in <#{CHANNEL_PROMOTIONS}> and DM sent.", ephemeral=True)
    else:
        await interaction.response.send_message(f"✅ Promotion posted in <#{CHANNEL_PROMOTIONS}>, but I couldn't DM {member.mention}.", ephemeral=True)



# ------------------------
# ⚠️ Infraction Command
# ------------------------
@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="infraction", description="Give a user an infraction")
@require_staff_permission()
@app_commands.describe(
    member="Member to infract",
    reason="Reason for infraction",
    punishment="Type of punishment"
)
@app_commands.choices(punishment=[
    app_commands.Choice(name="Warning", value="Warning"),
    app_commands.Choice(name="Strike", value="Strike"),
    app_commands.Choice(name="Under Investigation", value="Under Investigation"),
    app_commands.Choice(name="Suspension", value="Suspension"),
    app_commands.Choice(name="Demotion", value="Demotion"),
    app_commands.Choice(name="Termination", value="Termination"),
    app_commands.Choice(name="Staff Blacklist", value="Staff Blacklist")
])
async def infraction(interaction: discord.Interaction, member: discord.Member, reason: str, punishment: app_commands.Choice[str]):
    # Banner embed
    banner_embed = discord.Embed(color=discord.Color.blue())
    banner_embed.set_image(url=INFRACTION_BANNER_URL)
    
    # Infraction details embed
    infraction_embed = discord.Embed(
        title="⚠️ Infraction Issued",
        description= "Your account has received an infraction for the following reason(s). If you believe this was a mistake or would like to appeal, please submit an appeal.",
        color=discord.Color.blue()
    )
    infraction_embed.add_field(name="👤 User", value=member.mention, inline=True)
    infraction_embed.add_field(name="📋 Reason", value=reason, inline=True)
    infraction_embed.add_field(name="⚖️ Punishment", value=punishment.value, inline=True)
    infraction_embed.set_footer(text=f"Issued by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

    # Send DM to member
    dm_message = f"You have received an infraction in **{interaction.guild.name}**.\n**Reason:** {reason}\n**Punishment:** {punishment.value}"
    dm_sent = await send_dm_safe(member, content=dm_message)

    # Get infractions channel
    channel = bot.get_channel(CHANNEL_INFRACTIONS)
    if channel is None:
        await interaction.response.send_message("❌ Could not find the infractions log channel. Please check the channel ID.", ephemeral=True)
        return

    # Send banner and infraction embed
    await channel.send(embed=banner_embed)
    await channel.send(embed=infraction_embed)

    # Confirm privately
    if dm_sent:
        await interaction.response.send_message(f"✅ Infraction for {member.mention} has been logged in <#{CHANNEL_INFRACTIONS}> and DM sent.", ephemeral=True)
    else:
        await interaction.response.send_message(f"✅ Infraction logged in <#{CHANNEL_INFRACTIONS}>, but I couldn't DM {member.mention}.", ephemeral=True)



# /say command
@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="say", description="Make the bot say a message (staff only).")
@require_staff_permission()
@app_commands.describe(message="What should the bot say?")
async def say(interaction: discord.Interaction, message: str):
    # Defer to keep command hidden
    await interaction.response.defer(ephemeral=True)

    # Send the bot's message to the same channel
    await interaction.channel.send(message)

    # Confirm success to the command user
    await interaction.followup.send("✅ Message sent!", ephemeral=True)


# ------------------------
# Training
# ------------------------


@bot.tree.command(
    guild=discord.Object(id=GUILD_ID),
    name="stafftraining",
    description="Create a staff training or ride-along announcement."
)
@require_staff_permission()
@app_commands.describe(
    session_type="Choose between Training or Ride Along",
    notes="Add any important notes or instructions"
)
@app_commands.choices(session_type=[
    app_commands.Choice(name="Training", value="Training"),
    app_commands.Choice(name="Ride Along", value="Ride Along")
])
async def stafftraining(interaction: discord.Interaction, session_type: app_commands.Choice[str], notes: str):
    # Channel where message will be sent
    target_channel_id = 1431693846357479636
    target_channel = interaction.guild.get_channel(target_channel_id)

    if not target_channel:
        await interaction.response.send_message("❌ Could not find the target channel.", ephemeral=True)
        return

    # Role to ping
    role_id = 1428228426179018762
    role_mention = f"<@&{role_id}>"

    # Build embed
    embed = discord.Embed(
        title=f"🚔 Staff {session_type.value} Announcement",
        color=discord.Color.blue()
    )
    embed.add_field(name="👮 **Host**", value=interaction.user.mention, inline=False)
    embed.add_field(name="📝 **Type**", value=session_type.value, inline=True)
    embed.add_field(name="🧾 **Notes**", value=notes, inline=False)
    embed.add_field(name="\U0001f517 Server code sftrain", value="", inline=False)
    embed.set_footer(text=f"LAPD {session_type.value} Announcement")

    # Buttons
    class StaffTrainingView(View):
        attendees = set()
        def __init__(self, target_channel):
            super().__init__(timeout=None)
            self.target_channel = target_channel
            join_button = Button(label="Join", style=discord.ButtonStyle.success)
            join_button.callback = self.join_button_haandler
            self.add_item(join_button)
            attendees_button = Button(label="Attendees", style=discord.ButtonStyle.secondary)
            attendees_button.callback = self.attendees_button_handler
            self.add_item(attendees_button)


        async def join_button_haandler(self, interaction: discord.Interaction):
                self.attendees.add(interaction.user.mention) 
                await interaction.response.send_message(f"✅ You joined the training!", ephemeral=True)

        async def attendees_button_handler(self, interaction: discord.Interaction):
            data = ','.join(self.attendees)
            await interaction.response.send_message(f"👋 Attendees: {data}", ephemeral=True)


    view = StaffTrainingView(target_channel)

    # Send to specific channel
    await target_channel.send(content=role_mention, embed=embed, view=view)
    await interaction.response.send_message(f"✅ Sent your {session_type.value.lower()} announcement to <#{target_channel_id}>!", ephemeral=True)

# ------------------------
# ssu
# ------------------------
# Constants
# ------------------------
GUILD_ID = 1427147442411012149
ALLOWED_ROLES = [1427161909349843004, 1427161368804589738]  # Admin & Moderator
ANNOUNCE_CHANNEL_ID = 1427153224330248213
PING_ROLE_ID = 1428247832229318727
SSU_VOTE_GOAL = 5
SESSION_BANNER_URL = "https://media.discordapp.net/attachments/1427494059257233449/1437332565051838556/Sessions.png?ex=6912dbc3&is=69118a43&hm=0691c34703b71062a86e746bce58519edd38983937dfb381f5d0386810218140&=&format=webp&quality=lossless"
training_banner_url= "https://media.discordapp.net/attachments/1373459392241864716/1436403102667505845/Training_sfcrp.png?ex=690f7a22&is=690e28a2&hm=5599508dbce650516a0774017e742f84e0c8127e236e01ef555e4f70ca83103a&=&format=webp&quality=lossless"

# ------------------------
# Decorator to restrict commands to specific staff roles
# ------------------------
def require_specific_staff():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message(
                "⛔ You do not have permission to use this command.", ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)
# ------------------------
# Enhanced Session Management System
# ------------------------

import json
import os

# Constants
GUILD_ID = 1427147442411012149
ALLOWED_ROLES = [1427161909349843004, 1427161368804589738]  # Admin & Moderator
ANNOUNCE_CHANNEL_ID = 1427153224330248213
PING_ROLE_ID = 1428247832229318727
SSU_VOTE_GOAL = 5
LOW_PLAYER_THRESHOLD = 3  # Alert when players drop below this
SESSION_BANNER_URL = "https://media.discordapp.net/attachments/1373459392241864716/1435519241381216268/Sessions.png?ex=690c42f9&is=690af179&hm=5032379abf5a4f35544453428ae2e425632760a9d1c72b950a1c5757c52e3621&=&format=webp&quality=lossless"
training_banner_url = "https://media.discordapp.net/attachments/1373459392241864716/1436403102667505845/Training_sfcrp.png?ex=690f7a22&is=690e28a2&hm=5599508dbce650516a0774017e742f84e0c8127e236e01ef555e4f70ca83103a&=&format=webp&quality=lossless"

# Session data storage
SESSION_DATA_FILE = "session_data.json"

def load_session_data():
    """Load session history from JSON"""
    if os.path.exists(SESSION_DATA_FILE):
        try:
            with open(SESSION_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"sessions": [], "current_session": None}
    return {"sessions": [], "current_session": None}

def save_session_data(data):
    """Save session data to JSON"""
    with open(SESSION_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ------------------------
# Decorator to restrict commands to specific staff roles
# ------------------------
def require_specific_staff():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message(
                "⛔ You do not have permission to use this command.", ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

# ------------------------
# Enhanced Session Management System
# ------------------------
from datetime import datetime, timedelta
import json
import os



# Session data storage
SESSION_DATA_FILE = "session_data.json"

def load_session_data():
    """Load session history from JSON"""
    if os.path.exists(SESSION_DATA_FILE):
        try:
            with open(SESSION_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"sessions": [], "current_session": None}
    return {"sessions": [], "current_session": None}

def save_session_data(data):
    """Save session data to JSON"""
    with open(SESSION_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ------------------------
# Decorator to restrict commands to specific staff roles
# ------------------------
def require_specific_staff():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message(
                "⛔ You do not have permission to use this command.", ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

# 
# ------------------------
# /ssv Command — Session Vote (Enhanced)
# ------------------------
# Replace your /ssv command (around line 548-683) with this fixed version:

@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="ssv", description="Start session vote (SSV)")
@require_specific_staff()
async def ssv(interaction: discord.Interaction):
    channel = interaction.guild.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        return await interaction.response.send_message("❌ Announcement channel not found.", ephemeral=True)

    # Check if session already active
    session_data = load_session_data()
    if session_data.get("current_session"):
        return await interaction.response.send_message("⚠️ A session is already active! Use `/ssd` to end it first.", ephemeral=True)

    embed = discord.Embed(
        title="🟡 Server Standby — Vote for Session Start",
        description=f"Server currently in **standby**.\nPlayers can vote ✅ to start the session.\n\n**Vote Goal:** {SSU_VOTE_GOAL} votes\n**Current Votes:** 0",
        color=discord.Color.gold()
    )
    embed.add_field(name="🎮 Started by", value=interaction.user.mention, inline=True)
    embed.set_image(url=SESSION_BANNER_URL)
    embed.set_footer(text="Server Status: SSV — Waiting for player votes")

    class VoteView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)  # IMPORTANT: No timeout for persistent buttons
            self.yes_votes = set()
            self.voters_info = {}

        @discord.ui.button(label="✅ Vote to Start (0)", style=discord.ButtonStyle.success, custom_id="vote_yes_persistent")
        async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            user_id = interaction.user.id
            
            if user_id in self.yes_votes:
                await interaction.response.send_message("⚠️ You've already voted!", ephemeral=True)
                return
            
            self.yes_votes.add(user_id)
            self.voters_info[user_id] = interaction.user.display_name
            vote_count = len(self.yes_votes)

            # Update button label
            button.label = f"✅ Vote to Start ({vote_count})"
            
            # Update embed
            embed_update = interaction.message.embeds[0]
            embed_update.description = f"Server currently in **standby**.\nPlayers can vote ✅ to start the session.\n\n**Vote Goal:** {SSU_VOTE_GOAL} votes\n**Current Votes:** {vote_count}"
            
            # Add voters list if there are voters
            if vote_count > 0:
                voter_list = ", ".join([f"**{name}**" for name in list(self.voters_info.values())[:10]])
                if vote_count > 10:
                    voter_list += f" and **{vote_count - 10}** more..."
                
                # Update or add voters field
                if len(embed_update.fields) > 1:
                    # Remove old voters field if it exists
                    if len(embed_update.fields) > 2:
                        embed_update.remove_field(2)
                    embed_update.add_field(name="👥 Voters", value=voter_list, inline=False)
                else:
                    embed_update.add_field(name="👥 Voters", value=voter_list, inline=False)

            await interaction.message.edit(embed=embed_update, view=self)

            if vote_count >= SSU_VOTE_GOAL:
                await interaction.response.send_message(
                    f"🎉 Vote goal reached ({vote_count}/{SSU_VOTE_GOAL})! Starting session...", ephemeral=True
                )
                
                # Disable buttons
                for item in self.children:
                    item.disabled = True
                await interaction.message.edit(view=self)
                
                # Start session automatically
                await start_ssu(channel, interaction, vote_initiated=True, voter_count=vote_count)
                self.stop()
                return

            await interaction.response.send_message(
                f"✅ Your vote has been counted! ({vote_count}/{SSU_VOTE_GOAL})", ephemeral=True
            )

        @discord.ui.button(label="❌ Remove Vote", style=discord.ButtonStyle.danger, custom_id="vote_no_persistent")
        async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            user_id = interaction.user.id
            
            if user_id not in self.yes_votes:
                await interaction.response.send_message("⚠️ You haven't voted yet!", ephemeral=True)
                return
            
            self.yes_votes.discard(user_id)
            self.voters_info.pop(user_id, None)
            vote_count = len(self.yes_votes)
            
            # Update button label
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.custom_id == "vote_yes_persistent":
                    item.label = f"✅ Vote to Start ({vote_count})"
            
            # Update embed
            embed_update = interaction.message.embeds[0]
            embed_update.description = f"Server currently in **standby**.\nPlayers can vote ✅ to start the session.\n\n**Vote Goal:** {SSU_VOTE_GOAL} votes\n**Current Votes:** {vote_count}"
            
            # Update voters list
            if vote_count > 0:
                voter_list = ", ".join([f"**{name}**" for name in list(self.voters_info.values())[:10]])
                if vote_count > 10:
                    voter_list += f" and **{vote_count - 10}** more..."
                
                # Update or replace voters field
                if len(embed_update.fields) > 2:
                    embed_update.set_field_at(2, name="👥 Voters", value=voter_list, inline=False)
            else:
                # Remove voters field if no votes
                if len(embed_update.fields) > 2:
                    embed_update.remove_field(2)
            
            await interaction.message.edit(embed=embed_update, view=self)
            await interaction.response.send_message("❌ Vote removed.", ephemeral=True)

        @discord.ui.button(label="📊 View Voters", style=discord.ButtonStyle.secondary, custom_id="view_voters_persistent")
        async def view_voters_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if not self.yes_votes:
                await interaction.response.send_message("📊 No votes yet!", ephemeral=True)
                return
            
            voter_list = "\n".join([f"• **{name}**" for name in self.voters_info.values()])
            
            embed = discord.Embed(
                title=f"📊 Current Voters ({len(self.yes_votes)}/{SSU_VOTE_GOAL})",
                description=voter_list,
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    view = VoteView()
    
    # Send the message
    await channel.send(f"<@&{PING_ROLE_ID}>", embed=embed, view=view)
    await interaction.response.send_message("🟡 Session vote started! Players can now vote.", ephemeral=True)
# ------------------------
# /ssu Command — Start Session (Enhanced)
# ------------------------
@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="ssu", description="Start Session (SSU)")
@require_specific_staff()
async def ssu(interaction: discord.Interaction):
    channel = interaction.guild.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        return await interaction.response.send_message("❌ Announcement channel not found.", ephemeral=True)

    # Check if session already active
    session_data = load_session_data()
    if session_data.get("current_session"):
        return await interaction.response.send_message("⚠️ A session is already active! Use `/ssd` to end it first.", ephemeral=True)

    await start_ssu(channel, interaction)
    await interaction.response.send_message("🟢 Session started successfully!", ephemeral=True)
# ------------------------
# /ssd Command — End Session (Enhanced)
# ------------------------
@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="ssd", description="End Session (SSD)")
@require_specific_staff()
async def ssd(interaction: discord.Interaction):
    channel = interaction.guild.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        return await interaction.response.send_message("❌ Announcement channel not found.", ephemeral=True)

    session_data = load_session_data()
    current_session = session_data.get("current_session")
    
    if not current_session:
        return await interaction.response.send_message("⚠️ No active session to end!", ephemeral=True)

    # Calculate session duration
    start_time = datetime.fromisoformat(current_session["start_time"])
    end_time = datetime.utcnow()
    duration = end_time - start_time
    
    
    embed = discord.Embed(
        title="🔴 Server Shutdown — Session Ended",
        description="The server session has now ended.\nThank you for participating!",
        color=discord.Color.red()
    )
    embed.add_field(name="🎮 Started by", value=current_session["host_name"], inline=True)
    embed.add_field(name="🛑 Ended by", value=interaction.user.mention, inline=True)
    embed.set_image(url="https://media.discordapp.net/attachments/1427494059257233449/1437332565051838556/Sessions.png?ex=6912dbc3&is=69118a43&hm=0691c34703b71062a86e746bce58519edd38983937dfb381f5d0386810218140&=&format=webp&quality=lossless")
    embed.set_footer(text="Server Status: SSD — Thanks for playing!")

    await channel.send(embed=embed)

    # Save session to history
    current_session["end_time"] = end_time.isoformat()
    current_session["ended_by_id"] = str(interaction.user.id)
    current_session["ended_by_name"] = interaction.user.display_name
    current_session["duration_minutes"] = int(duration.total_seconds() // 60)
    
    session_data["sessions"].append(current_session)
    session_data["current_session"] = None
    save_session_data(session_data)

    await interaction.response.send_message("🔴 Session ended and logged!", ephemeral=True)

# 

# ------------------------
# /sessionstatus Command — View Current Session Info
# ------------------------
@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="sessionstatus", description="View current session information")
async def sessionstatus(interaction: discord.Interaction):
    session_data = load_session_data()
    current_session = session_data.get("current_session")
    
    if not current_session:
        return await interaction.response.send_message("⚠️ No active session running!", ephemeral=True)

    start_time = datetime.fromisoformat(current_session["start_time"])
    duration = datetime.utcnow() - start_time
    hours = int(duration.total_seconds() // 3600)
    minutes = int((duration.total_seconds() % 3600) // 60)

    embed = discord.Embed(
        title="📊 Current Session Status",
        description="Active session information:",
        color=discord.Color.green()
    )
    embed.add_field(name="🎮 Host", value=current_session["host_name"], inline=True)
    embed.add_field(name="👥 Current Players", value=f"**{current_session.get('current_players', 0)}**", inline=True)
    embed.add_field(name="📈 Peak Players", value=f"**{current_session.get('peak_players', 0)}**", inline=True)
    embed.add_field(name="⏱️ Duration", value=f"{hours}h {minutes}m", inline=True)
    embed.add_field(name="📅 Started", value=f"<t:{int(start_time.timestamp())}:R>", inline=True)
    embed.add_field(name="📊 Updates", value=f"{current_session.get('player_updates', 0)}", inline=True)
    
    if current_session.get("vote_initiated"):
        embed.add_field(name="🗳️ Started By", value="Community Vote", inline=True)
    
    embed.set_footer(text="Session is currently active")
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed)

# ------------------------
# /sessionhistory Command — View Past Sessions
# ------------------------
@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="sessionhistory", description="View recent session history")
async def sessionhistory(interaction: discord.Interaction):
    session_data = load_session_data()
    sessions = session_data.get("sessions", [])
    
    if not sessions:
        return await interaction.response.send_message("📊 No session history yet!", ephemeral=True)

    # Get last 5 sessions
    recent_sessions = sorted(sessions, key=lambda x: x["start_time"], reverse=True)[:5]

    embed = discord.Embed(
        title="📜 Recent Session History",
        description=f"Showing last {len(recent_sessions)} sessions:",
        color=discord.Color.blue()
    )

    for idx, session in enumerate(recent_sessions, 1):
        start = datetime.fromisoformat(session["start_time"])
        duration_min = session.get("duration_minutes", 0)
        hours = duration_min // 60
        minutes = duration_min % 60
        
        session_info = (
            f"**Host:** {session['host_name']}\n"
            f"**Duration:** {hours}h {minutes}m\n"
            f"**Peak Players:** {session.get('peak_players', 0)}\n"
            f"**Date:** {start.strftime('%b %d, %Y at %I:%M %p')}"
        )
        
        embed.add_field(
            name=f"Session #{len(sessions) - sessions.index(session)}",
            value=session_info,
            inline=False
        )

    embed.set_footer(text=f"Total sessions: {len(sessions)}")
    await interaction.response.send_message(embed=embed)

# ------------------------
# /sessionstats Command — View Session Statistics
# ------------------------
@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="sessionstats", description="View overall session statistics")
async def sessionstats(interaction: discord.Interaction):
    session_data = load_session_data()
    sessions = session_data.get("sessions", [])
    
    if not sessions:
        return await interaction.response.send_message("📊 No session data yet!", ephemeral=True)

    # Calculate statistics
    total_sessions = len(sessions)
    total_minutes = sum(s.get("duration_minutes", 0) for s in sessions)
    avg_duration = total_minutes / total_sessions if total_sessions > 0 else 0
    max_players = max((s.get("peak_players", 0) for s in sessions), default=0)
    avg_players = sum(s.get("peak_players", 0) for s in sessions) / total_sessions if total_sessions > 0 else 0

    # Most active host
    host_counter = {}
    for session in sessions:
        host = session["host_name"]
        host_counter[host] = host_counter.get(host, 0) + 1
    
    most_active_host = max(host_counter.items(), key=lambda x: x[1]) if host_counter else ("N/A", 0)

    embed = discord.Embed(
        title="📊 Session Statistics",
        description="All-time server statistics:",
        color=discord.Color.gold()
    )
    embed.add_field(name="📈 Total Sessions", value=f"**{total_sessions}**", inline=True)
    embed.add_field(name="⏱️ Total Playtime", value=f"**{total_minutes // 60}h {total_minutes % 60}m**", inline=True)
    embed.add_field(name="🏆 Most Active Host", value=f"**{most_active_host[0]}**\n({most_active_host[1]} sessions)", inline=True)
    
    embed.set_footer(text="Statistics since bot deployment")
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed)

# ------------------------
# Helper function to start SSU (Enhanced)
# ------------------------
async def start_ssu(channel, interaction, vote_initiated=False, voter_count=0):
    session_data = load_session_data()
    
    start_time = datetime.utcnow()
    
    # Create new session
   # Replace your start_ssu function (around line 793-831) with this:

async def start_ssu(channel, interaction, vote_initiated=False, voter_count=0):
    session_data = load_session_data()
    
    start_time = datetime.utcnow()
    
    # Create new session
    new_session = {
        "id": len(session_data["sessions"]) + 1,
        "host_id": str(interaction.user.id),
        "host_name": interaction.user.display_name,
        "start_time": start_time.isoformat(),
        "current_players": 0,
        "peak_players": 0,
        "player_updates": 0,
        "player_history": [],
        "vote_initiated": vote_initiated,
        "voter_count": voter_count
    }
    
    session_data["current_session"] = new_session
    save_session_data(session_data)
    
    embed = discord.Embed(
        title="🟢 Server Start Up — Session Open",
        description="The server is now **open for RP**! Join in and have fun!",
        color=discord.Color.green()
    )
    embed.add_field(name="🎮 Started by", value=interaction.user.mention, inline=True)
    
    if vote_initiated:
        embed.add_field(name="🗳️ Vote Count", value=f"{voter_count} votes", inline=True)
        embed.add_field(name="Server Code", value="SSCRPP")
        embed.set_footer(text="Server Status: SSU — Started by community vote!")
    else:
        embed.add_field(name="Server Code", value="SSCRPP")
        embed.set_footer(text="Server Status: SSU — Join now!")
    embed.set_image(url="https://media.discordapp.net/attachments/1373459392241864716/1435519241381216268/Sessions.png?ex=69162639&is=6914d4b9&hm=2fe27dfccf414d840a81705fce6689454d1c7890984fcabba6874cd1a8e7634c&=&format=webp&quality=lossless")
    embed.timestamp = start_time
    
    await channel.send(f"<@&{PING_ROLE_ID}>", embed=embed)
# ------------------------
# ------------------------
# /trainingresult Command — Log Training Results + DM Trainee
# ------------------------
TRAINING_RESULTS_CHANNEL_ID = 1428231048575058030  # Change if needed

@bot.tree.command(
    guild=discord.Object(id=GUILD_ID),
    name="trainingresult",
    description="Post a trainee's pass/fail results and DM them automatically"
)
@require_specific_staff()
@app_commands.describe(
    trainee="The trainee being evaluated",
    result="Did they pass or fail?",
    notes="Any training notes or feedback"
)
@app_commands.choices(
    result=[
        app_commands.Choice(name="✅ Pass", value="pass"),
        app_commands.Choice(name="❌ Fail", value="fail"),
    ]
)
async def trainingresult(interaction: discord.Interaction, trainee: discord.Member, result: app_commands.Choice[str], notes: str):
    channel = interaction.guild.get_channel(TRAINING_RESULTS_CHANNEL_ID)
    if not channel:
        return await interaction.response.send_message("❌ Training results channel not found.", ephemeral=True)

    if result.value == "pass":
        color = discord.Color.green()
        result_text = "✅ **Passed**"
        dm_message = (
            f"🎉 Congratulations {trainee.mention}!\n\n"
            f"You have **passed** your training session.\n\n"
            f"**Notes:** {notes}\n\n"
        )
    else:
        color = discord.Color.red()
        result_text = "❌ **Failed**"
        dm_message = (
            f"⚠️ Hello {trainee.mention},\n\n"
            f"Unfortunately, you did **not pass** your training this time.\n\n"
            f"**Notes:** {notes}\n\n"
        )

    # Create embed
    embed = discord.Embed(
        title="📋 Training Results",
        description=f"**Trainee:** {trainee.mention}\n**Result:** {result_text}",
        color=color
    )
    embed.add_field(name="Instructor", value=interaction.user.mention, inline=True)
    embed.add_field(name="Notes", value=notes if notes else "No additional notes provided.", inline=False)
    embed.set_image(url="")
    embed.set_footer(text="Training Completion Record")

    # Send to training results channel
    await channel.send(embed=embed)

    # Try to DM trainee safely
    try:
        await trainee.send(dm_message)
    except discord.Forbidden:
        await interaction.response.send_message(
            f"✅ Result posted, but I couldn't DM {trainee.mention} (DMs off).",
            ephemeral=True
        )
        return

    # Confirm success to staff
    await interaction.response.send_message(
        f"✅ Training result posted and DM sent to {trainee.mention}.",
        ephemeral=True
    )
# Welcome/Leave messages
@bot.event
async def on_member_join(member):
    # Send welcome message with server rules
    pass
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
import os
from datetime import datetime
from collections import Counter, defaultdict
import re

# ------------------------
# RP Data Storage Setup
# ------------------------
RP_LOG_FILE = "rp_logs.json"

def load_rp_logs():
    """Load RP logs from JSON file"""
    if os.path.exists(RP_LOG_FILE):
        try:
            with open(RP_LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_rp_logs(logs):
    """Save RP logs to JSON file"""
    with open(RP_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

# ------------------------
# Enhanced /logrp Command with Database Storage
# ------------------------
CHANNEL_RP_LOGS = 1429695512910757961  # Your RP logs channel
ROLEPLAY_BANNER_URL = "https://media.discordapp.net/attachments/1427494059257233449/1432155262566793418/Game_log.png?ex=69000606&is=68feb486&hm=01bb72f8cea2e76f9ef49dd10b80d85ebde94f93228bf0b104da9bb46c82672c&=&format=webp&quality=lossless"

@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="logrp", description="Log a roleplay event")
@app_commands.describe(
    location="Where did the RP take place?",
    description="Brief description of what happened.",
    participants="Who was involved in the RP?"
)
async def logrp(interaction: discord.Interaction, location: str, description: str, participants: str):
    log_channel = interaction.guild.get_channel(CHANNEL_RP_LOGS)
    if not log_channel:
        await interaction.response.send_message("⚠️ Log channel not found. Please contact an admin.", ephemeral=True)
        return
    
    # Create embed for display
    embed = discord.Embed(title="📘 Roleplay Log", color=discord.Color.dark_blue())
    embed.add_field(name="📍 Location", value=location, inline=True)
    embed.add_field(name="📝 Roleplay", value=description, inline=False)
    embed.add_field(name="👥 Participants", value=participants, inline=False)
    embed.set_footer(text=f"Logged by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()
    
    # Send to channel
    await log_channel.send(embed=embed)
    
    # Save to database
    logs = load_rp_logs()
    
    # Extract participant mentions/names for better tracking
    participant_list = re.findall(r'<@!?(\d+)>|([A-Za-z0-9_]+)', participants)
    participant_ids = []
    participant_names = []
    
    for mention_id, name in participant_list:
        if mention_id:
            participant_ids.append(mention_id)
            try:
                member = await interaction.guild.fetch_member(int(mention_id))
                participant_names.append(member.display_name)
            except:
                participant_names.append(f"User_{mention_id}")
        elif name:
            participant_names.append(name)
    
    rp_entry = {
        "id": len(logs) + 1,
        "logger_id": str(interaction.user.id),
        "logger_name": interaction.user.display_name,
        "location": location.lower(),
        "description": description,
        "participants": participants,
        "participant_ids": participant_ids,
        "participant_names": participant_names,
        "timestamp": datetime.utcnow().isoformat(),
        "guild_id": str(interaction.guild_id)
    }
    
    logs.append(rp_entry)
    save_rp_logs(logs)
    
    await interaction.response.send_message(f"✅ Roleplay log #{rp_entry['id']} posted successfully!", ephemeral=True)



# ------------------------
# /rplog Command - View Specific RP Log by ID
# ------------------------
@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="rplog", description="View a specific RP log by ID")
@app_commands.describe(log_id="The ID number of the RP log")
async def rplog(interaction: discord.Interaction, log_id: int):
    logs = load_rp_logs()
    
    # Find the log
    log = next((l for l in logs if l["id"] == log_id and l.get("guild_id") == str(interaction.guild_id)), None)
    
    if not log:
        await interaction.response.send_message(f"❌ RP log #{log_id} not found!", ephemeral=True)
        return
    
    # Create detailed embed
    
    embed = discord.Embed(
        title=f"📘 RP Log #{log['id']}",
        color=discord.Color.dark_blue(),
    )
    embed.add_field(name="📍 Location", value=log["location"].title(), inline=True)
    embed.add_field(name="👤 Logged By", value=log["logger_name"], inline=True)
    embed.add_field(name="📝 Description", value=log["description"], inline=False)
    embed.add_field(name="👥 Participants", value=log["participants"], inline=False)
    
    await interaction.response.send_message(embed=embed)

# ------------------------
# /rpleaderboard Command - Top RP Contributors
# ------------------------
@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="rpleaderboard", description="View top RP contributors")
@app_commands.describe(
    category="What to rank by"
)
@app_commands.choices(category=[
    app_commands.Choice(name="Most RPs Logged", value="logged"),
    app_commands.Choice(name="Most RPs Participated", value="participated"),
    app_commands.Choice(name="Most Active Locations", value="locations")
])
async def rpleaderboard(interaction: discord.Interaction, category: app_commands.Choice[str] = None):
    logs = load_rp_logs()
    
    # Filter logs for this guild
    guild_logs = [log for log in logs if log.get("guild_id") == str(interaction.guild_id)]
    
    if not guild_logs:
        await interaction.response.send_message("📊 No RP logs found yet! Start logging with `/logrp`", ephemeral=True)
        return
    
    category_type = category.value if category else "logged"
    
    embed = discord.Embed(
        title="🏆 RP Leaderboard",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    
    if category_type == "logged":
        # Count RPs logged by each user
        logger_counter = Counter()
        for log in guild_logs:
            logger_counter[log["logger_id"]] += 1
        
        top_loggers = logger_counter.most_common(10)
        leaderboard_text = ""
        
        for idx, (user_id, count) in enumerate(top_loggers, 1):
            try:
                member = await interaction.guild.fetch_member(int(user_id))
                medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"**{idx}.**"
                leaderboard_text += f"{medal} {member.mention} - **{count}** RPs logged\n"
            except:
                pass
        
        embed.description = "Top users who have logged the most RPs"
        embed.add_field(name="📝 Most RPs Logged", value=leaderboard_text or "No data", inline=False)
    
    elif category_type == "participated":
        # Count participations
        participation_counter = Counter()
        for log in guild_logs:
            for pid in log["participant_ids"]:
                participation_counter[pid] += 1
        
        top_participants = participation_counter.most_common(10)
        leaderboard_text = ""
        
        for idx, (user_id, count) in enumerate(top_participants, 1):
            try:
                member = await interaction.guild.fetch_member(int(user_id))
                medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"**{idx}.**"
                leaderboard_text += f"{medal} {member.mention} - **{count}** RPs\n"
            except:
                pass
        
        embed.description = "Top users who have participated in the most RPs"
        embed.add_field(name="👥 Most Active RPers", value=leaderboard_text or "No data", inline=False)
    
    elif category_type == "locations":
        # Count most popular locations
        location_counter = Counter()
        for log in guild_logs:
            location_counter[log["location"]] += 1
        
        top_locations = location_counter.most_common(10)
        leaderboard_text = ""
        
        for idx, (location, count) in enumerate(top_locations, 1):
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"**{idx}.**"
            leaderboard_text += f"{medal} **{location.title()}** - **{count}** RPs\n"
        
        embed.description = "Most popular RP locations"
        embed.add_field(name="📍 Top Locations", value=leaderboard_text or "No data", inline=False)
    
    embed.set_footer(text=f"Total RPs in server: {len(guild_logs)}")
    await interaction.response.send_message(embed=embed)
# Add this command anywhere in your bot code (after the helper functions, before bot.run())


# BONUS: Advanced version with channel selection and more options
@bot.tree.command(
    guild=discord.Object(id=GUILD_ID),
    name="affiliatepost",
    description="Post a custom affiliate embed with advanced options"
)
@require_staff_permission()
@app_commands.describe(
    title="The title of the affiliate embed",
    description="The description/text content of the embed",
    image_url="Optional: Main image URL (leave empty for no image)",
    thumbnail_url="Optional: Small thumbnail image in top-right corner",
    color="Optional: Hex code (#FF5733) or color name (blue, green, red, gold, purple)",
    footer_text="Optional: Custom footer text",
    author_name="Optional: Author name at the top of the embed",
    url="Optional: URL that the title links to"
)
async def affiliatepost(
    interaction: discord.Interaction,
    title: str,
    description: str,
    image_url: str = None,
    thumbnail_url: str = None,
    color: str = "blue",
    footer_text: str = None,
    author_name: str = None,
    url: str = None
):
    """
    Advanced affiliate embed with more customization options
    Posts only to the designated affiliate channel
    """
    
    # Get the affiliate channel (same restricted channel)
    affiliate_channel = interaction.guild.get_channel(1427152315902591137)
    if not affiliate_channel:
        await interaction.response.send_message(
            "❌ Affiliate channel not found! Please contact an administrator.",
            ephemeral=True
        )
        return
    
    # Parse color - accepts hex codes or color names
    color_map = {
        "blue": discord.Color.blue(),
        "green": discord.Color.green(),
        "red": discord.Color.red(),
        "gold": discord.Color.gold(),
        "purple": discord.Color.purple(),
        "orange": discord.Color.orange(),
        "teal": discord.Color.teal(),
        "magenta": discord.Color.magenta(),
        "dark_blue": discord.Color.dark_blue(),
        "dark_green": discord.Color.dark_green(),
        "dark_red": discord.Color.dark_red(),
        "black": discord.Color.from_rgb(0, 0, 0),
        "white": discord.Color.from_rgb(255, 255, 255)
    }
    
    embed_color = color_map.get(color.lower())
    
    if not embed_color:
        try:
            hex_color = color.strip()
            if hex_color.startswith('#'):
                hex_color = hex_color[1:]
            
            if len(hex_color) == 3:
                hex_color = ''.join([c*2 for c in hex_color])
            
            if len(hex_color) == 6:
                embed_color = discord.Color(int(hex_color, 16))
            else:
                raise ValueError("Invalid hex length")
                
        except (ValueError, TypeError):
            await interaction.response.send_message(
                f"⚠️ Invalid color: `{color}`\n"
                f"Use a color name or hex code (#FF5733)",
                ephemeral=True
            )
            return
    
    # Validate URLs if provided
    if image_url and not (image_url.startswith('http://') or image_url.startswith('https://')):
        await interaction.response.send_message(
            "❌ Invalid image URL! Must start with `http://` or `https://`",
            ephemeral=True
        )
        return
    
    if thumbnail_url and not (thumbnail_url.startswith('http://') or thumbnail_url.startswith('https://')):
        await interaction.response.send_message(
            "❌ Invalid thumbnail URL! Must start with `http://` or `https://`",
            ephemeral=True
        )
        return
    
    if url and not (url.startswith('http://') or url.startswith('https://')):
        await interaction.response.send_message(
            "❌ Invalid title URL! Must start with `http://` or `https://`",
            ephemeral=True
        )
        return
    
    # Create the affiliate embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=embed_color,
        url=url if url else None
    )
    
    # Set author if provided
    if author_name:
        embed.set_author(
            name=author_name,
            icon_url=interaction.user.display_avatar.url
        )
    
    # Only set images if URLs were provided
    if image_url:
        embed.set_image(url=image_url)
    
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    
    # Set footer
    if footer_text:
        embed.set_footer(
            text=footer_text,
            icon_url=interaction.user.display_avatar.url
        )
    else:
        embed.set_footer(
            text=f"Posted by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
    
    embed.timestamp = discord.utils.utcnow()
    
    # Send to the affiliate channel only
    await affiliate_channel.send(embed=embed)
    
    # Confirm to user
    await interaction.response.send_message(
        f"✅ Affiliate embed posted successfully in <#{1427152315902591137}>!",
        ephemeral=True
    )
# --------------------------
# Run Bot
# --------------------------
import asyncio

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print("Slash commands synced.")
    except Exception as e:
        print(f"Slash sync error: {e}")

    print(f"Logged in as {bot.user} ({bot.user.id})")

async def load_cogs():
    await bot.load_extension("status")  # loads status.py using setup()

asyncio.run(load_cogs())

bot.run(BOT_TOKEN)
