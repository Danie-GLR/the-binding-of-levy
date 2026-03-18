"""Discord bot runtime with /dbot slash commands for caption relay settings."""

from __future__ import annotations

import os

import discord
from discord import app_commands
from discord.ext import commands

from .discord_settings import GuildBotSettings, get_guild_settings, save_guild_settings

_ALLOWED_TRANSLATION_LANGS = [
    app_commands.Choice(name="English", value="en"),
    app_commands.Choice(name="Spanish", value="es"),
    app_commands.Choice(name="French", value="fr"),
    app_commands.Choice(name="German", value="de"),
    app_commands.Choice(name="Portuguese", value="pt"),
    app_commands.Choice(name="Italian", value="it"),
    app_commands.Choice(name="Japanese", value="ja"),
]


def _guild_only(interaction: discord.Interaction) -> int:
    if not interaction.guild_id:
        raise app_commands.CheckFailure("This command can only be used inside a server.")
    return int(interaction.guild_id)


class DbotGroup(app_commands.Group):
    def __init__(self, *, name: str = "dbot", description: str = "Configure Discord caption bot settings") -> None:
        super().__init__(name=name, description=description)

    @app_commands.command(name="help", description="Show a quick setup card with easy commands")
    async def help_card(self, interaction: discord.Interaction) -> None:
        guild_id = _guild_only(interaction)
        embed = discord.Embed(
            title="Dbot Quick Commands",
            description="Use these commands to set relay, translation, and style quickly.",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Fast Setup",
            value="`/d quick channel:#captions`",
            inline=False,
        )
        embed.add_field(
            name="Enable Translation",
            value="`/d tr enabled:true target:en`",
            inline=False,
        )
        embed.add_field(
            name="Set Prefix",
            value="`/d p text:[CAP]`",
            inline=False,
        )
        embed.add_field(
            name="Check Status",
            value="`/d s`",
            inline=False,
        )
        embed.add_field(
            name="Overlay URL",
            value=(
                "`/stream-caption?overlay=1&relay=on&guild="
                f"{guild_id}`"
            ),
            inline=False,
        )
        embed.set_footer(text="Use /d ... for short commands, /dbot ... also works.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="quick", description="One-command setup for relay channel")
    @app_commands.describe(channel="Text channel to receive relayed captions")
    async def quick(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        guild_id = _guild_only(interaction)
        settings = get_guild_settings(guild_id)
        settings.relay_channel_id = int(channel.id)
        save_guild_settings(settings)
        await interaction.response.send_message(
            f"Quick setup done. Relay channel is now <#{channel.id}>.",
            ephemeral=True,
        )

    @app_commands.command(name="s", description="Short alias for status")
    async def status_short(self, interaction: discord.Interaction) -> None:
        await self.status(interaction)

    @app_commands.command(name="tr", description="Short alias for translation")
    @app_commands.choices(target=_ALLOWED_TRANSLATION_LANGS)
    async def translation_short(
        self,
        interaction: discord.Interaction,
        enabled: bool,
        target: app_commands.Choice[str] | None = None,
    ) -> None:
        await self.translation(interaction, enabled=enabled, target=target)

    @app_commands.command(name="ch", description="Short alias for channel")
    async def channel_short(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        await self.channel(interaction, channel=channel)

    @app_commands.command(name="p", description="Short alias for prefix")
    async def prefix_short(self, interaction: discord.Interaction, text: str = "") -> None:
        await self.prefix(interaction, text=text)

    @app_commands.command(name="status", description="Show current bot settings for this server")
    async def status(self, interaction: discord.Interaction) -> None:
        guild_id = _guild_only(interaction)
        settings = get_guild_settings(guild_id)
        relay = str(settings.relay_channel_id) if settings.relay_channel_id else "not set"
        translation = "on" if settings.translation_enabled else "off"
        target = settings.translation_target
        prefix = settings.caption_prefix or "(none)"

        message = (
            f"Relay channel: {relay}\n"
            f"Translation: {translation} ({target})\n"
            f"Caption prefix: {prefix}"
        )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="setup", description="Quick setup relay channel + translation")
    @app_commands.describe(
        channel="Text channel to receive captions",
        translation="Enable translation for relayed captions",
        target="Target language when translation is enabled",
        prefix="Optional message prefix for each caption",
    )
    @app_commands.choices(target=_ALLOWED_TRANSLATION_LANGS)
    async def setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        translation: bool = False,
        target: app_commands.Choice[str] | None = None,
        prefix: str = "",
    ) -> None:
        guild_id = _guild_only(interaction)
        settings = GuildBotSettings(
            guild_id=guild_id,
            relay_channel_id=int(channel.id),
            translation_enabled=bool(translation),
            translation_target=(target.value if target else "en"),
            caption_prefix=prefix.strip()[:80],
        )
        save_guild_settings(settings)
        await interaction.response.send_message(
            f"Saved. Relay channel set to <#{channel.id}>. Translation: "
            f"{'on' if settings.translation_enabled else 'off'} ({settings.translation_target}).",
            ephemeral=True,
        )

    @app_commands.command(name="channel", description="Set the text channel used for caption relay")
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        guild_id = _guild_only(interaction)
        settings = get_guild_settings(guild_id)
        settings.relay_channel_id = int(channel.id)
        save_guild_settings(settings)
        await interaction.response.send_message(
            f"Relay channel set to <#{channel.id}>.",
            ephemeral=True,
        )

    @app_commands.command(name="translation", description="Enable/disable translation and pick target language")
    @app_commands.choices(target=_ALLOWED_TRANSLATION_LANGS)
    async def translation(
        self,
        interaction: discord.Interaction,
        enabled: bool,
        target: app_commands.Choice[str] | None = None,
    ) -> None:
        guild_id = _guild_only(interaction)
        settings = get_guild_settings(guild_id)
        settings.translation_enabled = bool(enabled)
        if target:
            settings.translation_target = target.value
        save_guild_settings(settings)
        await interaction.response.send_message(
            f"Translation {'enabled' if settings.translation_enabled else 'disabled'}"
            f" (target: {settings.translation_target}).",
            ephemeral=True,
        )

    @app_commands.command(name="prefix", description="Set an optional prefix before relayed captions")
    async def prefix(self, interaction: discord.Interaction, text: str = "") -> None:
        guild_id = _guild_only(interaction)
        settings = get_guild_settings(guild_id)
        settings.caption_prefix = text.strip()[:80]
        save_guild_settings(settings)
        shown = settings.caption_prefix or "(none)"
        await interaction.response.send_message(
            f"Caption prefix saved: {shown}",
            ephemeral=True,
        )


def run_discord_bot() -> None:
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required to run the Discord bot.")

    intents = discord.Intents.none()
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready() -> None:
        if not hasattr(bot, "_dbot_synced"):
            bot.tree.add_command(DbotGroup(name="dbot", description="Configure Discord caption bot settings"))
            bot.tree.add_command(DbotGroup(name="d", description="Easy Dbot commands"))
            dev_guild_id = os.environ.get("DISCORD_DEV_GUILD_ID", "").strip()
            if dev_guild_id.isdigit():
                guild_obj = discord.Object(id=int(dev_guild_id))
                bot.tree.copy_global_to(guild=guild_obj)
                await bot.tree.sync(guild=guild_obj)
            else:
                await bot.tree.sync()
            setattr(bot, "_dbot_synced", True)
        print(f"Discord bot ready as {bot.user}")

    bot.run(token)
