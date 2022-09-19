import random
from datetime import datetime, timedelta

import discord
from discord.ext.commands import guild_only, has_permissions
from discord.ext.tasks import loop

from ._utils import *
from .. import db


class QOTD(Cog):
    """Sends a daily question in a channel"""

    def __init__(self, bot):
        self.send_questions.start()
        super().__init__(bot)

    @loop(minutes=1)
    async def send_questions(self):
        """Send a question to all enabled channels"""
        if datetime.now().hour != 12 or datetime.now().minute != 0:
            return
        async with db.Pool.acquire() as conn:
            questions = await conn.fetch(f"""
                                         SELECT * FROM {QOTDQuestion.__tablename__}
                                         WHERE used_at < $1;""", (datetime.now() - timedelta(days=2)).timestamp())

        channels = await QOTDChannel.get_by(enabled=True)
        if not questions:
            for channel in channels:
                discord_channel = await self.bot.fetch_channel(channel.channel_id)
                await discord_channel.send(embed=discord.Embed(title="No questions have been added yet!", color=discord.Color.red()))
        else:
            question = random.choice(questions)
            async with db.Pool.acquire() as conn:
                await conn.execute(f"""
                                    UPDATE {QOTDQuestion.__tablename__}
                                    SET used_at = $1
                                    WHERE question_id = $2;""", datetime.now().timestamp(), question.get("question_id"))
            for channel in channels:
                discord_channel = await self.bot.fetch_channel(channel.channel_id)
                await discord_channel.send(f"{question.get('question')}")

    @send_questions.before_loop
    async def before_sync(self):
        """Do preparation work before starting the periodic timer to sync cache with the database."""
        await self.bot.wait_until_ready()

    def cog_unload(self):
        """Detach from the running bot and cancel long-running code as the cog is unloaded."""
        self.send_questions.stop()

    @group(name="qotd", invoke_without_command=True)
    @has_permissions(manage_messages=True)
    @guild_only()
    async def qotd_group(self, ctx):
        """Manages questions of the day"""
        results = await QOTDQuestion.get_by(guild_id=ctx.guild.id)
        if not results:
            embed = discord.Embed(title="Questions for {}".format(ctx.guild.name))
            embed.set_thumbnail(url=ctx.guild.icon_url)
            embed.description = "No questions found for this guild! Add one using `{}qotd add <question>}`".format(
                ctx.prefix)
            embed.colour = discord.Color.red()
            await ctx.send(embed=embed)
            return
        else:
            fmt = 'ID {0.question_id}: `{0.question}`'

            filter_text = '\n'.join(map(fmt.format, results))
            embed = discord.Embed(title=f"Questions for {ctx.guild.name}")
            embed.set_thumbnail(url=ctx.guild.icon_url)
            if len(filter_text) > 1024:
                embed.description = filter_text
            else:
                embed.add_field(name="Questions", value=filter_text)
            embed.colour = discord.Color.dark_orange()
            await ctx.send(embed=embed)

    @qotd_group.command(name="channels", aliases=["config"])
    @has_permissions(manage_messages=True)
    @guild_only()
    async def qotd_channels(self, ctx):
        results = await QOTDChannel.get_by(guild_id=ctx.guild.id, enabled=True)
        if not results:
            embed = discord.Embed(title="Channels for {}".format(ctx.guild.name))
            embed.set_thumbnail(url=ctx.guild.icon_url)
            embed.description = "No Channels found for this guild! Add one using `{}qotd channeladd #channel`".format(
                ctx.prefix)
            embed.colour = discord.Color.red()
            await ctx.send(embed=embed)
            return
        else:
            fmt = '#<{0.channel_id}>'

            filter_text = '\n'.join(map(fmt.format, results))
            embed = discord.Embed(title=f"Channels for {ctx.guild.name}")
            embed.set_thumbnail(url=ctx.guild.icon_url)
            if len(filter_text) > 1024:
                embed.description = filter_text
            else:
                embed.add_field(name="Channels", value=filter_text)
            embed.colour = discord.Color.dark_orange()
            await ctx.send(embed=embed)

    @qotd_group.command(name="disable", aliases=["off", "stop"])
    @has_permissions(manage_messages=True)
    @guild_only()
    async def qotd_disable(self, ctx):
        """Disables the qotd"""
        results = await QOTDChannel.get_by(guild_id=ctx.guild.id, enabled=True)
        if not results:
            await ctx.send(embed=discord.Embed(title="QOTD is not enabled for this server", color=discord.Color.red()))
        else:
            for result in results:
                result.enabled = False
                await result.update_or_add()
            await ctx.send(
                embed=discord.Embed(title="QOTD has been disabled for this server", color=discord.Color.orange()))

    @qotd_group.command(name="channeladd", aliases=['set'])
    @has_permissions(manage_messages=True)
    @guild_only()
    async def qotd_channel_add(self, ctx, channel: discord.TextChannel):
        """Sets the channel for the qotd"""
        results = await QOTDChannel.get_by(guild_id=ctx.guild.id, channel_id=channel.id, enabled=True)
        if results:
            await ctx.send(
                embed=discord.Embed(title=f"QOTD is already enabled for #<{channel.id}>", color=discord.Color.red()))
        else:
            await QOTDChannel(guild_id=ctx.guild.id, channel_id=channel.id, enabled=True).update_or_add()
            await ctx.send(embed=discord.Embed(title=f"QOTD has been enabled for #<{channel.id}>",
                                               color=discord.Color.green()))

    @qotd_group.command(name="add", aliases=["create", "new"])
    @has_permissions(manage_messages=True)
    @guild_only()
    async def qotd_add(self, ctx, *, question: str):
        """Adds a new question"""
        if len(question) > 128:
            embed = discord.Embed(title="Question too long")
            embed.set_thumbnail(url=ctx.guild.icon_url)
            embed.description = "The question must be less than 128 characters"
            embed.colour = discord.Color.red()
            await ctx.send(embed=embed)
            return
        else:
            await QOTDQuestion(guild_id=ctx.guild.id, question=question).update_or_add()
            embed = discord.Embed(title="Question added")
            embed.set_thumbnail(url=ctx.guild.icon_url)
            embed.description = "The question has been added"
            embed.add_field(name="Question:", value=question)
            embed.colour = discord.Color.green()
            await ctx.send(embed=embed)

    @qotd_group.command(name="remove", aliases=["delete"])
    @has_permissions(manage_messages=True)
    @guild_only()
    async def qotd_remove(self, ctx, question_id: int):
        trigger = await QOTDQuestion.get_by(question_id=question_id, guild_id=ctx.guild.id)
        if trigger:
            await QOTDQuestion.delete(question_id=question_id)
            await ctx.send("Question removed!")
        else:
            await ctx.send("Question not found!")


class QOTDQuestion(db.DatabaseTable):
    """Keeps track of all the questions and when they were last used"""
    __tablename__ = "lily_qotd_questions"
    __uniques__ = "question_id"

    @classmethod
    async def initial_create(cls):
        """Create the table in the database"""
        async with db.Pool.acquire() as conn:
            await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {cls.__tablename__} (
            question_id serial PRIMARY KEY NOT NULL,
            guild_id bigint NOT NULL,
            question varchar NOT NULL,
            used_at bigint NOT NULL
            )""")

    def __init__(self, guild_id: int, question: str, used_at=0, question_id: int = None, ):
        super().__init__()
        self.question_id = question_id
        self.guild_id = guild_id
        self.question = question
        self.used_at = used_at

    @classmethod
    async def get_by(cls, **kwargs):
        results = await super().get_by(**kwargs)
        result_list = []
        for result in results:
            obj = QOTDQuestion(guild_id=result.get("guild_id"),
                               question=result.get("question"),
                               question_id=result.get('question_id'), used_at=result.get('used_at'))
            result_list.append(obj)
        return result_list


class QOTDChannel(db.DatabaseTable):
    """Holds the channels in which to send a daily question"""
    __tablename__ = 'lily_qotd_channels'
    __uniques__ = 'channel_id'

    @classmethod
    async def initial_create(cls):
        """Creates the table in the database"""
        async with db.Pool.acquire() as conn:
            await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {cls.__tablename__} (
            channel_id bigint PRIMARY KEY NOT NULL,
            guild_id bigint NOT NULL,
            enabled boolean NOT NULL DEFAULT true
            )""")

    def __init__(self, guild_id: int, channel_id: int, enabled: bool = True):
        super().__init__()
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.enabled = enabled

    @classmethod
    async def get_by(cls, **kwargs):
        results = await super().get_by(**kwargs)
        result_list = []
        for result in results:
            obj = QOTDChannel(guild_id=result.get("guild_id"),
                              channel_id=result.get("channel_id"),
                              enabled=result.get('enabled'))
            result_list.append(obj)
        return result_list


async def setup(bot):
    """Add the levels cog to a bot."""
    await bot.add_cog(QOTD(bot))
