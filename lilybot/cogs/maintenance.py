"""Maintenance commands for bot developers"""
from loguru import logger
import os

import discord
from discord.ext.commands import NotOwner

from ._utils import *


class Maintenance(Cog):
    """
    Commands for performing maintenance on the bot.
    These commands are restricted to bot developers.
    """

    def cog_check(self, ctx):  # All of this cog is only available to devs
        if ctx.author.id not in ctx.bot.config['developers']:
            raise NotOwner('You are not a developer!')
        return True

    @command()
    async def shutdown(self, ctx):
        """Force-stops the bot."""
        await ctx.send(embed=discord.Embed(title='Shutting down', color=discord.Color.red()))
        logger.info('Shutting down at request of {}#{} (in {}, #{})'.format(ctx.author.name,
                                                                            ctx.author.discriminator,
                                                                            ctx.guild.name,
                                                                            ctx.channel.name))
        await self.bot.shutdown()

    shutdown.example_usage = """
    `{prefix}shutdown` - stop the bot
    """

    @command()
    async def restart(self, ctx):
        """Restarts the bot."""
        await ctx.send(embed=discord.Embed(title='Restarting', color=discord.Color.red()))
        await self.bot.shutdown(restart=True)

    restart.example_usage = """
    `{prefix}restart` - restart the bot
    """

    @command()
    async def update(self, ctx):
        """
        Pulls code from GitHub and restarts.
        This pulls from whatever repository `origin` is linked to.
        If there are changes to download, and the download is successful, the bot restarts to apply changes.
        """
        res = os.popen("git pull").read()
        if res.startswith('Already up to date.'):
            await ctx.send(embed=discord.Embed(description='```\n' + res + '```', color=discord.Color.orange()))
        else:
            await ctx.send(embed=discord.Embed(title="Updated", description='```\n' + res + '```',
                                               color=discord.Color.orange()))
            await ctx.bot.get_command('restart').callback(self, ctx)

    update.example_usage = """
    `{prefix}update` - update to the latest commit and restart
    """


async def setup(bot):
    """Adds the maintenance cog to the bot process."""
    await bot.add_cog(Maintenance(bot))
