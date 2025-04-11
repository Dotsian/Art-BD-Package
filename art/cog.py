import asyncio
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

from ballsdex.settings import settings
from ballsdex.core.models import Ball

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

# KEYWORDS: $ball, $user
DM_MESSAGE = "Hi $user, your artwork for **$ball** has been accepted!"

STATIC = os.path.isdir("static")

FILE_PREFIX = "." if STATIC else ""
FILENAME_RE = re.compile(r"^(.+)(\.\S+)$")

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

class ArtType(Enum):
    SPAWN = "spawn"
    CARD = "card"

@dataclass
class MessageLink:
    bot: Any

    guild: discord.Guild | None = None
    thread: discord.Thread | None = None
    message: discord.Message | None = None

    async def from_link(self, link: str) -> discord.Message | None:
        parsed_link = link.split("/")

        self.guild = self.bot.get_guild(int(parsed_link[4]))

        if self.guild is None:
            return

        self.thread = self.guild.get_thread(int(parsed_link[5]))

        if self.thread is None:
            return

        self.message = await self.thread.fetch_message(int(parsed_link[6]))

        return self.message

class Art(commands.GroupCog):
    """
    Art management commands.
    """

    def __init__(self, bot: "BallsDexBot"):
        self.creating_threads = False
        self.bot = bot

    spawn = app_commands.Group(name="spawn", description="Spawn art management")
    card = app_commands.Group(name="card", description="Card art management")

    async def _create(
        self, interaction: discord.Interaction, channel: discord.ForumChannel, art: ArtType
    ):
        if self.creating_threads:
            await interaction.response.send_message(
                "Thread generation is still ongoing!", ephemeral=True
            )
            return

        self.creating_threads = True

        threads_created = 0
        existing_threads = {x.name for x in channel.threads}

        await interaction.response.send_message(
            "Starting thread generation!", ephemeral=True
        )

        await interaction.channel.send(
            "Generating threads...\n"
            "-# This may take a while depending on the amount of collectibles you have."
        )

        balls = await Ball.filter(enabled=True)

        for ball in balls:
            if ball.country in existing_threads:
                continue

            attribute = ball.wild_card if art == ArtType.SPAWN else ball.collection_card

            try:
                thread = await channel.create_thread(
                    name=ball.country, file=discord.File(FILE_PREFIX + attribute)
                )

                await thread.message.pin()
            except Exception as error:
                await interaction.channel.send(
                    f"Failed to create `{ball.country}`\n```\n{error}\n```",
                )

                continue

            threads_created += 1

            await asyncio.sleep(0.75)

        self.creating_threads = False

        await interaction.channel.send(f"Created `{threads_created}` threads")

    async def _update(
        self, interaction: discord.Interaction, channel: discord.ForumChannel, art: ArtType
    ):
        threads_updated = 0

        await interaction.response.send_message(
            "Starting update process!", ephemeral=True
        )

        await interaction.channel.send(
            "Updating threads...\n"
            "-# This may take a while depending on the amount of collectibles you updated."
        )

        attribute = "wild_card" if art == ArtType.SPAWN else "collection_card"

        for thread in channel.threads:
            thread_message = await thread.fetch_message(thread.id)

            thread_artwork_path = thread_message.attachments[0].filename
            ball_artwork_path = await Ball.get_or_none(country=thread.name).values_list(
                attribute, flat=True
            )

            if ball_artwork_path is None:
                await interaction.channel.send(f"Could not find {thread.name}")
                continue

            prefix = "/static/uploads/" if STATIC else ""

            if prefix + thread_artwork_path == ball_artwork_path:
                continue

            try:
                await thread_message.edit(attachments=[
                    discord.File(FILE_PREFIX + ball_artwork_path)
                ])
            except Exception as error:
                await interaction.channel.send(f"Failed to update `{thread.name}`\n```\n{error}\n```")

                continue

            threads_updated += 1

            await asyncio.sleep(0.75)

        await interaction.channel.send(f"Updated `{threads_updated}` threads")

    async def _accept(
        self, interaction: discord.Interaction, art: ArtType, link: str, index: int = 1
    ):
        index = index - 1
        message_link = MessageLink(self.bot)

        try:
            message = await message_link.from_link(link)
        except Exception as error:
            await interaction.response.send_message(
                f"An error occured while trying to retrieve the message.\n```{error}```",
                ephemeral=True
            )
            return
        
        if message_link.thread is None:
            await interaction.response.send_message(
                "Failed to fetch thread from message link.", ephemeral=True
            )
            return

        thread_message = await message_link.thread.fetch_message(message_link.thread.id)

        if message is None:
            await interaction.response.send_message(
                "Failed to fetch thread message from message link.", ephemeral=True
            )
            return

        if index > len(message.attachments) or index < 0:
            await interaction.response.send_message(
                f"There are only {len(message.attachments)} attachments; "
                f"{index} is an invalid attachment number.",
                ephemeral=True
            )
            return

        ball = await Ball.get_or_none(country=message_link.thread.name)

        if ball is None:
            await interaction.response.send_message(
                f"{ball.country} doesn't exist.", ephemeral=True
            )
            return
        
        await interaction.response.defer()

        await message.add_reaction("✅")

        path = await save_file(message.attachments[index])

        if art == ArtType.SPAWN:
            ball.wild_card = f"/{path}"
        else:
            ball.collection_card = f"/{path}"

        await ball.save(update_fields=["wild_card" if art == ArtType.SPAWN else "collection_card"])

        art_file = FILE_PREFIX + (ball.wild_card if art == ArtType.SPAWN else ball.collection_card)

        suffix_message = ""

        try:
            await message.author.send(DM_MESSAGE
                .replace("$ball", ball.country)
                .replace("$user", message.author.display_name)
            )
        except Exception:
            suffix_message = "\n-# Failed to DM user."

        await thread_message.edit(attachments=[discord.File(art_file)])

        await interaction.followup.send(
            f"Accepted {ball.country} art made by **{message.author.name}**{suffix_message}",
            file=discord.File(art_file)
        )

    @spawn.command(name="create")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.admin_role_ids)
    async def spawn_create(self, interaction: discord.Interaction, channel: discord.ForumChannel):
        """
        Generates a thread per countryball containing its spawn art in a specific forum.

        Parameters
        ----------
        channel: discord.ForumChannel
            The channel you want to generate the spawn art in.
        """
        try:
            await self._create(interaction, channel, ArtType.SPAWN)
        except Exception:
            self.creating_threads = False

    @card.command(name="create")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.admin_role_ids)
    async def card_create(self, interaction: discord.Interaction, channel: discord.ForumChannel):
        """
        Generates a thread per countryball containing its card art in a specific forum.

        Parameters
        ----------
        channel: discord.ForumChannel
            The channel you want to generate the card art in.
        """
        try:
            await self._create(interaction, channel, ArtType.CARD)
        except Exception:
            self.creating_threads = False

    @spawn.command(name="update")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.admin_role_ids)
    async def spawn_update(self, interaction: discord.Interaction, channel: discord.ForumChannel):
        """
        Updates all outdated countryball spawn art in a specified forum.

        Parameters
        ----------
        channel: discord.ForumChannel
            The channel you want to update the spawn art in.
        """
        await self._update(interaction, channel, ArtType.SPAWN)

    @card.command(name="update")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.admin_role_ids)
    async def card_update(self, interaction: discord.Interaction, channel: discord.ForumChannel):
        """
        Updates all outdated countryball card art in a specified forum.

        Parameters
        ----------
        channel: discord.ForumChannel
            The channel you want to update the card art in.
        """
        await self._update(interaction, channel, ArtType.CARD)

    @spawn.command(name="accept")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.admin_role_ids)
    async def spawn_accept(self, interaction: discord.Interaction, link: str, index: int = 1):
        """
        Accepts a countryball's spawn art in a thread using a message link.

        Parameters
        ----------
        link: str
            The messsage link containing the spawn art.
        index: int
            The attachment you want to use, identified by its index.
        """
        await self._accept(interaction, ArtType.SPAWN, link, index)

    @card.command(name="accept")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.admin_role_ids)
    async def card_accept(self, interaction: discord.Interaction, link: str, index: int = 1):
        """
        Accepts a countryball's card art in a thread using a message link.

        Parameters
        ----------
        link: str
            The messsage link containing the card art.
        index: int
            The attachment you want to use, identified by its index.
        """
        await self._accept(interaction, ArtType.CARD, link, index)
