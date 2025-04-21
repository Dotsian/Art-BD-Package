import asyncio
import os
import re
import tomllib
from dataclasses import dataclass, field
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

STATIC = not os.path.isdir("admin_panel/media")

FILE_PREFIX = "." if STATIC else "./admin_panel/media/"
FILENAME_RE = re.compile(r"^(.+)(\.\S+)$")

class PackageSettings:
    """
    Settings for the art package that can be accessed via the `config.toml` file.
    """

    def __init__(self, path):
        with open(path, "rb") as f:
            data = tomllib.load(f)

        if data is None:
            return

        self.accepted_message = data.get(
            "accepted-message", "Hi $user, your artwork for **$ball** has been accepted!"
        )

        self.art_role_ids = data.get("art-role-ids", [])
        self.art_guilds = data.get("art-guilds", [])

        self.accepted_emoji = data.get("accepted-emoji", "✅")
        self.progress_rate = data.get("progress-rate", 25)

        self.update_thread_art = data.get("update-thread-art", True)

class ArtType(Enum):
    SPAWN = "wild_card"
    CARD = "collection_card"

art_settings = PackageSettings(
    Path(os.path.dirname(os.path.abspath(__file__)), "./config.toml")
)

async def save_file(attachment: discord.Attachment) -> Path:
    path_name = "static/uploads" if STATIC else "admin_panel/media"

    path = Path(f"./{path_name}/{attachment.filename}")

    match = FILENAME_RE.match(attachment.filename)

    if not match:
        raise TypeError("The file you uploaded lacks an extension.")

    i = 1

    while path.exists():
        path = Path(f"./{path_name}/{match.group(1)}-{i}{match.group(2)}")
        i = i + 1
    
    await attachment.save(path)

    return path.relative_to("./admin_panel/media/")

@app_commands.guilds(*art_settings.art_guilds)
class Art(commands.GroupCog):
    """
    Art management commands.
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
        self.loading_message: discord.Message | None = None

    spawn = app_commands.Group(name="spawn", description="Spawn art management")
    card = app_commands.Group(name="card", description="Card art management")

    async def _create(
        self, interaction: discord.Interaction, channel: discord.ForumChannel, art: ArtType
    ):
        if self.loading_message is not None:
            await interaction.response.send_message(
                "Thread creation is still running!", ephemeral=True
            )
            return
        
        await interaction.response.defer(thinking=True)
        
        threads_created = 0
        existing_threads = {x.name for x in channel.threads}

        await interaction.followup.send(
            "Starting thread creation!", ephemeral=True
        )

        balls = [x for x in await Ball.filter(enabled=True) if x.country not in existing_threads]
        ball_length = len(balls)

        self.loading_message = await interaction.channel.send(
            f"Progress: 0% (0/{ball_length})"
        )

        if self.loading_message is None:
            return

        for ball in balls:
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

            if threads_created % art_settings.progress_rate == 0 or threads_created == ball_length:
                percentage = round((threads_created / ball_length) * 100, 2)

                await self.loading_message.edit(
                    content=f"Progress: {percentage}% ({threads_created}/{ball_length})"
                )

            await asyncio.sleep(0.75)

        await interaction.channel.send(content=f"Finished! Created `{threads_created}` threads")
        self.loading_message = None

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
        if not link.startswith("https://discord.com/channels/"):
            await interaction.response.send("Invalid message link entered.", ephemeral=True)
            return
        
        index = index - 1
        parsed_link = link.split("/")

        guild = self.bot.get_guild(int(parsed_link[4]))

        if guild is None:
            await interaction.response.send_message(
                f"Could not fetch guild from message link.", ephemeral=True
            )
            return

        thread = guild.get_thread(int(parsed_link[5]))

        if thread is None:
            await interaction.response.send_message(
                f"Could not fetch thread from message link.", ephemeral=True
            )
            return

        try:
            message = await thread.fetch_message(int(parsed_link[6]))
        except Exception as error:
            await interaction.response.send_message(
                f"An error occured while trying to retrieve the message.\n```{error}```",
                ephemeral=True
            )
            return

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

        ball = await Ball.get_or_none(country=thread.name)

        if ball is None:
            await interaction.response.send_message(
                f"{ball.country} doesn't exist.", ephemeral=True
            )
            return
        
        await interaction.response.defer(thinking=True)

        await message.add_reaction(art_settings.accepted_emoji)

        path = await save_file(message.attachments[index])

        setattr(ball, art.value, f"/{path}")

        await ball.save(update_fields=[art.value])

        art_file = FILE_PREFIX + getattr(ball, art.value)

        suffix_message = ""

        try:
            await message.author.send(art_settings.accepted_message
                .replace("$ball", ball.country)
                .replace("$user", message.author.display_name)
            )
        except Exception:
            suffix_message = "\n-# Failed to DM user."

        if settings.update_thread_art:
            thread_message = await thread.fetch_message(thread.id)

            await thread_message.edit(attachments=[discord.File(art_file)])

        await interaction.followup.send(
            f"Accepted {ball.country} art made by **{message.author.name}**{suffix_message}",
            file=discord.File(art_file)
        )

    @spawn.command(name="create")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *art_settings.art_role_ids)
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
            self.loading_message = None

    @card.command(name="create")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *art_settings.art_role_ids)
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
            self.loading_message = None

    @spawn.command(name="update")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *art_settings.art_role_ids)
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
    @app_commands.checks.has_any_role(*settings.root_role_ids, *art_settings.art_role_ids)
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
    @app_commands.checks.has_any_role(*settings.root_role_ids, *art_settings.art_role_ids)
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
    @app_commands.checks.has_any_role(*settings.root_role_ids, *art_settings.art_role_ids)
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

