"""Commands specific to development. Only approved developers can use these commands."""
import copy

import discord
from discord.ext.commands import NotOwner
from loguru import logger

from lilybot.context import LilyBotContext
from ._utils import *


class Development(Cog):
    """
    Commands useful for developing the bot.
    These commands are restricted to bot developers.
    """
    eval_globals = {}
    for module in ('asyncio', 'collections', 'discord', 'inspect', 'itertools'):
        eval_globals[module] = __import__(module)
    eval_globals['__builtins__'] = __import__('builtins')

    def cog_check(self, ctx: LilyBotContext):  # All of this cog is only available to devs
        if ctx.author.id not in ctx.bot.config['developers']:
            raise NotOwner('you are not a developer!')
        return True

    @command()
    async def reload(self, ctx: LilyBotContext, cog: str):
        """Reloads a cog."""
        extension = 'lilybot.cogs.' + cog
        msg = await ctx.send('Reloading extension %s' % extension)
        await self.bot.reload_extension(extension)
        await msg.edit(content='Reloaded extension %s' % extension)

    reload.example_usage = """
    `{prefix}reload development` - reloads the development cog
    """

    @command(name='su', pass_context=True)
    async def pseudo(self, ctx: LilyBotContext, user: discord.Member, *, command: str):
        """Execute a command as another user."""
        msg = copy.copy(ctx.message)
        msg.author = user
        msg.content = command
        context = await self.bot.get_context(msg)
        context.is_pseudo = True  # adds new flag to bypass ratelimit
        # let's also add a log of who ran pseudo
        logger.info(
            f"Running pseudo on request of {ctx.author} ({ctx.author.id}) in '{ctx.guild}' #{ctx.channel}:")
        logger.info("-" * 32)
        logger.info(ctx.message.content)
        logger.info("-" * 32)
        await self.bot.invoke(context)

    pseudo.example_usage = """
    `{prefix}su cooldude#1234 {prefix}ping` - simulate cooldude sending `{prefix}ping`
    """


async def setup(bot):
    """Adds the development cog to the bot."""
    await bot.add_cog(Development(bot))
