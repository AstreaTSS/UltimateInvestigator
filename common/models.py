"""
Copyright 2021-2024 AstreaTSS.
This file is part of PYTHIA, formerly known as Ultimate Investigator.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import os
import re
import typing
from enum import IntEnum

import interactions as ipy
import orjson
from prisma._async_http import Response
from prisma.models import PrismaConfig, PrismaNames, PrismaTruthBullet
from pydantic import field_serializer, field_validator


# yes, this is a copy from common.utils
# but circular imports are a thing
def yesno_friendly_str(bool_to_convert: bool) -> str:
    return "yes" if bool_to_convert else "no"


def generate_regexp(attribute: str) -> str:
    return rf"regexp_replace({attribute}, '([\%_])', '\\\1', 'g')"


ILIKE_ESCAPE = re.compile(r"([\%_])")


def escape_ilike(value: str) -> str:
    return ILIKE_ESCAPE.sub(r"\\\1", value)


TEMPLATE_MARKDOWN = re.compile(r"({{(.*)}})")


def code_template(value: str) -> str:
    return TEMPLATE_MARKDOWN.sub(r"`\1`", value)


class TruthBullet(PrismaTruthBullet):
    aliases: set[str]

    @field_validator("aliases", mode="after")
    @classmethod
    def _transform_aliases_into_set(cls, value: list[str]) -> set[str]:
        return set(value)

    @field_serializer("aliases", when_used="always")
    def _transform_aliases_into_list(self, value: set[str]) -> list[str]:
        return sorted(value)

    @property
    def chan_mention(self) -> str:
        return f"<#{self.channel_id}>"

    def bullet_info(self) -> str:
        str_list = [
            f"Trigger `{self.trigger}` - in {self.chan_mention}",
            f"Aliases: {', '.join(f'`{a}`' for a in self.aliases)}",
            f"Hidden: {yesno_friendly_str(self.hidden)}",
            f"Found: {yesno_friendly_str(self.found)}",
        ]

        str_list.extend(
            (
                f"Finder: {f'<@{self.finder}>' if self.finder else 'N/A'}",
                "",
                f"Description: {self.description}",
            )
        )

        return "\n".join(str_list)

    def found_embed(self, username: str, singular_bullet: str) -> ipy.Embed:
        embed = ipy.Embed(
            title=f"{singular_bullet} Discovered",
            timestamp=ipy.Timestamp.utcnow(),
            color=int(os.environ["BOT_COLOR"]),
        )
        embed.description = (
            f"`{self.trigger}` - from {self.chan_mention}\n\n{self.description}"
        )

        footer = f"Found by {username}" if self.finder else "To be found as of"
        embed.set_footer(text=footer)

        return embed

    @classmethod
    async def find(
        cls, channel_id: ipy.Snowflake_Type, content: str
    ) -> typing.Self | None:
        return await cls.prisma().query_first(
            FIND_TRUTH_BULLET_STR, int(channel_id), content
        )

    @classmethod
    async def find_exact(
        cls, channel_id: ipy.Snowflake_Type, content: str
    ) -> typing.Self | None:
        return await cls.prisma().query_first(
            FIND_TRUTH_BULLET_EXACT_STR, int(channel_id), content
        )

    @classmethod
    async def find_possible_bullet(
        cls, channel_id: ipy.Snowflake_Type, trigger: str
    ) -> typing.Self | None:
        return await cls.prisma().find_first(
            where={
                "channel_id": int(channel_id),
                "trigger": {"equals": escape_ilike(trigger), "mode": "insensitive"},
            }
        )

    @classmethod
    async def validate(cls, channel_id: ipy.Snowflake_Type, trigger: str) -> bool:
        return (
            await cls.prisma()._client.query_first(
                VALIDATE_TRUTH_BULLET_STR, int(channel_id), trigger
            )
            is not None
        )

    async def save(self) -> None:
        data = self.model_dump()
        await self.prisma().update(where={"id": self.id}, data=data)  # type: ignore


class Names(PrismaNames):
    async def save(self) -> None:
        data = self.model_dump(exclude={"config"})
        await self.prisma().update(where={"id": self.id}, data=data)  # type: ignore


class InvestigationType(IntEnum):
    DEFAULT = 1
    COMMAND_ONLY = 2


class Config(PrismaConfig):
    investigation_type: InvestigationType

    if typing.TYPE_CHECKING:
        names: Names
    else:
        names: typing.Optional[Names] = None

    @field_validator("investigation_type", mode="after")
    @classmethod
    def _transform_int_into_investigation_type(cls, value: int) -> InvestigationType:
        return InvestigationType(value)

    @field_serializer("investigation_type", when_used="always")
    def _transform_investigation_type_into_int(self, value: InvestigationType) -> int:
        return value.value

    @classmethod
    async def get(cls, guild_id: int) -> typing.Self:
        config = await cls.prisma().find_unique_or_raise(
            where={"guild_id": guild_id}, include={"names": True}
        )

        if not config.names:
            config = await cls.prisma().update(
                where={"guild_id": config.guild_id},
                data={"names": {"create": {}}},
                include={"names": True},
            )
            if typing.TYPE_CHECKING:
                assert config is not None

        return config

    @classmethod
    async def get_or_none(cls, guild_id: int) -> typing.Optional[typing.Self]:
        config = await cls.prisma().find_unique(
            where={"guild_id": guild_id}, include={"names": True}
        )

        if config and not config.names:
            config = await cls.prisma().update(
                where={"guild_id": config.guild_id},
                data={"names": {"create": {}}},
                include={"names": True},
            )

        return config

    async def save(self) -> None:
        data = self.model_dump(exclude={"names", "names_id"})
        await self.prisma().update(where={"guild_id": self.guild_id}, data=data)  # type: ignore


FIND_TRUTH_BULLET_STR: typing.Final[str] = (
    f"""
SELECT
    {', '.join(TruthBullet.model_fields)}
FROM
    uinewtruthbullets
WHERE
    channel_id = $1
    AND found = false
    AND (
        $2 ILIKE CONCAT('%', {generate_regexp('trigger')}, '%')
        OR EXISTS (
            SELECT 1
            FROM unnest(aliases) AS alias
            WHERE $2 ILIKE CONCAT('%', {generate_regexp('alias')}, '%')
        )
    );
""".strip()  # noqa: S608
)

VALIDATE_TRUTH_BULLET_STR: typing.Final[str] = (
    """
SELECT
    1
FROM
    uinewtruthbullets
WHERE
    channel_id = $1
    AND (
        UPPER($2) = UPPER(trigger)
        OR EXISTS (
            SELECT 1
            FROM unnest(aliases) AS alias
            WHERE UPPER($2) = UPPER(alias)
        )
    );
""".strip()
)

FIND_TRUTH_BULLET_EXACT_STR: typing.Final[str] = (
    f"""
SELECT
    {', '.join(TruthBullet.model_fields)}
FROM
    uinewtruthbullets
WHERE
    channel_id = $1
    AND (
        UPPER($2) = UPPER(trigger)
        OR EXISTS (
            SELECT 1
            FROM unnest(aliases) AS alias
            WHERE UPPER($2) = UPPER(alias)
        )
    );
""".strip()  # noqa: S608
)


class FastResponse(Response):
    async def json(self, **kwargs: typing.Any) -> typing.Any:
        return orjson.loads(await self.original.aread(), **kwargs)


Response.json = FastResponse.json  # type: ignore
