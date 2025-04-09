import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

from ballsdex.core.models import Ball

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

STATIC = os.path.isdir("static")
FILE_PREFIX = "." if STATIC else ""

async def save_file(attachment: discord.Attachment) -> Path:
    path_name = "./admin_panel/media"

    if STATIC:
        path_name = './static/uploads'

    path = Path(f"{path_name}/{attachment.filename}")

    match = FILENAME_RE.match(attachment.filename)

    if not match:
        raise TypeError("The file you uploaded lacks an extension.")

    i = 1

    while path.exists():
        path = Path(f"{path_name}/{match.group(1)}-{i}{match.group(2)}")
        i = i + 1
    
    await attachment.save(path)

    if STATIC:
        return path

    return path.relative_to("./admin_panel/media/")

@dataclass
class MessageLink:
    bot: Any

    guild: discord.Guild | None = None
    thread: discord.Thread | None = None
    message: discord.Message | None = None

    async def from_link(self, link: str):
        parsed_link = link.split("/")

        self.guild = self.bot.get_guild(int(parsed_link[4]))
        self.thread = self.guild.get_thread(int(parsed_link[5]))
        self.message = await thread.fetch_message(int(parsed_link[6]))

        return self.message

class ArtCog(commands.Cog):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def updateart(self, ctx: commands.Context, channel: discord.ForumChannel):
        """
        If a countryball's spawn art is outdated in the specified forum channel, 
        it will automatically be updated to match the current spawn artwork.

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
            thread_message = await thread.fetch_message(thread.id)

            thread_artwork_path = thread_message.attachments[0].filename
            ball_artwork_path = await Ball.get_or_none(country=thread.name).values_list(
                "wild_card", flat=True
            )

            if ball_artwork_path is None:
                await ctx.send(f"Could not find {thread.name}")
                continue

            prefix = "/static/uploads/" if STATIC else ""

            if prefix + thread_artwork_path == ball_artwork_path:
                continue

            try:
                await thread_message.edit(attachments=[
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
        existing_threads = {x.name for x in channel.threads}

        await ctx.send(
            "Generating threads...\n"
            "-# This may take a while depending on the amount of collectibles you have."
        )

        balls = await Ball.filter(enabled=True)

        for ball in balls:
            if ball.country in existing_threads:
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

        await ctx.send(f"Created `{threads_created}` threads")

    @commands.command()
    @commands.is_owner()
    async def acceptart(
        self, ctx: commands.Context, message_link: str, index: int = 1
    ):
        """
        Accepts spawn art in a thread.

        Parameters
        ----------
        message_link: str
            The messsage link containing the art.
        index: int
            The attachment you want to use, identified by its index.
        """
        index = index - 1
        message_link = MessageLink(self.bot)

        try:
            message = await message_link.from_link(message_link)
        except Exception as error:
            await ctx.send(
                f"An error occured while trying to retrieve the message.\n```{error}```"
            )
            return

        if index > len(message.attachment) or index < 0:
            await ctx.send(
                f"There are only {len(message.attachments)} attachments; "
                f"{index} is an invalid attachment number."
            )
            return

        ball = await Ball.get_or_none(country=thread.name)

        if ball is None:
            await ctx.send(f"{ball.country} doesn't exist.")
            return

        await message.add_reaction("✅")

        path = await save_file(message.attachments[index])

        ball.wild_card = f"/{path}"

        await ball.save(update_fields=["wild_card"])

        await ctx.send(
            f"Accepted {ball.country} art made by **{message.author.name}**",
            file=discord.File(f"./{path}")
        )
