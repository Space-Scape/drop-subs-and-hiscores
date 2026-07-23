import os
import discord
from discord.ext import commands
from datetime import datetime
from discord import app_commands

LOG_CHANNEL_ID = 1520357794904019065
MESSAGE_LOG_CHANNEL_ID = 1520357794904019065 

def format_dt(dt):
    """Formats a datetime object into a standard string."""
    return dt.strftime("%m/%d/%Y %I:%M %p")

async def send_log(guild: discord.Guild, embed: discord.Embed, channel_id: int = LOG_CHANNEL_ID):
    """Sends an embed to the designated log channel."""
    log_channel = guild.get_channel(channel_id)
    if log_channel:
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            print(f"Missing permissions to send log in guild: {guild.id} to channel {channel_id}")
        except discord.HTTPException as e:
            print(f"Failed to send log: {e}")

class Obscurity(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Obscurity Logger has been loaded and is ready.")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        added_roles = [r for r in after.roles if r not in before.roles]
        for role in added_roles:
            embed = discord.Embed(title=":white_check_mark: Role Added to User", color=discord.Color.green(), timestamp=datetime.utcnow())
            embed.add_field(name="User", value=f"{after.display_name} ({after}) | {after.id}", inline=False)
            embed.add_field(name="Role", value=role.mention, inline=False)
            await send_log(after.guild, embed)
        removed_roles = [r for r in before.roles if r not in after.roles]
        for role in removed_roles:
            embed = discord.Embed(title=":x: Role Removed from User", color=discord.Color.red(), timestamp=datetime.utcnow())
            embed.add_field(name="User", value=f"{after.display_name} ({after}) | {after.id}", inline=False)
            embed.add_field(name="Role", value=role.mention, inline=False)
            await send_log(after.guild, embed)
        if before.nick != after.nick:
            embed = discord.Embed(title=":pencil: Nickname Changed", color=discord.Color.orange(), timestamp=datetime.utcnow())
            embed.add_field(name="User", value=f"{after.display_name} ({after}) | {after.id}", inline=False)
            embed.add_field(name="Old Nickname", value=before.nick or "*None*", inline=True)
            embed.add_field(name="New Nickname", value=after.nick or "*None*", inline=True)
            await send_log(after.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.content == after.content or not before.guild:
            return

        old_content = before.content if before.content else "*no content*"
        if len(old_content) > 1024:
            old_content = old_content[:1020] + "..."

        new_content = after.content if after.content else "*no content*"
        if len(new_content) > 1024:
            new_content = new_content[:1020] + "..."

        embed = discord.Embed(title=":pencil: Message Updated", color=discord.Color.gold(), timestamp=datetime.utcnow())
        embed.add_field(name="Old Message", value=old_content, inline=False)
        embed.add_field(name="New Message", value=new_content, inline=False)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Author", value=f"{before.author.display_name} ({before.author}) | {before.author.id}", inline=True)
        await send_log(before.guild, embed, MESSAGE_LOG_CHANNEL_ID)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        del_content = message.content if message.content else "*no content*"
        if len(del_content) > 1024:
            del_content = del_content[:1020] + "..."

        embed = discord.Embed(title=":wastebasket: Message Deleted", color=discord.Color.dark_red(), timestamp=datetime.utcnow())
        embed.add_field(name="Deleted Message", value=del_content, inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Author", value=f"{message.author.display_name} ({message.author}) | {message.author.id}", inline=True)
        await send_log(message.guild, embed, MESSAGE_LOG_CHANNEL_ID)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = discord.Embed(title=":wave: Member Joined", color=discord.Color.green(), timestamp=datetime.utcnow())
        embed.add_field(name="User", value=f"{member.display_name} ({member}) | {member.id}", inline=False)
        embed.add_field(name="Account Created", value=format_dt(member.created_at), inline=False)
        await send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        entry = None
        try:
            async for log in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                if log.target.id == member.id and (datetime.utcnow() - log.created_at).total_seconds() < 5:
                    entry = log
                    break
        except discord.Forbidden: pass

        embed = discord.Embed(timestamp=datetime.utcnow())
        embed.add_field(name="User", value=f"{member.display_name} ({member}) | {member.id}", inline=False)

        if entry:
            embed.title = ":anger: Member Kicked"
            embed.color = discord.Color.dark_red()
            embed.add_field(name="By", value=f"{entry.user.display_name} ({entry.user})", inline=False)
            embed.add_field(name="Reason", value=entry.reason or "*No reason provided*", inline=False)
        else:
            embed.title = ":saluting_face: Member Left"
            embed.color = discord.Color.red()
        await send_log(guild, embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot: return

        embed = discord.Embed(timestamp=datetime.utcnow())
        user_val = f"{member.display_name} ({member}) | {member.id}"

        if before.channel is None and after.channel is not None:
            embed.title, embed.color = ":microphone2: Voice Channel Joined", discord.Color.green()
            embed.add_field(name="User", value=user_val, inline=False)
            embed.add_field(name="Channel", value=after.channel.mention, inline=False)
            await send_log(member.guild, embed)
        elif before.channel is not None and after.channel is None:
            embed.title, embed.color = ":mute: Voice Channel Left", discord.Color.red()
            embed.add_field(name="User", value=user_val, inline=False)
            embed.add_field(name="Channel", value=before.channel.mention, inline=False)
            await send_log(member.guild, embed)
        elif before.channel and after.channel and before.channel != after.channel:
            embed.title, embed.color = ":arrow_right_hook: Voice Channel Switched", discord.Color.blue()
            embed.add_field(name="User", value=user_val, inline=False)
            embed.add_field(name="Old Channel", value=before.channel.mention, inline=True)
            embed.add_field(name="New Channel", value=after.channel.mention, inline=True)
            await send_log(member.guild, embed)



    @app_commands.command(name="scrape_id", description="Scrape all non-bot Discord user IDs to a text file.")
    async def scrape_id(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("❌ Could not resolve your server membership.", ephemeral=True)
            return

        has_moderator_role = any(role.name == "Administrators" for role in member.roles)
        perms = member.guild_permissions
        has_admin_permission = perms.administrator
        has_manage_guild_permission = perms.manage_guild
        is_guild_owner = member.id == interaction.guild.owner_id

        if not any((has_moderator_role, has_admin_permission, has_manage_guild_permission, is_guild_owner)):
            await interaction.response.send_message(
                "❌ You do not have permission. Requires Moderators role, Manage Server, Administrator, or server ownership.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        ids = [str(m.id) for m in interaction.guild.members if not m.bot]
        filename = f"member_ids_{interaction.guild.id}.txt"
        with open(filename, "w") as f:
            f.write("\n".join(ids))

        try:
            await interaction.followup.send(
                content=f"✅ Scraped {len(ids)} member IDs.",
                file=discord.File(filename),
            )
        finally:
            if os.path.exists(filename):
                os.remove(filename)
    
    @commands.command(name="export_ids")
    async def export_ids(self, ctx: commands.Context):
        if not any(role.name == "Administators" for role in ctx.author.roles):
            await ctx.send("❌ You do not have permission.", delete_after=5)
            return
        await ctx.typing()
        ids = [str(m.id) for m in ctx.guild.members if not m.bot]
        filename = f"member_ids_{ctx.guild.id}.txt"
        with open(filename, "w") as f: f.write("\n".join(ids))
        await ctx.send(f"✅ Exported {len(ids)} member IDs.", file=discord.File(filename))
        os.remove(filename)

async def setup(bot: commands.Bot):
    await bot.add_cog(Obscurity(bot))
