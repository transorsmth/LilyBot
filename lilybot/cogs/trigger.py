import asyncio
import random
import re

import discord
from discord.ext.commands import has_permissions, guild_only

from ._utils import *
from .. import db
from ..components import detect_keysmash


class Trigger(Cog):
    """Manages triggers similar to carl bot"""

    @Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        results = await TriggerResponseRecords.get_by(guild_id=message.guild.id)
        for trigger in results:
            if re.search(trigger.trigger, message.content):
                await asyncio.sleep(0.5)
                if trigger.embed:
                    await message.channel.send(embed=discord.Embed(title=trigger.response))
                    return
                else:
                    await message.channel.send(trigger.response)
                    return
        if message.guild.id == 983814962822660176:
            if detect_keysmash.is_keysmash(message.content) and message.guild.get_role(
                    983824647856472154) in message.author.roles:
                choices = ["good girl", 'cutie', 'sweetheart']

                nsfw_choices = ['good bottom', ';)', 'hottie', 'adorable']
                # nsfw category ID:
                if message.channel.category_id == 983817576616460328:
                    choices.extend(nsfw_choices)
                await asyncio.sleep(0.2)
                await message.channel.send(random.choice(choices))

    @group(name="trigger", aliases=["triggers"], invoke_without_command=True)
    @has_permissions(manage_messages=True)
    @guild_only()
    async def trigger_group(self, ctx):
        """Manages triggers"""
        results = await TriggerResponseRecords.get_by(guild_id=ctx.guild.id)
        if not results:
            embed = discord.Embed(title="Triggers for {}".format(ctx.guild.name))
            embed.set_thumbnail(url=ctx.guild.icon_url)
            embed.description = "No triggers found for this guild! Add one using `{}trigger add <trigger> <response>`".format(
                ctx.prefix)
            embed.colour = discord.Color.red()
            await ctx.send(embed=embed)
            return
        else:
            fmt = 'ID {0.id}: `{0.trigger}`, ({0.embed}), {0.response}'

            filter_text = '\n'.join(map(fmt.format, results))
            embed = discord.Embed(title=f"Triggers for {ctx.guild.name}")
            embed.set_thumbnail(url=ctx.guild.icon_url)
            if len(filter_text) > 1024:
                embed.description = filter_text
            else:
                embed.add_field(name="Triggers", value=filter_text)
            embed.colour = discord.Color.dark_orange()
            await ctx.send(embed=embed)

    trigger_group.example_usage = """
    `{prefix}trigger` - Lists all the triggers in the current server
    `{prefix}trigger add hello hi! how are you?` - adds the response "hi! how are you?" for the trigger "hello"
    `{prefix}trigger remove 12` - removes the trigger with an id of 12
    """

    trigger_group.example_usage = """
    `{prefix}trigger` - Lists all the triggers in the current server
    `{prefix}trigger add hello hi! how are you?` - adds the response "hi! how are you?" for the trigger "hello"
    `{prefix}trigger remove 12` - removes the trigger with an id of 12
    """

    @trigger_group.command(name="add", aliases=["create", "new"])
    @has_permissions(manage_messages=True)
    @guild_only()
    async def trigger_add(self, ctx, embed: bool, regex: str, *, response: str):
        """Adds a new trigger"""
        if len(regex) > 100:
            await ctx.send("Trigger is too long!")
            return
        if len(response) > 1024:
            await ctx.send("Response is too long!")
            return
        if not await TriggerResponseRecords.get_by(trigger=regex, guild_id=ctx.guild.id):
            database_object = TriggerResponseRecords(trigger=regex, response=response, guild_id=ctx.guild.id,
                                                     embed=embed)
            await database_object.update_or_add()
            await ctx.send("Trigger added!")
        else:
            await ctx.send("Trigger already exists!")

    @trigger_group.command(name="remove", aliases=["delete"])
    @has_permissions(manage_messages=True)
    @guild_only()
    async def trigger_remove(self, ctx, trigger_id: int):
        """Removes a trigger"""
        trigger = await TriggerResponseRecords.get_by(trigger_id=trigger_id, guild_id=ctx.guild.id)
        if trigger:
            await TriggerResponseRecords.delete(trigger_id=trigger_id)
            await ctx.send("Trigger removed!")
        else:
            await ctx.send("Trigger not found!")


class TriggerResponseRecords(db.DatabaseTable):
    """Trigger Records"""

    __tablename__ = 'lily_trigger_responses'
    __uniques__ = 'trigger_id'

    @classmethod
    async def initial_create(cls):
        """Create the table in the database"""
        async with db.Pool.acquire() as conn:
            await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {cls.__tablename__} (
            trigger_id serial PRIMARY KEY NOT NULL,
            guild_id bigint NOT NULL,
            trigger varchar NOT NULL,
            response varchar NOT NULL,
            embed boolean NOT NULL DEFAULT false
            )""")

    def __init__(self, guild_id: int, trigger: str, response: str, embed: bool, trigger_id: int = None):
        super().__init__()
        self.id = trigger_id
        self.guild_id = guild_id
        self.trigger = trigger
        self.response = response
        self.embed = embed

    @classmethod
    async def get_by(cls, **kwargs):
        results = await super().get_by(**kwargs)
        result_list = []
        for result in results:
            obj = TriggerResponseRecords(guild_id=result.get("guild_id"),
                                         trigger=result.get("trigger"),
                                         response=result.get("response"),
                                         trigger_id=result.get('trigger_id'),
                                         embed=result.get('embed'))
            result_list.append(obj)
        return result_list

    async def version_1(self):
        """DB migration v1"""
        async with db.Pool.acquire() as conn:
            await conn.execute(f"""
            ALTER TABLE {self.__tablename__}
            ADD embed boolean NOT NULL DEFAULT false;
            """)

    __versions__ = [version_1]


async def setup(bot):
    """Add the levels cog to a bot."""
    await bot.add_cog(Trigger(bot))
