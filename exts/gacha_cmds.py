"""
Copyright 2021-2024 AstreaTSS.
This file is part of PYTHIA, formerly known as Ultimate Investigator.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import importlib
import random
import typing

import interactions as ipy
import tansy

import common.help_tools as help_tools
import common.models as models
import common.utils as utils


def short_desc(description: str) -> str:
    if len(description) > 25:
        description = f"{description[:22]}..."
    return description


class GachaCommands(utils.Extension):
    def __init__(self, bot: utils.THIABase) -> None:
        self.name = "Gacha Commands"
        self.bot: utils.THIABase = bot

    gacha = tansy.SlashCommand(
        name="gacha",
        description="Hosts public-facing gacha commands.",
        default_member_permissions=ipy.Permissions.MANAGE_GUILD,
        dm_permission=False,
    )

    @gacha.subcommand(
        "draw",
        sub_cmd_description="Draws an item from the gacha.",
    )
    async def gacha_draw(self, ctx: utils.THIASlashContext) -> None:
        config = await ctx.fetch_config({"gacha": True, "names": True})
        if typing.TYPE_CHECKING:
            assert config.gacha is not None
            assert config.names is not None

        if not config.player_role or not config.gacha.enabled:
            raise utils.CustomCheckFailure("Gacha is not enabled in this server.")

        if not ctx.author.has_role(config.player_role):
            raise utils.CustomCheckFailure("You do not have the Player role.")

        player = await models.GachaPlayer.get_or_create(ctx.guild.id, ctx.author.id)

        if player.currency_amount < config.gacha.currency_cost:
            raise utils.CustomCheckFailure(
                "You do not have enough currency to draw from the gacha."
            )

        item_count = await models.GachaItem.prisma().count(
            where={"guild_id": ctx.guild.id}
        )
        if item_count == 0:
            raise utils.CustomCheckFailure("No items in the gacha.")

        item = await models.GachaItem.prisma().find_first_or_raise(
            skip=random.randint(0, item_count - 1),  # noqa: S311
            where={"guild_id": ctx.guild.id, "amount": {"not": 0}},
            order={"id": "asc"},
        )

        if item.amount != -1:
            item.amount -= 1
            await models.GachaItem.prisma().update(
                data={"amount": item.amount}, where={"id": item.id}
            )

        await models.GachaPlayer.prisma().update(
            where={"user_guild_id": player.user_guild_id},
            data={
                "currency_amount": {"decrement": config.gacha.currency_cost},
                "items": {
                    # "set": [{"id": i.id} for i in player.items] if player.items else [], TODO: is this needed?
                    "connect": [{"id": item.id}],
                },
            },
        )

        embed = utils.make_embed(item.description, title=item.name)
        if item.image:
            embed.set_thumbnail(item.image)

        await ctx.send(embed=embed)

    @gacha.subcommand(
        "view",
        sub_cmd_description="Shows your gacha currency and items.",
    )
    async def gacha_profile(self, ctx: utils.THIASlashContext) -> None:
        config = await ctx.fetch_config({"gacha": True, "names": True})
        if typing.TYPE_CHECKING:
            assert config.gacha is not None
            assert config.names is not None

        if not config.player_role or not config.gacha.enabled:
            raise utils.CustomCheckFailure("Gacha is not enabled in this server.")

        player = await models.GachaPlayer.get_or_none(ctx.guild_id, ctx.author.id)
        if player is None:
            raise ipy.errors.BadArgument("You have no data for gacha.")

        items_list = [
            f"**{item.name}** - {short_desc(item.description)}"
            for item in (player.items or [])
        ]
        if len(items_list) > 30:
            chunks = [items_list[x : x + 30] for x in range(0, len(items_list), 30)]
            embeds = [
                utils.make_embed(
                    "\n".join(chunk),
                    title=f"{ctx.author.display_name}'s Gacha Data",
                )
                for chunk in chunks
            ]
            embeds[0].description = (
                "Currency:"
                f" {player.currency_amount} {config.names.currency_name(player.currency_amount)}\n\n**Items:**{embeds[0].description}"
            )

            pag = help_tools.HelpPaginator.create_from_embeds(
                self.bot, *embeds, timeout=120
            )
            await pag.send(ctx, ephemeral=True)
        else:
            items_list.insert(
                0,
                "Currency:"
                f" {player.currency_amount} {config.names.currency_name(player.currency_amount)}\n\n**Items:**",
            )

            await ctx.send(
                embed=utils.make_embed(
                    "\n".join(items_list),
                    title="Items",
                ),
                ephemeral=True,
            )

    @gacha.subcommand(
        "give-currency",
        sub_cmd_description="Gives currency to a user.",
    )
    async def gacha_give_currency(
        self,
        ctx: utils.THIASlashContext,
        recipient: ipy.Member = tansy.Option("The recipient."),
        amount: int = tansy.Option("The amount to give.", min_value=1, max_value=999),
    ) -> None:
        config = await ctx.fetch_config({"gacha": True, "names": True})
        if typing.TYPE_CHECKING:
            assert config.gacha is not None
            assert config.names is not None

        if not config.player_role or not config.gacha.enabled:
            raise utils.CustomCheckFailure("Gacha is not enabled in this server.")

        if not ctx.author.has_role(config.player_role):
            raise utils.CustomCheckFailure("You do not have the Player role.")
        if not recipient.has_role(config.player_role):
            raise ipy.errors.BadArgument("The recipient does not have the Player role.")

        player = await models.GachaPlayer.get_or_none(ctx.guild_id, ctx.author.id)
        if player is None:
            if not ctx.author.has_role(config.player_role):
                raise ipy.errors.BadArgument("You have no data for gacha.")
            player = await models.GachaPlayer.prisma().create(
                data={"user_guild_id": f"{ctx.guild_id}-{ctx.author.id}"}
            )

        if player.currency_amount < amount:
            raise utils.CustomCheckFailure("You do not have enough currency to give.")

        recipient_player = await models.GachaPlayer.get_or_none(
            ctx.guild_id, recipient.id
        )
        if recipient_player is None:
            if not recipient.has_role(config.player_role):
                raise ipy.errors.BadArgument("The recipient has no data for gacha.")
            recipient_player = await models.GachaPlayer.prisma().create(
                data={"user_guild_id": f"{ctx.guild_id}-{recipient.id}"}
            )

        recipient_player.currency_amount += amount
        player.currency_amount -= amount
        await recipient_player.save()
        await player.save()

        await ctx.send(
            embed=utils.make_embed(
                f"Gave {amount} {config.names.currency_name(amount)} to"
                f" {recipient.display_name}."
            )
        )


def setup(bot: utils.THIABase) -> None:
    importlib.reload(utils)
    importlib.reload(help_tools)
    GachaCommands(bot)
