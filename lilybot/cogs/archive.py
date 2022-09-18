import discord

from ._utils import *


class Archive(Cog):
    @command()
    async def archivetest(self, ctx, *, channel: discord.TextChannel):
        """Archives a channel to another channel"""
        messages = await channel.history(oldest_first=True, limit=None).flatten()
        print(len(messages))


async def setup(bot):
    """Add the levels cog to a bot."""
    await bot.add_cog(Archive(bot))
