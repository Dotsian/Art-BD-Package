import asyncio
import os
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from ballsdex.core.models import Ball

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


class ArtCog(commands.Cog):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def makerevamps(self, ctx: commands.Context, channel: discord.ForumChannel):
        """
        Generates a list of all countryball's spawn arts in a specific forum channel.

        Parameters
        ----------
        channel: discord.ForumChannel
            The channel you want to generate the spawn art in.
        """
        threads = [x.name for x in channel.threads]
        threads_created = 0

        await ctx.send(
            "Generating threads...\n"
            "-# This may take a while depending on the amount of collectibles you have."
        )

        for ball in await Ball.filter(enabled=True):
            if ball.country in threads:
                continue

            prefix = "." if os.path.isdir("static") else ""

            await channel.create_thread(
                name=ball.country, file=discord.File(prefix + ball.wild_card)
            )

            threads_created += 1

            await asyncio.sleep(1)

        await ctx.send(f"Created `{threads_created}` threads")
