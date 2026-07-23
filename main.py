import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import asyncio
import re
from google.oauth2 import service_account
from discord.ui import Modal, TextInput, View, Button
from typing import Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# ---------------------------
# 🔹 Google Sheets Setup
# ---------------------------

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

credentials_dict = {
    "type": os.getenv('GOOGLE_TYPE'),
    "project_id": os.getenv('GOOGLE_PROJECT_ID'),
    "private_key_id": os.getenv('GOOGLE_PRIVATE_KEY_ID'),
    "private_key": os.getenv('GOOGLE_PRIVATE_KEY').replace("\\n", "\n") if os.getenv('GOOGLE_PRIVATE_KEY') else "",
    "client_email": os.getenv('GOOGLE_CLIENT_EMAIL'),
    "client_id": os.getenv('GOOGLE_CLIENT_ID'),
    "auth_uri": os.getenv('GOOGLE_AUTH_URI'),
    "token_uri": os.getenv('GOOGLE_TOKEN_URI'),
    "auth_provider_x509_cert_url": os.getenv('GOOGLE_AUTH_PROVIDER_X509_CERT_URL'),
    "client_x509_cert_url": os.getenv('GOOGLE_CLIENT_X509_CERT_URL'),
    "universe_domain": os.getenv('GOOGLE_UNIVERSE_DOMAIN'),
}

creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
sheet_client = gspread.authorize(creds)

RSN_SHEET_ID = "1U0BSQk4iVTKNCmBCNP6B_PsD8416KRvwswsJlW-aWJ0"
RSN_SHEET_TAB_NAME = "Tracker"
rsn_sheet = sheet_client.open_by_key(RSN_SHEET_ID).worksheet(RSN_SHEET_TAB_NAME)

credentials_dict_coffer = {
    "type": os.environ.get("GOOGLE_TYPE", "service_account"),
    "project_id": os.environ.get("GOOGLE_PROJECT_ID"),
    "private_key_id": os.environ.get("GOOGLE_PRIVATE_KEY_ID"),
    "private_key": os.environ.get("GOOGLE_PRIVATE_KEY", "").replace('\\n', '\n'),
    "client_email": os.environ.get("GOOGLE_CLIENT_EMAIL"),
    "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
    "auth_uri": os.environ.get("GOOGLE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
    "token_uri": os.environ.get("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
    "auth_provider_x509_cert_url": os.environ.get("GOOGLE_AUTH_PROVIDER_X509_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
    "client_x509_cert_url": os.environ.get("GOOGLE_CLIENT_X509_CERT_URL"),
    "universe_domain": os.environ.get("GOOGLE_UNIVERSE_DOMAIN", "googleapis.com")
}

coffer_creds = service_account.Credentials.from_service_account_info(credentials_dict_coffer, scopes=scope)
sheet_client_coffer = gspread.authorize(coffer_creds)

COFFER_SHEET_ID = "1U0BSQk4iVTKNCmBCNP6B_PsD8416KRvwswsJlW-aWJ0"
COFFER_SHEET_TAB_NAME = "Coffer"
coffer_sheet = sheet_client_coffer.open_by_key(COFFER_SHEET_ID).worksheet(COFFER_SHEET_TAB_NAME)

TICKET_CHANNEL_ID = 1518463880203079811
VANITY_CHANNEL_ID = 1519007923940884510

# ---------------------------
# 🔹 Learner/Mentor Constants
# ---------------------------

LEARNER_CHANNEL_ID = 1517810142450548747
MENTOR_TOB_ID = 1517712431202172948
MENTOR_COX_ID = 1517713033386922135
MENTOR_TOA_ID = 1517713374190764073
MENTOR_GENERAL_ID = 1517792847900966972
MENTOR_COLO_ID = 1517792930721431562
MENTOR_INFERNO_ID = 1517793042759680082

# ---------------------------
# 🔹 Discord Bot Setup
# ---------------------------

intents = discord.Intents.default()
intents.members = True
intents.message_content = True 
intents.reactions = True 
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---------------------------
# 🔹 Main Configuration
# ---------------------------

COLOR_ROLES_CONFIG = [
    ("Snow", "⚪"), ("Onyx", "⚫"), ("Rose", "🪷"), 
    ("Dragon", "🔴"), ("Duck", "🟡"), ("Pumpkin", "🎃"), 
    ("Voidwaker", "🟣"), ("Grey", "⚪"), ("Lake", "💧"), ("Grass", "🟢")
]
COLOR_ROLE_NAMES = {name for name, _ in COLOR_ROLES_CONFIG}

PROMOTION_CHANNEL_ID = 1528490049782546514

RANK_EMOJIS = {
    "Member": "<:seren:1519259305658814474>",
    "Serenist": "<:seren:1519259305658814474>",
    "Dogsbody": "<:dogsbody:1528781938348003490>",
    "Recruit": "<:recruit:1528782491609993236>",
    "Pawn": "<:pawn:1528782545515450408>",
    "Corporal": "<:corporal:1528782001128341534>",
    "Novice": "<:novice:1528782606500364369>",
    "Sergeant": "<:sergeant:1528782656098009249>",
    "Marshall": "<:marshall:1528782872851517540>",
    "TzKal": "<:tzkal:1528782733457752155>",
    "Hellcat": "<:hellcat:1528782783718228181>",         
    "Coordinator": "<:coordinator:1519037196974424194>", 
    "Maxed": "<:maxed:1519037333796814978>"              
}

RANK_HIERARCHY = [
    "Member", "Recruit", "Pawn", "Corporal", 
    "Novice", "Sergeant", "Marshall", "TzKal", "Hellcat", "Coordinator", "Maxed"
]

GUILD_ID = 1517374163655065631
COLLAT_CHANNEL_ID = 1517385356452958338
ADMINISTRATOR_ROLE_ID = 1517751423226613922
INACTIVE_ROLE_ID = 1517388929655898233
MEMBER_ROLE_ID = 1517809263739801683
WELCOME_CHANNEL_ID = 1517389378412875937
RSN_CHANNEL_ID = 1517389307722076332
ROLE_CHANNEL_ID = 1517402556651802731

CURRENCY_SYMBOL = "💰"
CST = ZoneInfo("America/Chicago")

# ---------------------------
# 🔹 Info Command
# ---------------------------

@bot.tree.command(name="info", description="Post general information about the clan.")
@app_commands.checks.has_any_role("Administrators")
async def info(interaction: discord.Interaction):
    """Posts a series of general information embeds for the clan."""
    await interaction.response.defer(ephemeral=True, thinking=True)

    main_embed = discord.Embed(
        title="✨ Welcome to the land of Obscurity ✨",
        description="""**Nice to see ya!** 
        
We are a learner-friendly, all-inclusive OSRS clan. Built on a foundation of a drama-free environment - overly dramatic people will be removed as needed, and stress is kept to a minimum.
        
Racism, sexism, and bigotry = *instant kick*, no matter who you are. Other clans might look past it, but not ours - find a different one if you have to.
        
Formed by a group of very welcoming individuals with many differences in life, but similar in ideals. 

Below you will find everything you need to know about how our clan operates.

**What we offer:**
• Raids & Bossing
• Mentorship
• Friendship
• Learner Events
• Clan Massing/Wildy Events
• Active Voice Chats""",
        color=discord.Color.from_rgb(184, 249, 249)
    )
    main_embed.add_field(
        name="🔗 Important Links",
        value="• **Wise Old Man:** [Obscurity Page](https://wiseoldman.net/groups/25289)",
        inline=False
    )

    channels_embed = discord.Embed(
        title="🪷 Channels",
        description="> A breakdown of the different categories and channels in our server.",
        color=discord.Color.from_rgb(196, 249, 233)
    )
    channels_embed.add_field(
        name="📢 【 ANNOUNCEMENTS 】",
        value="""• **#📣announcements** - Official clan news, events, and updates.
        • **#👤personal-announcements** - Member milestones and personal updates.
        • **#💥rank-up-announcements** - Announcements for achieved rank-ups""",
        inline=False
    )
    channels_embed.add_field(
        name="🛡️ 【 LANDING SITE 】",
        value="""• **#❗info** - You are here! General clan information.
• **#📚rules** - Our clan rules and community guidelines.
• **#✌️welcome** - The main entry point for new arrivals.
• **#🎯role-select** - Choose your ping preferences and bossing roles and pick a custom color.
• **#💡link-rsn-to-join** - Verify your OSRS account here to gain full access.""",
        inline=False
    )
    channels_embed.add_field(
        name="💜 【 SUPPORT 】",
        value="""• **#👐join** - Open a ticket to officially join the clan.
• **#⚔️ranks** - Apply for vanity, activity, and god alignment ranks.
• **#✉️contact** - Open a private ticket to speak with the admin team.""",
        inline=False
    )
    channels_embed.add_field(
        name="😀 【 CHAT 】",
        value="""• **#☮️general** - Hang out and chat about anything.
• **#⚔️grouping** - Find teams for raids, bosses, and minigames.
• **#👁️clan-chat** - Bridge connecting to our in-game clan chat.
• **#🤝collats** - Request and track collateral for item lending.
• **#😭memes** - Share your favorite OSRS and general memes.
• **#⭐drops-achievements** - Flex your new pets, purples, and 99s!""",
        inline=False
    )

    systems_embed = discord.Embed(
        title="🗺️ Clan Systems",
        description="> A quick guide to navigating our server and utilizing our systems.",
        color=discord.Color.from_rgb(196, 249, 233)
    )
    systems_embed.add_field(
        name="🎟️ Role and Ticket Systems",
        value="• https://discord.com/channels/1517374163655065631/1517402556651802731 - Claim your bossing roles here.\n• https://discord.com/channels/1517374163655065631/1518463880203079811 - Open a support ticket to speak privately with admins.\n• https://discord.com/channels/1517374163655065631/1518570261161447515 Change the color of your name!\n• https://discord.com/channels/1517374163655065631/1519007923940884510 Add in-game vanity roles!",
        inline=False
    )
    systems_embed.add_field(
        name="🔔 Collateral & Item Lending",
        value="Post collat requests in https://discord.com/channels/1517374163655065631/1517385356452958338. Paste an image and @mention a user in your post to summon the **Collat Notifier**. You can use the buttons on the message to notify players when an item is requested or returned.",
        inline=False
    )

    rank_embed = discord.Embed(
        title="⚔️ Ranking Structure",
        description="> Many of the ranks are purely vanity, from raid-specific roles to god alignments. The Zenyte and Maxxed roles need applying for, with full-client screenshots of the required items.",
        color=discord.Color.from_rgb(216, 249, 209)
    )
    rank_embed.add_field(
        name="🙂 Members & Verified",
        value="Registering your RSN grants the Verified role. Joining through the https://discord.com/channels/1517374163655065631/1518463838435938304 channel will grant you the member role",
        inline=False
    )
    rank_embed.add_field(
        name="🪞 Activity & Vanity Ranks",
        value="Ranks like Zenyte and Maxed are obtained through the rank application panel. Check the channel for details.",
        inline=False
    )
    rank_embed.add_field(
        name="📜 Mentors & Event Coordinators",
        value="These members are trusted to teach raids (ToB/CoX/ToA) or plan and host clan events. Reach out to them if you want to learn!",
        inline=False
    )
    rank_embed.add_field(
        name="🗝️ Administration",
        value="Staff structure is all handled at the top-level, with nothing below or higher. Admins handle anything between rule enforcement, ticket resolution, and server maintenance. They can all equally do the same things, but some may know more about certain subjects (i.e., Server support, Clan support, Community support, etc.), which is where a small distinction between admins is drawn. Do not DM them directly; please use the https://discord.com/channels/1517374163655065631/1518463880203079811 channel!",
        inline=False
    )

    bots_embed = discord.Embed(
        title="🤖 Server Bots",
        description="🎵 **Euphony - the music bot**\nUse /play and provide a link in a voice channel text chat or https://discord.com/channels/1517374163655065631/1518576235809214545.",
        color=discord.Color.from_rgb(235, 250, 185)
    )
    bots_embed.add_field(
        name="👁️ Obscura (Our Custom Bot)",
        value="Handles our tickets, RSN registration, clan coffer tracking, and role assignments. Type `/help` to see all available commands.",
        inline=False
    )
    bots_embed.add_field(
        name="🧙‍♂️ Wise Old Man",
        value="Tracks group EHP, EHB, and bossing records.",
        inline=False
    )

    await interaction.channel.send(embed=main_embed)
    await asyncio.sleep(0.5)
    await interaction.channel.send(embed=channels_embed)
    await asyncio.sleep(0.5)
    await interaction.channel.send(embed=systems_embed)
    await asyncio.sleep(0.5)
    await interaction.channel.send(embed=rank_embed)
    await asyncio.sleep(0.5)
    await interaction.channel.send(embed=bots_embed)

    await interaction.followup.send("✅ Clan info embeds have been posted.", ephemeral=True)

# ---------------------------
# 🔹 Rules Command
# ---------------------------

@bot.tree.command(name="rules", description="Post the clan rules message.")
@app_commands.checks.has_any_role("1517751423226613922")
async def rules(interaction: discord.Interaction):
    """Posts a series of embeds detailing the clan rules."""
    await interaction.response.defer(ephemeral=True, thinking=True)

    rule_data = [
        ("No unsolicited DM's",
         "If you have any issues or want to directly communicate with admins privately, DO NOT dm them directly; instead, utilize the ticket systems. We will not respond to direct DMs."),
        ("Zero Tolerance for Toxicity", 
         "Disrespect, toxicity, and elitism are strictly prohibited. Treat everyone with respect, or you will be removed. This is a friendly environment, and there are plenty of other clans out there."),
        ("No Heavy Religion or Politics", 
         "Absolutely no heavy religious or political discussions in the server or clan chat. Keep it in your private DMs or do not discuss it at all."),
        ("No Rage-Quitting", 
         "Abandoning a raid or boss mid-trip without a legitimate reason is unacceptable. It's better to leave at the start if anything, but leaving your team without saying anything will result in a warning."),
        ("No Doxing or Privacy Breaches", 
         "Sharing another person’s personal information without their explicit consent will result in a permanent ban. No exceptions."),
        ("Strict ToS Adherence", 
         "Macroing, Real World Trading (RWT), Solicitation, and Hate Speech (slurs, racist jokes, attacks on religions, nationalities, or identities) are actions that will result in an instant, unappealable ban. Ignorance of Jagex or Discord ToS is not an excuse; it's mostly common sense. Just don't do it or find another clan."),
        ("No Scamming, Luring, or Begging", 
         "Scammers and lurers will be instantly banned and submitted to RuneWatch. Begging is prohibited and will result in a warning."),
        ("Mandatory Loot Splitting Unless FFA", 
         "All uniques obtained in group content are considered to be split, and it should be stated that you are FFA before starting. This also applies to Ironmen and FFA worlds. Saying you can not split late into a raid or PvM trip is treated as scamming."),
        ("Approved Clients Only", 
         "Using cheat plug-ins or unofficial, unapproved clients is strictly prohibited. Cheaters will be removed if proof is provided."),
        ("IGN Matching", 
         "Your RSN should be linked through https://discord.com/channels/1517374163655065631/1517389307722076332")
    ]
    rule_colors = [
        (206, 2, 2), (201, 4, 4), (195, 5, 5), (190, 6, 6),
        (185, 7, 7), (179, 9, 9), (174, 10, 10), (168, 12, 12), (168, 12, 12)
    ]

    rule_embeds = [
        discord.Embed(title=title, description=description, color=discord.Color.from_rgb(*rule_colors[i]))
        for i, (title, description) in enumerate(rule_data)
    ]

    await interaction.channel.send(embeds=rule_embeds)
    await interaction.followup.send("✅ Rules message has been posted.", ephemeral=True)

# ---------------------------
# 🔹 Say Command
# ---------------------------

@bot.tree.command(name="say", description="Makes the bot say something in the current channel.")
@app_commands.describe(message="The message you want the bot to say.")
@app_commands.checks.has_any_role("Administrators")
async def say(interaction: discord.Interaction, message: str):
    """Makes the bot say something."""
    await interaction.channel.send(message)
    await interaction.response.send_message("✅ Message sent!", ephemeral=True, delete_after=5)

# ---------------------------
# 🔹 Help Command
# ---------------------------

@bot.tree.command(name="help", description="Shows a list of all available commands and what they do.")
async def help(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)

    embed = discord.Embed(
        title="🤖 Obscurity Bot Help",
        description="Here is a list of all the commands you can use. Commands marked with 🔒 are for Admins only.",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="👋 General Commands",
        value="""
        `/help` - Displays this help message.
        `/rsn` - Checks your currently registered RuneScape Name.
        """,
        inline=False
    )

    embed.add_field(
        name="💰 Clan Coffer Commands",
        value="""
        `/bank` - Shows the current coffer total and who is holding or owed money.
        `/deposit` - Opens a modal to deposit money into the clan coffer.
        `/withdraw` - Opens a modal to withdraw money from the clan coffer.
        `/holding [amount] [user]` - Sets or adds to the amount of money a user is holding.
        `/owed [amount] [user]` - Sets the amount of money a user is owed.
        `/clear_owed [user]` - Clears the owed amount for a specific user.
        `/clear_holding [user]` - Clears the holding amount for a specific user.
        """,
        inline=False
    )

    embed.add_field(
        name="🔒 Admin Commands",
        value="""
        `/info` - Posts the detailed clan information embeds in the current channel.
        `/rules` - Posts the clan rules embeds in the current channel.
        `/rank` - Posts the rank requirement embeds in the current channel.
        `/say [message]` - Makes the bot send the specified message in the current channel.
        `/welcome` - Welcomes a new member (in threads).
        `/rsn_panel` - Posts the interactive RSN registration panel.
        `/time_panel` - Posts the interactive timezone selection panel.
        """,
        inline=False
    )

    await interaction.followup.send(embed=embed, ephemeral=True)

# ---------------------------
# 🔹 Tickets
# ---------------------------

class ReasonModal(discord.ui.Modal, title="Close Ticket with Reason"):
    reason = discord.ui.TextInput(
        label="Reason for closing", 
        style=discord.TextStyle.paragraph, 
        required=True,
        placeholder="e.g., Application accepted, issue resolved..."
    )

    def __init__(self, thread: discord.Thread, creator: discord.User | discord.Member):
        super().__init__()
        self.thread = thread
        self.creator = creator

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Sending reason and closing ticket...", ephemeral=True)
        try:
            await self.creator.send(f"Your ticket (**{self.thread.name}**) has been closed.\n**Reason:** {self.reason.value}")
        except discord.Forbidden:
            await interaction.channel.send("⚠️ *Could not DM the user the reason (their DMs are closed).*")
        
        await self.thread.edit(archived=True, locked=True, reason=f"Closed by {interaction.user.display_name}")

class DelayModal(discord.ui.Modal, title="Delay Ticket Close"):
    hours = discord.ui.TextInput(
        label="Hours to delay", 
        placeholder="e.g., 2 (decimals work too, like 1.5)", 
        required=True
    )

    def __init__(self, thread: discord.Thread):
        super().__init__()
        self.thread = thread

    async def on_submit(self, interaction: discord.Interaction):
        try:
            delay_hours = float(self.hours.value)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number for hours.", ephemeral=True)
            return
        
        await interaction.response.send_message(f"⏱️ Ticket scheduled to close in **{delay_hours}** hours.", ephemeral=False)
        
        async def delayed_close():
            await asyncio.sleep(delay_hours * 3600)
            try:
                await self.thread.edit(archived=True, locked=True, reason="Auto-closed after delay.")
            except Exception:
                pass

        asyncio.create_task(delayed_close())

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def get_ticket_creator(self, thread: discord.Thread):
        async for message in thread.history(limit=5, oldest_first=True):
            if message.author.bot and message.mentions:
                return message.mentions[0]
        return None

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="ctrl_close_btn", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message("Locking and archiving ticket...", ephemeral=True)
            await interaction.channel.edit(archived=True, locked=True, reason=f"Closed by {interaction.user.display_name}")

    @discord.ui.button(label="Delay Close", style=discord.ButtonStyle.secondary, custom_id="ctrl_delay_btn", emoji="⏱️")
    async def delay_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_modal(DelayModal(interaction.channel))

    @discord.ui.button(label="Close With Reason", style=discord.ButtonStyle.primary, custom_id="ctrl_reason_btn", emoji="📝")
    async def close_reason(self, interaction: discord.Interaction, button: discord.ui.Button):
        if isinstance(interaction.channel, discord.Thread):
            creator = await self.get_ticket_creator(interaction.channel)
            if not creator:
                await interaction.response.send_message("❌ Could not identify the original ticket creator.", ephemeral=True)
                return
            await interaction.response.send_modal(ReasonModal(interaction.channel, creator))

class VanityTicketButton(discord.ui.Button):
    def __init__(self, role_name: str, requirements: str, emoji=None):
        super().__init__(
            label=role_name, 
            style=discord.ButtonStyle.secondary, 
            emoji=emoji, 
            custom_id=f"vanity_ticket_{role_name.replace(' ', '_')}"
        )
        self.role_name = role_name
        self.requirements = requirements

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("❌ This can only be used in a text channel.", ephemeral=True)
            return

        # 1. Defer the interaction immediately so Discord knows the bot is working on it
        await interaction.response.defer(ephemeral=True)

        try:
            # 2. Safely process the API calls
            thread_name = f"{self.role_name} - {interaction.user.display_name}"
            thread = await interaction.channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                auto_archive_duration=1440
            )
            await thread.add_user(interaction.user)

            embed = discord.Embed(
                title=f"⚔️ {self.role_name} Rank Application",
                color=discord.Color.from_rgb(184, 249, 249)
            )
            
            embed.description = (
                f"Hello {interaction.user.mention}!\n\n"
                f"To claim the **{self.role_name}** rank, you must meet the following requirements:\n"
                f"> **{self.requirements}**\n\n"
                "**⚠️ SCREENSHOT REQUIREMENTS ⚠️**\n"
                "Per clan rules, you **must** provide full client screenshots with your chatbox open to be approved for this rank. Cropped images will be rejected."
            )

            if self.emoji and self.emoji.url:
                embed.set_thumbnail(url=self.emoji.url)

            await thread.send(
                content=f"{interaction.user.mention} <@&{ADMINISTRATOR_ROLE_ID}>", 
                embed=embed, 
                view=TicketControlView()
            )
            
            # 3. Use followup.send instead of response.send_message since we deferred earlier
            await interaction.followup.send(f"✅ Application ticket opened: {thread.mention}", ephemeral=True)
            
        except Exception as e:
            # If rate-limited, it fails gracefully and tells the user
            await interaction.followup.send(f"❌ Failed to create ticket. Please try again in a moment. (Error: `{e}`)", ephemeral=True)


class VanityView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        get_emoji = lambda name: discord.utils.get(guild.emojis, name=name)
        
        self.add_item(VanityTicketButton("Recruit", "Combat 80 + Dragon Gloves, Dragon Defender", get_emoji("recruit")))
        self.add_item(VanityTicketButton("Pawn", "Combat 90 + Barrow Gloves, Regular Void, Medium CAs", get_emoji("pawn")))
        self.add_item(VanityTicketButton("Corporal", "Combat 100 + Elite Void, Piety, Fire Cape", get_emoji("corporal")))
        self.add_item(VanityTicketButton("Novice", "Combat 110 + Upgraded Runepouch, Hard CA's", get_emoji("novice")))
        self.add_item(VanityTicketButton("Sergeant", "Combat 120 + Quiver *or* Infernal Cape, Elite CA's", get_emoji("sergeant")))
        self.add_item(VanityTicketButton("Marshall", "Combat 122 + Quiver *and* Infernal cape, Master CA's", get_emoji("marshall")))
        self.add_item(VanityTicketButton("TzKal", "Grandmaster CA's", get_emoji("tzkal")))
        
        self.add_item(VanityTicketButton("Pet Hunter", "Minimum total of 20 pets obtained", get_emoji("hellcat")))
        self.add_item(VanityTicketButton("Collection Logger", "Filled 1000 collection log slots", get_emoji("coordinator")))
        self.add_item(VanityTicketButton("Maxed", "2376 total level", get_emoji("maxed")))
        
        self.add_item(RoleButton("Serenist", get_emoji("seren")))
        self.add_item(RoleButton("Dogsbody", get_emoji("dogsbody")))
        self.add_item(RoleButton("Skiller", get_emoji("skiller")))

class WelcomeTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Join The Clan", style=discord.ButtonStyle.blurple, custom_id="welcome_ticket_btn", emoji="👐")
    async def open_welcome_thread(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(JoinModal())

class SupportTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Support Ticket", style=discord.ButtonStyle.blurple, custom_id="support_ticket_btn", emoji="🗝️")
    async def open_support_thread(self, interaction: discord.Interaction, button: discord.ui.Button):
        if isinstance(interaction.channel, discord.TextChannel):
            thread_name = f"Support - {interaction.user.display_name}"
            thread = await interaction.channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                auto_archive_duration=1440
            )
            await thread.add_user(interaction.user)

            await thread.send(
                content=f"Hey {interaction.user.mention} - please leave your response below and an admin (<@&{ADMINISTRATOR_ROLE_ID}>) will help you out shortly.", 
                view=TicketControlView()
            )
            await interaction.response.send_message(f"Support ticket opened: {thread.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("Support Ticket failed to open - Please contact server admin.", ephemeral=True)
    
@bot.tree.command(name="panel_welcome", description="Post the Welcome ticket panel.")
@app_commands.checks.has_any_role("Administrators")
async def panel_welcome(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✨ Apply to Join Obscurity ✨", 
        description="We are thrilled that you're interested in joining our community! To start your application process, please click the 'Join' button below.",
        color=discord.Color.from_rgb(184, 249, 249)
    )
    
    embed.add_field(
        name="👥 Our Community",
        value="We uphold a welcoming and positive environment.\n\nThose that value these things might find this community to be the place they have been looking for, and we intend to keep it that way.\n\nWe hold our values and what we do to as high a standard as reasonably possible - we only ask that our members do the same.\n\nThat being said, please follow our rules. Knowingly breaking them will be cause for removal from the clan.",
        inline=False
    )
    
    embed.add_field(
        name="🎒 Requirements",
        value="To join the clan you should be friendly and positive. The main items we'll ask for are basic PvM gear.\n\nYou can use the image below as a rough estimate - though you should have full tribrid gear of *some* kind.",
        inline=False
    )

    embed.add_field(
        name="⚠️ Before You Apply",
        value="Please ensure you have read the server rules here: https://discord.com/channels/1517374163655065631/1517389459459538994.",
        inline=False
    )
    
    embed.set_image(url="")
    embed.set_footer(text="Join Obscurity • Click the button below to begin")
    
    await interaction.response.send_message("Posting Welcome panel...", ephemeral=True)
    await interaction.channel.send(embed=embed, view=WelcomeTicketView())

@bot.tree.command(name="panel_support", description="Post the Support ticket panel.")
@app_commands.checks.has_any_role("Administrators")
async def panel_support(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🆘 Support Center", 
        description="Need assistance from the administration team? Open a private support ticket and we will help you as soon as we are available.",
        color=discord.Color.from_rgb(43, 45, 49)
    )

    embed.add_field(
        name="📌 What can we help with?",
        value="• **Questions:** General inquiries about the clan or systems.\n• **Reports:** Reporting a player for breaking rules or toxic behavior.\n• **Coffer/Bank:** Issues or questions regarding clan wealth and payouts.\n• **Roles:** Requesting missing roles or name updates.",
        inline=False
    )
    
    embed.add_field(
        name="⏳ Response Time",
        value="Admins are in various timezones. Please be patient after opening your ticket and provide as much detail as possible.",
        inline=False
    )

    embed.set_footer(text="Obscurity Admin Team • Please don't misuse the ticket system and refrain from messaging admins directly.")
    
    await interaction.response.send_message("Posting Support panel...", ephemeral=True)
    await interaction.channel.send(embed=embed, view=SupportTicketView())
    

# ---------------------------
# 🔹 Color Panel
# ---------------------------

class ColorButton(discord.ui.Button):
    def __init__(self, role_name: str, emoji: str, row: int):
        super().__init__(
            style=discord.ButtonStyle.secondary, 
            label=role_name, 
            emoji=emoji, 
            custom_id=f"color_role_{role_name.replace(' ', '_')}", 
            row=row
        )
        self.role_name = role_name

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This can only be used in a server.", ephemeral=True)
            return
        
        guild = interaction.guild
        if not guild: return
        
        role_objects = []
        target_role = None
        for role in guild.roles:
            if role.name in COLOR_ROLE_NAMES:
                role_objects.append(role)
                if role.name == self.role_name:
                    target_role = role
        
        if not target_role:
            await interaction.response.send_message(f"Role '{self.role_name}' not found in the server. Please ask an admin to create it first.", ephemeral=True)
            return
        
        roles_to_remove = [r for r in role_objects if r in interaction.user.roles and r != target_role]
        
        await interaction.response.defer(ephemeral=True)
        try:
            if roles_to_remove:
                await interaction.user.remove_roles(*roles_to_remove, reason="Color role switch")
            
            if target_role not in interaction.user.roles:
                await interaction.user.add_roles(target_role, reason="Color role selection")
                await interaction.followup.send(f"Equipped the **{self.role_name}** color!", ephemeral=True)
            else:
                await interaction.user.remove_roles(target_role, reason="Color role toggle off")
                await interaction.followup.send(f"Removed the **{self.role_name}** color.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("I lack permissions to manage roles. Please ensure my bot role is higher than the color roles.", ephemeral=True)

class ColorPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for i, (role_name, emoji) in enumerate(COLOR_ROLES_CONFIG):
            self.add_item(ColorButton(role_name, emoji, row=i // 5))

class JoinModal(discord.ui.Modal, title="Join Obscurity"):
    referral = discord.ui.TextInput(
        label="How did you hear about us?",
        style=discord.TextStyle.short,
        placeholder="e.g., Reddit, Friend, In-game...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if isinstance(interaction.channel, discord.TextChannel):
            thread_name = f"Welcome - {interaction.user.display_name}"
            thread = await interaction.channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                auto_archive_duration=1440
            )
            await thread.add_user(interaction.user)

            # 1. Setup the primary requirements embed
            requirements_embed = discord.Embed(
                title="Clan Requirements",
                description="Thanks for your interest in joining Obscurity. We're a learner-friendly and all-inclusive clan. Please send the requirements for the clan below so someone can assist you.",
                color=discord.Color.blurple()
            )
            
            requirements_embed.add_field(
                name="⏳ Response Time",
                value="Admins are in various timezones. Please be patient after opening your ticket.",
                inline=False
            )
            
            # 2. Create the separate Join Method embed
            join_method_embed = discord.Embed(
                title="Join Method",
                description=self.referral.value,
                color=discord.Color.blurple()
            )

            welcome_message = f"Hello {interaction.user.mention}! A member of the <@&1517751423226613922> team will be right with you to help."
            
            # 3. Pass both embeds in a list so they stack neatly in the ticket
            await thread.send(
                content=welcome_message, 
                embeds=[requirements_embed, join_method_embed], 
                view=TicketControlView()
            )
            
            await interaction.response.send_message(f"Welcome ticket opened here: {thread.mention}", ephemeral=True)
            
        else:
            await interaction.response.send_message("Ticket failed to open! Please try again...", ephemeral=True)
# ---------------------------
# 🔹 Welcome
# ---------------------------

class BaseRoleButton(discord.ui.Button):
    def __init__(self, role_name: str, role_id: int, emoji=None):
        super().__init__(
            label=role_name, 
            style=discord.ButtonStyle.secondary, 
            emoji=emoji, 
            custom_id=f"baserole_{role_id}"
        )
        self.role_name = role_name
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if not role:
            await interaction.response.send_message(f"❌ Role '{self.role_name}' not found in server.", ephemeral=True)
            return

        # Prevent users from having both base roles simultaneously
        other_id = 1528545466227359785 if self.role_id == 1528789248415891516 else 1528789248415891516
        other_role = interaction.guild.get_role(other_id)
        
        if other_role and other_role in interaction.user.roles:
            await interaction.user.remove_roles(other_role)

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"{interaction.user.mention}, role **{self.role_name}** removed.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"{interaction.user.mention}, role **{self.role_name}** added.", ephemeral=True)

class WelcomeBaseRoleView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        get_emoji = lambda name: discord.utils.get(guild.emojis, name=name)
        
        # Uses the exact Role IDs requested
        self.add_item(BaseRoleButton("Serenist", 1528789248415891516, get_emoji("seren")))
        self.add_item(BaseRoleButton("Dogsbody", 1528545466227359785, get_emoji("dogsbody")))

@bot.tree.command(name="welcome", description="Welcome the ticket creator and give them default roles.")
async def welcome(interaction: discord.Interaction):
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("⚠️ This command must be used inside a ticket thread.", ephemeral=True)
        return

    ticket_creator = None
    async for message in interaction.channel.history(limit=20, oldest_first=True):
        if message.author.bot:
            for mention in message.mentions:
                if not mention.bot:
                    ticket_creator = mention
                    break
            if ticket_creator:
                break

    if not ticket_creator:
        await interaction.response.send_message("⚠️ Could not detect who opened this ticket.", ephemeral=True)
        return

    roles_to_assign = ["Member"] 
    missing_roles = []
    guild = interaction.guild

    for role_name in roles_to_assign:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            await ticket_creator.add_roles(role)
        else:
            missing_roles.append(role_name)

    embed = discord.Embed(
        title="🎉 Welcome to Obscurity! 🎉",
        description=f"""Happy to have you with us, {ticket_creator.mention}!\n
                    Head over to https://discord.com/channels/1517374163655065631/1517389459459538994 to familiarize yourself with our rules so you aren't accidentally breaking them!\n
                    """,
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(embed=embed, view=WelcomeView())

    # 🔹 Wait 1 second, then post the base role prompt
    await asyncio.sleep(1)
    
    role_embed = discord.Embed(
        title="Choose Your Path",
        description="Which base role would you like to start with?",
        color=discord.Color.from_rgb(184, 249, 249)
    )
    role_embed.add_field(
        name="<:seren:1519259305658814474> Serenist", 
        value="New members who want to (learn) pvm.", 
        inline=False
    )
    role_embed.add_field(
        name="<:dogsbody:1528781938348003490> Dogsbody", 
        value="New members who are here for vibes and community without focus on pvm.", 
        inline=False
    )
    
    await interaction.channel.send(embed=role_embed, view=WelcomeBaseRoleView(interaction.guild))

class WelcomeView(View):
    def __init__(self):
        super().__init__(timeout=None)

# -----------------------------
# Role Button & Views
# -----------------------------

class RoleButton(Button):
    def __init__(self, role_name: str, emoji=None):
        super().__init__(label=role_name, style=discord.ButtonStyle.secondary, emoji=emoji, custom_id=role_name)

    async def callback(self, interaction: discord.Interaction):
        role_name = self.custom_id
        role = discord.utils.get(interaction.guild.roles, name=role_name)

        if not role:
            await interaction.response.send_message(f"❌ Role '{role_name}' not found.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            feedback = f"{interaction.user.mention}, role **{role_name}** removed."
        else:
            await interaction.user.add_roles(role)
            feedback = f"{interaction.user.mention}, role **{role_name}** added."

        await interaction.response.send_message(feedback, ephemeral=True)
        await asyncio.sleep(1)
        try:
            await interaction.delete_original_response()
        except Exception:
            pass

class RaidsView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        get_emoji = lambda name: discord.utils.get(guild.emojis, name=name)
        self.add_item(RoleButton("Theatre of Blood", get_emoji("tob")))
        self.add_item(RoleButton("Chambers of Xeric", get_emoji("cox")))
        self.add_item(RoleButton("Tombs of Amascut", get_emoji("toa")))
        self.add_item(RoleButton("Theatre of Blood Hard Mode", get_emoji("hmt")))
        self.add_item(RoleButton("Chambers of Xeric Challenge Mode", get_emoji("cm")))


class BossesView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        get_emoji = lambda name: discord.utils.get(guild.emojis, name=name)
        self.add_item(RoleButton("Bandos GWD", get_emoji("graardor")))
        self.add_item(RoleButton("Saradomin GWD", get_emoji("sara")))
        self.add_item(RoleButton("Zamorak GWD", get_emoji("zammy")))
        self.add_item(RoleButton("Armadyl GWD", get_emoji("arma")))
        self.add_item(RoleButton("Nex", get_emoji("nex")))
        self.add_item(RoleButton("Corporeal Beast", get_emoji("corp")))
        self.add_item(RoleButton("Callisto", get_emoji("callisto")))
        self.add_item(RoleButton("Vet'ion", get_emoji("vetion")))
        self.add_item(RoleButton("Venenatis", get_emoji("venenatis")))
        self.add_item(RoleButton("Hueycoatl", get_emoji("hueycoatl")))
        self.add_item(RoleButton("Yama", get_emoji("yama")))

class EventsView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        get_emoji = lambda name: discord.utils.get(guild.emojis, name=name)
        self.add_item(RoleButton("Events", get_emoji("event")))
        self.add_item(RoleButton("Learn ToB!", get_emoji("sanguine")))
        self.add_item(RoleButton("PvP", "💀"))

class OtherRolesView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        get_emoji = lambda name: discord.utils.get(guild.emojis, name=name)
        # Using some default discord emojis here, but feel free to swap them out!
        self.add_item(RoleButton("Other Games", "🎮"))
        self.add_item(RoleButton("Geoguessr", "🌍"))
        self.add_item(RoleButton("Osrs TCG", "🃏"))
        self.add_item(RoleButton("Movie Nights", "🍿"))

class ToBModal(discord.ui.Modal, title="Learn Theatre of Blood"):
    goals = discord.ui.TextInput(
        label="What are you trying to learn?",
        style=discord.TextStyle.short,
        placeholder="e.g., Beginner, Metas, Specific roles",
        required=True
    )
    gear = discord.ui.TextInput(
        label="What is your gear?",
        style=discord.TextStyle.paragraph,
        placeholder="Refer to the setups in the gear channel",
        required=True
    )
    verzik = discord.ui.TextInput(
        label="Have you ever been to Verzik?",
        style=discord.TextStyle.short,
        placeholder="Yes or No",
        required=True
    )
    hard_mode = discord.ui.TextInput(
        label="Do you want to learn Hard Mode?",
        style=discord.TextStyle.short,
        placeholder="Yes or No",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.client.get_channel(LEARNER_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("❌ Error: Learner channel not found.", ephemeral=True)
            return

        thread_name = f"ToB Learner - {interaction.user.display_name}"
        thread = await channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.private_thread,
            auto_archive_duration=1440
        )
        await thread.add_user(interaction.user)

        embed = discord.Embed(
            title="🩸 ToB Learner Ticket",
            color=discord.Color.red()
        )
        embed.add_field(name="Goals", value=self.goals.value, inline=False)
        embed.add_field(name="Gear", value=self.gear.value, inline=False)
        embed.add_field(name="Verzik Experience", value=self.verzik.value, inline=False)
        embed.add_field(name="Hard Mode ToB", value=self.hard_mode.value, inline=False)
        embed.set_footer(text="Please review: https://discord.com/channels/1517374163655065631/1519831937575944243")

        await thread.send(
            content=f"{interaction.user.mention} | <@&{MENTOR_TOB_ID}>",
            embed=embed,
            view=TicketControlView() # Reusing your existing ticket control system
        )
        
        await interaction.response.send_message(f"✅ Your ToB ticket has been opened: {thread.mention}", ephemeral=True)

class CoXModal(discord.ui.Modal, title="Learn Chambers of Xeric"):
    goals = discord.ui.TextInput(
        label="What are you trying to learn?",
        style=discord.TextStyle.short,
        placeholder="e.g., Beginner, Metas",
        required=True
    )
    gear = discord.ui.TextInput(
        label="What is your gear?",
        style=discord.TextStyle.paragraph,
        placeholder="Refer to the setups in the gear channel",
        required=True
    )
    dwh = discord.ui.TextInput(
        label="Do you have a dragon warhammer?",
        style=discord.TextStyle.short,
        placeholder="Yes or No",
        required=True
    )
    challenge_mode = discord.ui.TextInput(
        label="Do you want to learn Challenge Mode?",
        style=discord.TextStyle.short,
        placeholder="Yes or No",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.client.get_channel(LEARNER_CHANNEL_ID)
        thread = await channel.create_thread(
            name=f"CoX Learner - {interaction.user.display_name}",
            type=discord.ChannelType.private_thread,
            auto_archive_duration=1440
        )
        await thread.add_user(interaction.user)

        embed = discord.Embed(title="🐉 CoX Learner Ticket", color=discord.Color.green())
        embed.add_field(name="Goals", value=self.goals.value, inline=False)
        embed.add_field(name="Gear", value=self.gear.value, inline=False)
        embed.add_field(name="Dragon Warhammer", value=self.dwh.value, inline=False)
        embed.add_field(name="Challenge Mode", value=self.challenge_mode.value, inline=False)
        embed.set_footer(text="Please review: https://discord.com/channels/1517374163655065631/1519831937575944243")

        await thread.send(
            content=f"{interaction.user.mention} | <@&{MENTOR_COX_ID}>",
            embed=embed,
            view=TicketControlView()
        )
        await interaction.response.send_message(f"✅ Your CoX ticket has been opened: {thread.mention}", ephemeral=True)

class ToAModal(discord.ui.Modal, title="Learn Tombs of Amascut"):
    invocation = discord.ui.TextInput(
        label="What invocation level do you want to learn?",
        style=discord.TextStyle.short,
        placeholder="e.g., Normal mode, Expert Mode, or High Invo?",
        required=True
    )
    gear = discord.ui.TextInput(
        label="What is your gear?",
        style=discord.TextStyle.paragraph,
        placeholder="Refer to the setups in the gear channel",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.client.get_channel(LEARNER_CHANNEL_ID)
        thread = await channel.create_thread(
            name=f"ToA Learner - {interaction.user.display_name}",
            type=discord.ChannelType.private_thread,
            auto_archive_duration=1440
        )
        await thread.add_user(interaction.user)

        embed = discord.Embed(title="🏜️ ToA Learner Ticket", color=discord.Color.gold())
        embed.add_field(name="Invocation Level", value=self.invocation.value, inline=False)
        embed.add_field(name="Gear", value=self.gear.value, inline=False)
        embed.set_footer(text="Please review: https://discord.com/channels/1517374163655065631/1519831937575944243")

        await thread.send(
            content=f"{interaction.user.mention} | <@&{MENTOR_TOA_ID}>",
            embed=embed,
            view=TicketControlView()
        )
        await interaction.response.send_message(f"✅ Your ToA ticket has been opened: {thread.mention}", ephemeral=True)

class GeneralModal(discord.ui.Modal, title="Learn a Boss"):
    boss = discord.ui.TextInput(
        label="What boss do you want to learn?",
        style=discord.TextStyle.short,
        placeholder="e.g., God Wars, Zulrah, Vorkath",
        required=True
    )
    experience = discord.ui.TextInput(
        label="Are you a beginner or learning mechanics?",
        style=discord.TextStyle.short,
        placeholder="e.g., Complete beginner, just need help with X",
        required=True
    )
    gear = discord.ui.TextInput(
        label="Do you have the gear for this boss?",
        style=discord.TextStyle.short,
        placeholder="Yes or No",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.client.get_channel(LEARNER_CHANNEL_ID)
        thread = await channel.create_thread(
            name=f"Boss Learner - {interaction.user.display_name}",
            type=discord.ChannelType.private_thread,
            auto_archive_duration=1440
        )
        await thread.add_user(interaction.user)

        embed = discord.Embed(title="⚔️ General Boss Learner Ticket", color=discord.Color.blue())
        embed.add_field(name="Target Boss", value=self.boss.value, inline=False)
        embed.add_field(name="Experience Level", value=self.experience.value, inline=False)
        embed.add_field(name="Gear Ready", value=self.gear.value, inline=False)
        embed.set_footer(text="Please review: https://discord.com/channels/1517374163655065631/1519831937575944243")

        await thread.send(
            content=f"{interaction.user.mention} | <@&{MENTOR_GENERAL_ID}>",
            embed=embed,
            view=TicketControlView()
        )
        await interaction.response.send_message(f"✅ Your Bossing ticket has been opened: {thread.mention}", ephemeral=True)


class ColosseumModal(discord.ui.Modal, title="Learn the Colosseum"):
    first_time = discord.ui.TextInput(
        label="Is it your first time entering the Colo?",
        style=discord.TextStyle.short,
        placeholder="Yes or No",
        required=True
    )
    research = discord.ui.TextInput(
        label="Have you researched this content at all?",
        style=discord.TextStyle.paragraph,
        placeholder="e.g., Watched guides, know the basics, etc.",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.client.get_channel(LEARNER_CHANNEL_ID)
        thread = await channel.create_thread(
            name=f"Colo Learner - {interaction.user.display_name}",
            type=discord.ChannelType.private_thread,
            auto_archive_duration=1440
        )
        await thread.add_user(interaction.user)

        embed = discord.Embed(title="🏟️ Colosseum Learner Ticket", color=discord.Color.dark_theme())
        embed.add_field(name="First Time?", value=self.first_time.value, inline=False)
        embed.add_field(name="Prior Research", value=self.research.value, inline=False)
        embed.set_footer(text="Please review: https://discord.com/channels/1517374163655065631/1519831937575944243")

        await thread.send(
            content=f"{interaction.user.mention} | <@&{MENTOR_COLO_ID}>",
            embed=embed,
            view=TicketControlView()
        )
        await interaction.response.send_message(f"✅ Your Colosseum ticket has been opened: {thread.mention}", ephemeral=True)


class InfernoModal(discord.ui.Modal, title="Learn the Inferno"):
    first_time = discord.ui.TextInput(
        label="Is it your first time entering the Inferno?",
        style=discord.TextStyle.short,
        placeholder="Yes or No",
        required=True
    )
    research = discord.ui.TextInput(
        label="Have you researched this content at all?",
        style=discord.TextStyle.paragraph,
        placeholder="e.g., Watched guides, know the basics, etc.",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.client.get_channel(LEARNER_CHANNEL_ID)
        thread = await channel.create_thread(
            name=f"Inferno Learner - {interaction.user.display_name}",
            type=discord.ChannelType.private_thread,
            auto_archive_duration=1440
        )
        await thread.add_user(interaction.user)

        embed = discord.Embed(title="🔥 Inferno Learner Ticket", color=discord.Color.orange())
        embed.add_field(name="First Time?", value=self.first_time.value, inline=False)
        embed.add_field(name="Prior Research", value=self.research.value, inline=False)
        embed.set_footer(text="Please review: https://discord.com/channels/1517374163655065631/1519831937575944243")

        await thread.send(
            content=f"{interaction.user.mention} | <@&{MENTOR_INFERNO_ID}>",
            embed=embed,
            view=TicketControlView()
        )
        await interaction.response.send_message(f"✅ Your Inferno ticket has been opened: {thread.mention}", ephemeral=True)


class LearnerTicketButton(discord.ui.Button):
    def __init__(self, label: str, style: discord.ButtonStyle, custom_id: str, modal_class, emoji=None):
        super().__init__(label=label, style=style, custom_id=custom_id, emoji=emoji)
        self.modal_class = modal_class

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(self.modal_class())

class LearnerTicketView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        get_emoji = lambda name: discord.utils.get(guild.emojis, name=name)
        
        self.add_item(LearnerTicketButton("Learn ToB", discord.ButtonStyle.danger, "learner_tob_btn", ToBModal, get_emoji("tob")))
        self.add_item(LearnerTicketButton("Learn CoX", discord.ButtonStyle.success, "learner_cox_btn", CoXModal, get_emoji("cox")))
        self.add_item(LearnerTicketButton("Learn ToA", discord.ButtonStyle.primary, "learner_toa_btn", ToAModal, get_emoji("toa")))
        self.add_item(LearnerTicketButton("Learn General Boss", discord.ButtonStyle.secondary, "learner_general_btn", GeneralModal, get_emoji("raider")))
        self.add_item(LearnerTicketButton("Learn Colosseum", discord.ButtonStyle.secondary, "learner_colo_btn", ColosseumModal, get_emoji("colosseum")))
        self.add_item(LearnerTicketButton("Learn Inferno", discord.ButtonStyle.secondary, "learner_inferno_btn", InfernoModal, get_emoji("inferno")))

@bot.tree.command(name="panel_learner", description="Post the Mentor/Learner ticket panel.")
@app_commands.checks.has_any_role("Administrators")
async def panel_learner(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 Learner & Mentor Requests", 
        description="Looking to learn a raid? Click the corresponding button below to fill out a request form. A mentor will be pinged and will assist you in a private thread as soon as they are available.",
        color=discord.Color.from_rgb(184, 249, 249)
    )

    embed.add_field(
        name="⚠️ Gear Requirements",
        value="Before applying, please ensure your gear meets the minimum requirements for mentoring (see here: https://discord.com/channels/1517374163655065631/1529761437021376512)",
        inline=False
    )
    
    await interaction.response.send_message("Posting Learner panel...", ephemeral=True)
    # Passed interaction.guild into the View here
    await interaction.channel.send(embed=embed, view=LearnerTicketView(interaction.guild))

# ---------------------------
# 🔹 RSN Commands
# ---------------------------

rsn_write_queue = asyncio.Queue()

async def rsn_writer():
    while True:
        member, rsn_value = await rsn_write_queue.get()
        try:
            cell = rsn_sheet.find(str(member.id))
            now = datetime.now(timezone.utc)
            timestamp = now.strftime(f"%B {now.day}, %Y at %I:%M%p")

            if cell is not None:
                rsn_sheet.update_cell(cell.row, 4, rsn_value)
                rsn_sheet.update_cell(cell.row, 5, timestamp)
            else:
                rsn_sheet.append_row([
                    member.name,
                    str(member.id),
                    "",
                    rsn_value,
                    timestamp
                ])
        except Exception as e:
            print(f"❌ Error writing RSN to sheet for {member}: {e}")
        finally:
            rsn_write_queue.task_done()

class RSNModal(discord.ui.Modal, title="Register RSN"):
    rsn = discord.ui.TextInput(label="RuneScape Name", placeholder="Enter your RSN")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            await rsn_write_queue.put((interaction.user, str(self.rsn)))
            await interaction.followup.send(f"✅ Your RSN **{self.rsn}** has been submitted!", ephemeral=True)
            
            verified_role = discord.utils.get(interaction.guild.roles, name="Verified")
            if verified_role and verified_role not in interaction.user.roles:
                await interaction.user.add_roles(verified_role)

            try:
                await interaction.user.edit(nick=str(self.rsn))
            except discord.Forbidden:
                pass
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to update RSN: `{e}`", ephemeral=True)

class RSNPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Register RSN", style=discord.ButtonStyle.success, emoji="📝", custom_id="register_rsn_button")
    async def register_rsn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RSNModal())

@tree.command(name="rsn_panel", description="Open the RSN registration panel.")
@app_commands.checks.has_any_role("Administrators")
async def rsn_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Register your RuneScape Name",
        description="Click the button below to register or update your RuneScape name in the records.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=RSNPanelView(), ephemeral=False)

@tree.command(name="rsn", description="Check your registered RSN.")
async def rsn(interaction: discord.Interaction):
    try:
        cell = rsn_sheet.find(str(interaction.user.id))
        rsn_value = rsn_sheet.cell(cell.row, 4).value
        await interaction.response.send_message(f"✅ Your registered RSN is **{rsn_value}**.", ephemeral=True)
    except gspread.exceptions.CellNotFound:
        await interaction.response.send_message("⚠️ You have not registered an RSN yet.", ephemeral=True)

# ---------------------------
# 🔹 TimeZones
# ---------------------------

TIMEZONE_DATA = {
    "PST": ("America/Los_Angeles", "🇺🇸"),
    "MST": ("America/Denver", "🇺🇸"),
    "CST": ("America/Chicago", "🇺🇸"),
    "EST": ("America/New_York", "🇺🇸"),
    "GMT": ("Europe/London", "🇬🇧"),
    "CET": ("Europe/Belgium", "🇧🇪"),
    "AEST": ("Australia/Sydney", "🇦🇺"),
}

TIME_OF_DAY_DATA = {
    "Morning": ("🌄", "6 AM - 12 PM"),
    "Day": ("🌇", "12 PM - 6 PM"),
    "Evening": ("🌆", "6 PM - 12 AM"),
    "Night": ("🌃", "12 AM - 6 AM"),
}

class TimeOfDayView(discord.ui.View):
    def __init__(self, guild, timezone_role, tz_abbr):
        super().__init__(timeout=60)
        self.guild = guild
        self.timezone_role = timezone_role
        self.tz_abbr = tz_abbr

        for tod_label, (emoji, _) in TIME_OF_DAY_DATA.items():
            role = discord.utils.get(guild.roles, name=tod_label)
            if role:
                self.add_item(TimeOfDayButton(tod_label, role, emoji, self.timezone_role, self.tz_abbr))

class TimeOfDayButton(discord.ui.Button):
    def __init__(self, label, role, emoji, timezone_role, tz_abbr):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, emoji=emoji)
        self.role = role
        self.label = label
        self.timezone_role = timezone_role
        self.tz_abbr = tz_abbr

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        if self.role in member.roles:
            await member.remove_roles(self.role)
            await interaction.response.send_message(f"❌ Removed time of day role **{self.label}**.", ephemeral=True)
            return

        await member.add_roles(self.role)
        await interaction.response.send_message(f"✅ Added time of day role **{self.label}** for timezone **{self.tz_abbr}**.", ephemeral=True)

class TimezoneView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        for tz_abbr, (tz_str, flag) in TIMEZONE_DATA.items():
            role = discord.utils.get(guild.roles, name=tz_abbr)
            if role:
                self.add_item(TimezoneButton(tz_abbr, role, tz_str, flag, guild))

class TimezoneButton(discord.ui.Button):
    def __init__(self, tz_abbr, role, tz_str, emoji, guild):
        custom_id = f"timezone-btn:{role.id}"
        super().__init__(label=tz_abbr, style=discord.ButtonStyle.primary, custom_id=custom_id, emoji=emoji)
        self.tz_abbr = tz_abbr
        self.role = role
        self.tz_str = tz_str
        self.guild = guild

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild

        if self.role in member.roles:
            await member.remove_roles(self.role)
            await interaction.response.send_message(f"❌ Removed timezone role **{self.tz_abbr}**.", ephemeral=True)
            return

        old_tz_roles = [r for abbr in TIMEZONE_DATA.keys() if (r := discord.utils.get(guild.roles, name=abbr)) in member.roles]
        if old_tz_roles:
            await member.remove_roles(*old_tz_roles)

        await member.add_roles(self.role)
        await interaction.response.send_message(f"✅ Timezone set to **{self.tz_abbr}**. Select your usual time of day:", view=TimeOfDayView(guild, self.role, self.tz_abbr), ephemeral=True)

@bot.tree.command(name="time_panel", description="Open the timezone selection panel.")
async def time_panel(interaction: discord.Interaction):
    view = TimezoneView(interaction.guild)
    embed = discord.Embed(
        title="🕒 Select Your Usual Timezones",
        description="Click the button that best matches the timezones you are most often active.",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ---------------------------
# 🔹 Coffer
# ---------------------------

def parse_amount(input_str: str) -> int:
    input_str = input_str.lower().replace(" ", "").replace(",", ".")
    if input_str.endswith("m"):
        return int(float(input_str[:-1]) * 1_000_000)
    return int(float(input_str) * 1_000_000)

def format_million(amount: int) -> str:
    millions = amount / 1_000_000
    if millions.is_integer():
        return f"{int(millions):,}M"
    return f"{millions:,.2f}M".rstrip('0').rstrip('.')

def log_coffer_entry(discord_id: int, discord_name: str, action: str, amount_changed: int, coffer_total: int, holding: int, owed: int):
    timestamp = datetime.now(CST).strftime("%I:%M%p %m/%d/%Y").lstrip("0").replace(" 0", " ")
    
    # This matches the exact 8 columns in your image
    row = [
        timestamp,
        action,
        str(discord_id),
        discord_name,
        amount_changed,
        coffer_total,
        holding,
        owed
    ]
    coffer_sheet.append_row(row)

def get_current_total_and_holders_and_owed():
    try:
        records = coffer_sheet.get_all_records()
    except Exception:
        return 0, {}, {}
        
    total = 0
    holders = {}
    owed = {}
    
    for r in records:
        # Rebuild the totals based on the history in the sheet
        name = str(r.get("Discord Name", ""))
        if not name:
            continue
            
        # The sheet tracks the latest holding/owed for the user on their row
        if r.get("Holding", "") != "":
            try:
                holders[name] = int(str(r["Holding"]).replace(",", ""))
            except ValueError:
                pass
                
        if r.get("Owed", "") != "":
            try:
                owed[name] = int(str(r["Owed"]).replace(",", ""))
            except ValueError:
                pass

        if r.get("Coffer Total", "") != "":
            try:
                total = int(str(r["Coffer Total"]).replace(",", ""))
            except ValueError:
                pass

    return total, {k: v for k, v in holders.items() if v > 0}, {k: v for k, v in owed.items() if v > 0}

class DepositWithdrawModal(Modal, title="Deposit/Withdraw"):
    amount_input = TextInput(label="Amount", placeholder="Enter amount (e.g. 20m)", required=True)

    def __init__(self, action: str):
        super().__init__()
        self.action = action

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = parse_amount(self.amount_input.value)
        except Exception:
            await interaction.response.send_message("❌ Invalid format.", ephemeral=True)
            return

        # Changed to user.name to use their actual Discord name instead of nickname
        name = interaction.user.name
        user_id = interaction.user.id
        total, holders, owed = get_current_total_and_holders_and_owed()
        
        current_holding = holders.get(name, 0)
        current_owed = owed.get(name, 0)
        
        if self.action == "Deposit":
            new_coffer = total + amount
            new_holding = max(current_holding - amount, 0)
            
            log_coffer_entry(user_id, name, "Deposit", amount, new_coffer, new_holding, current_owed)
            await interaction.response.send_message(f"{CURRENCY_SYMBOL} {name} deposited {format_million(amount)}!")
        else:
            new_coffer = total - amount
            
            log_coffer_entry(user_id, name, "Withdraw", -amount, new_coffer, current_holding, current_owed)
            await interaction.response.send_message(f"{CURRENCY_SYMBOL} {name} withdrew {format_million(amount)}!")

@bot.tree.command(name="deposit", description="Deposit money into the clan coffer")
async def deposit(interaction: discord.Interaction):
    await interaction.response.send_modal(DepositWithdrawModal("Deposit"))

@bot.tree.command(name="withdraw", description="Withdraw money from the clan coffer")
async def withdraw(interaction: discord.Interaction):
    await interaction.response.send_modal(DepositWithdrawModal("Withdraw"))

@bot.tree.command(name="holding", description="Add to a user's holding amount")
async def holding(interaction: discord.Interaction, amount: str, user: discord.User | None = None):
    target = user or interaction.user
    try:
        amt = parse_amount(amount)
    except Exception:
        await interaction.response.send_message("❌ Invalid format.", ephemeral=True)
        return

    total, holders, owed = get_current_total_and_holders_and_owed()
    new_holding = holders.get(target.name, 0) + amt
    current_owed = owed.get(target.name, 0)

    log_coffer_entry(target.id, target.name, "Holding Update", amt, total, new_holding, current_owed)
    await interaction.response.send_message(f"{CURRENCY_SYMBOL} **{target.name}** holding updated.")

@bot.tree.command(name="owed", description="Set a user's owed amount")
async def owed(interaction: discord.Interaction, amount: str, user: discord.User | None = None):
    target = user or interaction.user
    try:
        amt = parse_amount(amount)
    except Exception:
        await interaction.response.send_message("❌ Invalid format.", ephemeral=True)
        return

    total, holders, owed_dict = get_current_total_and_holders_and_owed()
    new_owed = owed_dict.get(target.name, 0) + amt
    current_holding = holders.get(target.name, 0)

    log_coffer_entry(target.id, target.name, "Owed Update", amt, total, current_holding, new_owed)
    await interaction.response.send_message(f"{CURRENCY_SYMBOL} **{target.name}** owed amount updated.")

@bot.tree.command(name="clear_owed", description="Clear owed amount for a user")
async def clear_owed(interaction: discord.Interaction, user: discord.User):
    total, holders, owed_dict = get_current_total_and_holders_and_owed()
    current_holding = holders.get(user.name, 0)
    
    log_coffer_entry(user.id, user.name, "Clear Owed", 0, total, current_holding, 0)
    await interaction.response.send_message(f"{CURRENCY_SYMBOL} Cleared owed amount for **{user.name}**.")

@bot.tree.command(name="clear_holding", description="Clear holding amount for a user")
async def clear_holding(interaction: discord.Interaction, user: discord.User):
    total, holders, owed_dict = get_current_total_and_holders_and_owed()
    current_owed = owed_dict.get(user.name, 0)

    log_coffer_entry(user.id, user.name, "Clear Holding", 0, total, 0, current_owed)
    await interaction.response.send_message(f"{CURRENCY_SYMBOL} Cleared holding for **{user.name}**.")

@bot.tree.command(name="bank", description="Show coffer total and who is holding or owed money")
async def bank(interaction: discord.Interaction):
    total, holders, owed = get_current_total_and_holders_and_owed()
    
    holder_lines = [f"🏦 **{name}** is holding {CURRENCY_SYMBOL} {format_million(amt)}" for name, amt in holders.items() if amt > 0]
    owed_lines = [f"💰 **{name}** is owed {CURRENCY_SYMBOL} {format_million(amt)}" for name, amt in owed.items() if amt > 0]

    bank_text = f"**{CURRENCY_SYMBOL} Main Bank:** {format_million(total)}\n**💰 Total Coffer:** {format_million(total + sum(holders.values()))}\n\n"
    bank_text += "\n".join(holder_lines) if holder_lines else "_Nobody is holding anything._"
    bank_text += "\n\n" + ("\n".join(owed_lines) if owed_lines else "_Nobody is owed anything._")

    await interaction.response.send_message(bank_text, ephemeral=False)

# ---------------------------
# 🔹 Collat Notifier
# ---------------------------

class CollatRequestModal(discord.ui.Modal, title="Request Item"):
    target_username = discord.ui.TextInput(label="Enter the username to notify", required=True)

    def __init__(self, parent_message: discord.Message, requester: discord.User):
        super().__init__()
        self.parent_message = parent_message
        self.requester = requester

    async def on_submit(self, interaction: discord.Interaction):
        target_member = discord.utils.find(lambda m: m.name == str(self.target_username.value).strip() or m.display_name == str(self.target_username.value).strip(), interaction.guild.members)
        if not target_member:
            await interaction.response.send_message("❌ User not found.", ephemeral=True)
            return

        await self.parent_message.reply(f"{self.requester.mention} is requesting their item from {target_member.mention}")
        await interaction.response.send_message("Request sent ✅", ephemeral=True)

async def get_original_message_actors(interaction: discord.Interaction):
    try:
        msg = await interaction.channel.fetch_message(interaction.message.reference.message_id)
        return msg, msg.author, next((m for m in msg.mentions if isinstance(m, (discord.Member, discord.User))), None)
    except:
        return None, None, None

class CollatButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Request Item", style=discord.ButtonStyle.primary, emoji="🔔", custom_id="collat:request_persistent")
    async def request_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg, author, mentioned = await get_original_message_actors(interaction)
        if not msg or interaction.user not in [author, mentioned]:
            return

        if not mentioned:
            await interaction.response.send_modal(CollatRequestModal(msg, interaction.user))
        else:
            await msg.reply(f"{interaction.user.mention} is requesting their item from {(mentioned if interaction.user == author else author).mention}.")
            await interaction.response.defer()

    @discord.ui.button(label="Item Returned", style=discord.ButtonStyle.success, emoji="📥", custom_id="collat:returned_persistent")
    async def item_returned(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg, author, mentioned = await get_original_message_actors(interaction)
        if not msg or interaction.user not in [author, mentioned]:
            return

        for child in self.children: child.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("Item marked as returned. ✅", ephemeral=True)

# ---------------------------
# 🔹 Panel Init
# ---------------------------

async def send_rsn_panel(channel: discord.TextChannel):
    await channel.purge(limit=10)
    await channel.send("📝 **Link your RSN by clicking below**", view=RSNPanelView())

async def send_combined_panels(channel: discord.TextChannel):
    await channel.purge(limit=20) 
    
    await channel.send("# 𝓣𝖎𝖒𝖊𝖟𝖔𝖓𝖊")
    await channel.send("🕒 𝓢𝖊𝖑𝖊𝖈𝖙 𝓨𝖔𝖚𝖗 𝓣𝖎𝖒𝖊𝖟𝖔𝖓𝖊", view=TimezoneView(channel.guild))
    
    await channel.send("# 𝕭𝖔𝖘𝖘 𝕽𝖔𝖑𝖊𝖘")
    await channel.send("**𝕽𝖆𝖎𝖉𝖘**", view=RaidsView(channel.guild))
    await channel.send("**𝕭𝖔𝖘𝖘𝖊𝖘**", view=BossesView(channel.guild))
    await channel.send("**𝕰𝖛𝖊𝖓𝖙𝖘**", view=EventsView(channel.guild))
    await channel.send("**𝕺𝖙𝖍𝖊𝖗 𝕽𝖔𝖑𝖊𝖘**", view=OtherRolesView(channel.guild))
    await channel.send("# 𝕮𝖔𝖑𝖔𝖗𝖘")
    await channel.send("**Select a Color Role:**\n*(Selecting a new color will automatically remove your old one)*", view=ColorPanelView())

# ---------------------------
# 🔹 Bot Events
# ---------------------------
@bot.tree.command(name="setup_panels", description="Deploy all interactive panels to their respective channels.")
@app_commands.checks.has_any_role("Administrators")
async def setup_panels(interaction: discord.Interaction):
    await interaction.response.send_message("Deploying all panels... this may take a moment.", ephemeral=True)
    
    # 1. RSN Panel
    if rsn_channel := bot.get_channel(RSN_CHANNEL_ID): 
        await send_rsn_panel(rsn_channel)
        
    # 2. Combined Boss Roles, Timezones & Colors Panel
    if combined_channel := bot.get_channel(ROLE_CHANNEL_ID): 
        await send_combined_panels(combined_channel)

    # 3. Vanity Rank Panel
    if vanity_channel := bot.get_channel(VANITY_CHANNEL_ID):
        await vanity_channel.purge(limit=20)
        
        rank_data = [
            ("<:seren:1519259305658814474>", "Serenist", "New members who want to (learn) pvm."),
            ("<:dogsbody:1528781938348003490>", "Dogsbody", "New members who are here for vibes and community without focus on pvm."),
            ("<:recruit:1528782491609993236>", "Recruit", "Combat 80 + Dragon Gloves, Dragon Defender."),
            ("<:pawn:1528782545515450408>", "Pawn", "Combat 90 + Barrow Gloves, Regular Void, Medium CAs."),
            ("<:corporal:1528782001128341534>", "Corporal", "Combat 100 + Elite Void, Piety, Fire Cape."),
            ("<:novice:1528782606500364369>", "Novice", "Combat 110 + Upgraded Runepouch, Hard CA's."),
            ("<:sergeant:1528782656098009249>", "Sergeant", "Combat 120 + Quiver *or* Infernal Cape, Elite CA's."),
            ("<:marshall:1528782872851517540>", "Marshall", "Combat 122 + Quiver *and* Infernal Cape, Master CA's."),
            ("<:tzkal:1528782733457752155>", "TzKal", "Grandmaster CA's"),
            ("<:hellcat:1528782783718228181>", "Pet Hunter", "Pet rank that requires a minimum total of 20 pets obtained."),
            ("<:coordinator:1519037196974424194>", "Collection Logger", "Must have filled 1000 collection log slots."),
            ("<:skiller:1519037750748119252>", "Skiller", "Take this rank if you primarily do skilling."),
            ("<:maxed:1519037333796814978>", "Maxed", "Take this rank if you're 2376 total level\n*(will be removed if you're not)*."),
        ]

        rank_colors = [
            (184, 249, 249), (190, 249, 241), (196, 249, 233), (203, 249, 225),
            (209, 249, 217), (216, 249, 209), (222, 249, 201), (229, 249, 193),
            (235, 250, 185), (242, 250, 177), (248, 250, 168), (255, 250, 160),
            (255, 235, 150), (255, 220, 140), (255, 205, 130), (255, 190, 120),
            (255, 175, 110), (255, 160, 100), (255, 145, 90)
        ]

        rank_embeds = [
            discord.Embed(
                title=f"{emoji}  {name}", 
                description=description, 
                color=discord.Color.from_rgb(*rank_colors[i])
            )
            for i, (emoji, name, description) in enumerate(rank_data)
        ]

        await vanity_channel.send(embeds=rank_embeds[:10])

        header_embed = discord.Embed(
            title="⚔️ Apply for Ranks",
            description="Click a button below to open a ticket and submit proof for a specific rank, or instantly toggle non-ticket roles.",
            color=discord.Color.from_rgb(184, 249, 249)
        )
        
        final_embeds = rank_embeds[10:] + [header_embed]
        await vanity_channel.send(embeds=final_embeds, view=VanityView(interaction.guild))

    # 4. Learner Panel
    if learner_channel := bot.get_channel(LEARNER_CHANNEL_ID):
        await learner_channel.purge(limit=10)
        
        learner_embed = discord.Embed(
            title="📚 Learner & Mentor Requests", 
            description="Looking to learn a raid? Click the corresponding button below to fill out a request form. A mentor will be pinged and will assist you in a private thread as soon as they are available.",
            color=discord.Color.from_rgb(184, 249, 249)
        )
        learner_embed.add_field(
            name="⚠️ Gear Requirements",
            value="Before applying, please ensure your gear meets the minimum requirements found here:\nhttps://discord.com/channels/1517374163655065631/1519831937575944243",
            inline=False
        )
        await learner_channel.send(embed=learner_embed, view=LearnerTicketView(interaction.guild))

    # 5. Support Panel
    if support_channel := bot.get_channel(TICKET_CHANNEL_ID):
        await support_channel.purge(limit=10)
        
        support_embed = discord.Embed(
            title="🆘 Support Center", 
            description="Need assistance from the administration team? Open a private support ticket and we will help you as soon as we are available.",
            color=discord.Color.from_rgb(43, 45, 49)
        )
        support_embed.add_field(
            name="📌 What can we help with?",
            value="• **Questions:** General inquiries about the clan or systems.\n• **Reports:** Reporting a player for breaking rules or toxic behavior.\n• **Coffer/Bank:** Issues or questions regarding clan wealth and payouts.\n• **Roles:** Requesting missing roles or name updates.",
            inline=False
        )
        support_embed.add_field(
            name="⏳ Response Time",
            value="Admins are in various timezones. Please be patient after opening your ticket and provide as much detail as possible.",
            inline=False
        )
        support_embed.set_footer(text="Obscurity Admin Team • Please don't misuse the ticket system and refrain from messaging admins directly.")
        
        await support_channel.send(embed=support_embed, view=SupportTicketView())

    # 6. Welcome Panel
    if welcome_channel := bot.get_channel(WELCOME_CHANNEL_ID):
        await welcome_channel.purge(limit=10)
        
        welcome_embed = discord.Embed(
            title="✨ Apply to Join Obscurity ✨", 
            description="We are thrilled that you're interested in joining our community! To start your application process, please click the 'Join' button below.",
            color=discord.Color.from_rgb(184, 249, 249)
        )
        welcome_embed.add_field(
            name="👥 Our Community",
            value="We uphold a welcoming and positive environment.\n\nThose that value these things might find this community to be the place they have been looking for, and we intend to keep it that way.\n\nWe hold our values and what we do to as high a standard as reasonably possible - we only ask that our members do the same.\n\nThat being said, please follow our rules. Knowingly breaking them will be cause for removal from the clan.",
            inline=False
        )
        welcome_embed.add_field(
            name="🎒 Requirements",
            value="To join the clan you should be friendly and positive. The main items we'll ask for are basic PvM gear.\n\nYou can use the image below as a rough estimate - though you should have full tribrid gear of *some* kind.",
            inline=False
        )
        welcome_embed.add_field(
            name="⚠️ Before You Apply",
            value="Please ensure you have read the server rules here: https://discord.com/channels/1517374163655065631/1517389459459538994.",
            inline=False
        )
        welcome_embed.set_image(url="https://i.postimg.cc/rw0nvj1K/Sprite-0002.png")
        welcome_embed.set_footer(text="Join Obscurity • Click the button below to begin")
        
        await welcome_channel.send(embed=welcome_embed, view=WelcomeTicketView())

    await interaction.followup.send("✅ All panels have been successfully deployed!", ephemeral=True)

@bot.tree.command(name="color_panel", description="Post the color role selection panel.")
@app_commands.checks.has_any_role("Administrators")
async def post_color_panel(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("Posting color panel...", ephemeral=True)
    await interaction.channel.send("**Select a Color Role:**\n*(Selecting a new color will automatically remove your old one)*", view=ColorPanelView())

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot: return
    await bot.process_commands(message)

    if message.channel.id == COLLAT_CHANNEL_ID:
        if (message.attachments or any(embed.image for embed in message.embeds)) and not message.reference:
            await message.reply("Collat actions:", view=CollatButtons(), allowed_mentions=discord.AllowedMentions.none())

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if after.bot or before.roles == after.roles: return

    # --- Existing Inactive Role Logic ---
    inactive_role = discord.utils.get(after.guild.roles, id=INACTIVE_ROLE_ID)
    if inactive_role and inactive_role in (set(after.roles) - set(before.roles)):
        try:
            await after.send(f"Hey {after.display_name}! You've been marked inactive in Obscurity. Rejoin anytime!")
        except:
            pass

    # --- New Promotion Logic ---
    # Helper function to find the user's highest current progression rank
    def get_highest_rank(member: discord.Member):
        for rank in reversed(RANK_HIERARCHY):
            if discord.utils.get(member.roles, name=rank):
                return rank
        return None

    old_rank = get_highest_rank(before)
    new_rank = get_highest_rank(after)

    if old_rank and new_rank and old_rank != new_rank:
        if RANK_HIERARCHY.index(new_rank) > RANK_HIERARCHY.index(old_rank):
            
            channel = after.guild.get_channel(PROMOTION_CHANNEL_ID)
            if channel:
                old_emoji = RANK_EMOJIS[old_rank]
                new_emoji = RANK_EMOJIS[new_rank]
                
                message_text = (
                    f"🎊 **Promotion!** 🎊\n"
                    f"Congratulations to {after.mention} on the new rank!\n"
                    f"> {old_emoji} ➜ {new_emoji}"
                )
                
                await channel.send(message_text)

@bot.event
async def on_ready():
    global has_synced
    print(f"✅ Logged in as {bot.user}")

    if not has_synced:
        try:
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            has_synced = True
        except Exception as e:
            print(f"❌ Command sync failed: {e}")
    
    bot.add_view(TicketControlView())
    bot.add_view(RSNPanelView())
    bot.add_view(CollatButtons())
    bot.add_view(WelcomeTicketView())
    bot.add_view(SupportTicketView())
    bot.add_view(TimezoneView(bot.get_guild(GUILD_ID)))
    bot.add_view(SupportTicketView())
    bot.add_view(LearnerTicketView())
    
    guild = bot.get_guild(GUILD_ID)
    if guild: 
        if bot.get_channel(ROLE_CHANNEL_ID): 
            bot.add_view(RaidsView(guild))
            bot.add_view(BossesView(guild))
            bot.add_view(EventsView(guild))    
            bot.add_view(OtherRolesView(guild))
        if bot.get_channel(ROLE_CHANNEL_ID): 
            bot.add_view(TimezoneView(guild))
        if bot.get_channel(VANITY_CHANNEL_ID):
            bot.add_view(VanityView(guild))
        bot.add_view(LearnerTicketView())
        bot.add_view(WelcomeBaseRoleView(guild))
    asyncio.create_task(rsn_writer())
        
async def main():
    async with bot:
        cogs_to_load = ["Obscure"]
        for cog_name in cogs_to_load:
            try:
                await bot.load_extension(cog_name)
                print(f"✅ Successfully loaded extension: {cog_name}")
            except Exception as e:
                print(f"🔥 Failed to load extension {cog_name}.")
                print(f"  Error: {e}")
                
        bot_token = os.getenv('DISCORD_TOKEN')
        if bot_token:
            await bot.start(bot_token)
        else:
            print("❌ Token missing.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
