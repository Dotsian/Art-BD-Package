import asyncio
import os
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from ballsdex.core.models import Ball

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

STATIC = os.path.isdir("static")
FILE_PREFIX = "." if STATIC else ""

class ArtCog(commands.Cog):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def updateart(self, ctx: commands.Context, channel: discord.ForumChannel):
        """
        If a countryball's spawn art is outdated in the specified forum channel, 
        they will automatically be updated to match the current spawn artwork.

        Parameters
        ----------
        channel: discord.ForumChannel
            The channel you want to update the spawn art in.
        """
        threads_updated = 0

        await ctx.send(
            "Updating threads...\n"
            "-# This may take a while depending on the amount of collectibles you updated."
        )

        for thread in channel.threads:
            thread_artwork_path = thread.starter_message.attachments[0].filename
            ball_artwork_path = await Ball.get(country=thread.name).values_list(
                "wild_card", flat=True
            )

            prefix = "/static/uploads/" if STATIC else ""

            if prefix + thread_artwork_path == ball_artwork_path:
                continue

            try:
                await thread.starter_message.edit(attachments=[
                    discord.File(FILE_PREFIX + ball_artwork_path)
                ])
            except Exception as error:
                await ctx.send(f"Failed to update `{thread.name}`\n```\n{error}\n```")
                await ctx.send("Continuing...")

                continue

            threads_updated += 1

            await asyncio.sleep(0.75)

        await ctx.send(f"Updated `{threads_updated}` threads")

    @commands.command()
    @commands.is_owner()
    async def spawnart(self, ctx: commands.Context, channel: discord.ForumChannel):
        """
        Generates a list of all countryball's spawn arts in a specific forum channel.

        Parameters
        ----------
        channel: discord.ForumChannel
            The channel you want to generate the spawn art in.
        """
        threads_created = 0
        threads = [x.name for x in channel.threads]

        await ctx.send(
            "Generating threads...\n"
            "-# This may take a while depending on the amount of collectibles you have."
        )

        for ball in await Ball.filter(enabled=True):
            if ball.country in threads:
                continue

            try:
                await channel.create_thread(
                    name=ball.country, file=discord.File(FILE_PREFIX + ball.wild_card)
                )
            except Exception as error:
                await ctx.send(f"Failed to create `{ball.country}`\n```\n{error}\n```")
                await ctx.send("Continuing...")

                continue

            threads_created += 1

            await asyncio.sleep(0.75)

        await ctx.send(f"Created `{threads_created}` threads")
