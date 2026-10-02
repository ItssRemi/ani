from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import discord
from discord.http import Route
from redbot.core import Config, commands


log = logging.getLogger("red.nebula.giveawayreminder")

DANK_MEMER_ID = 270904126974590976
COMPONENTS_V2_FLAG = 1 << 15
REMINDER_POST_KEY = "giveaway"
COOLDOWN_SECONDS = 300
GIVEAWAY_APP_COMMAND_ID = 1011560371078832208

COMMAND_MENTIONS = {
    "items": f"</giveaway create items:{GIVEAWAY_APP_COMMAND_ID}>",
    "coins": f"</giveaway create coins:{GIVEAWAY_APP_COMMAND_ID}>",
}

COMMAND_COPY_TEXT = {
    "items": "/giveaway create items",
    "coins": "/giveaway create coins",
}

COMMAND_NAMES = {
    "giveaway create items": "items",
    "giveaway create coins": "coins",
}

INTERACTION_ID_RE = re.compile(r"\bid=(\d+)")
INTERACTION_USER_ID_RE = re.compile(r"user=<User id=(\d+)")


@dataclass
class PendingGiveaway:
    guild_id: int
    channel_id: int
    message_id: int
    user_id: int
    kind: str
    seen_at: float
    interaction_id: Optional[int] = None


class GiveawayReminder(commands.Cog):
    """Engine-only reminder for Dank Memer giveaway create cooldowns."""

    __author__ = "Nebula"
    __version__ = "1.2.0"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=846235019465123772,
            force_registration=True,
        )
        self.config.register_guild(reminders={})

        self._pending_by_message: dict[tuple[int, int, int], PendingGiveaway] = {}
        self._pending_by_interaction: dict[tuple[int, int], PendingGiveaway] = {}
        self._tasks: dict[tuple[int, int], asyncio.Task] = {}
        self._seen_success_messages: set[int] = set()
        self._startup_task = self.bot.loop.create_task(self._restore_saved_reminders())

    def cog_unload(self):
        self._startup_task.cancel()

        for task in list(self._tasks.values()):
            task.cancel()

        self._tasks.clear()
        self._pending_by_message.clear()
        self._pending_by_interaction.clear()
        self._seen_success_messages.clear()

    async def _restore_saved_reminders(self) -> None:
        wait = getattr(self.bot, "wait_until_red_ready", None) or getattr(
            self.bot,
            "wait_until_ready",
            None,
        )

        if wait:
            await wait()

        try:
            all_guilds = await self.config.all_guilds()
        except Exception:
            all_guilds = {}

        for guild_id, guild_data in all_guilds.items():
            reminders = guild_data.get("reminders") or {}

            for user_id_text, record in list(reminders.items()):
                try:
                    user_id = int(user_id_text)
                    remind_at = int(record["remind_at"])
                except (KeyError, TypeError, ValueError):
                    continue

                if record.get("state") == "waiting":
                    schedule_id = str(record.get("schedule_id") or f"legacy:{remind_at}:waiting")
                    self._schedule_task(int(guild_id), user_id, remind_at, schedule_id)

    async def _reminder_enabled_for(self, user_id: int) -> bool:
        core = self.bot.get_cog("NebulaReminderCore")
        if core is None:
            return False

        checker = getattr(core, "is_reminder_enabled", None)
        if checker is None:
            return False

        return bool(await checker(int(user_id), "giveaway"))

    async def set_enabled(self, user_id: int, enabled: bool) -> None:
        if enabled:
            return

        user_id = int(user_id)

        for key, task in list(self._tasks.items()):
            _guild_id, task_user_id = key
            if int(task_user_id) == user_id:
                task.cancel()
                self._tasks.pop(key, None)

        try:
            all_guilds = await self.config.all_guilds()
        except Exception:
            all_guilds = {}

        for guild_id, guild_data in all_guilds.items():
            reminders = guild_data.get("reminders") or {}
            record = reminders.pop(str(user_id), None)
            if not isinstance(record, dict):
                continue

            await self._delete_record_post(user_id, record)
            await self.config.guild_from_id(int(guild_id)).reminders.set(reminders)

    async def set_user_enabled(self, user_id: int, enabled: bool) -> None:
        await self.set_enabled(user_id, enabled)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not self._is_dank_message(message):
            return

        if not message.guild:
            return

        if self._message_is_pending_candidate(message):
            self._track_pending_message(message)
            return

        if not self._message_has_created_success(message):
            return

        if message.id in self._seen_success_messages:
            return

        reference_id = self._reference_message_id_from_message(message)
        interaction_id = self._interaction_id_from_message(message)
        user_id = self._interaction_user_id_from_message(message)

        pending = self._resolve_pending(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            reference_message_id=reference_id,
            interaction_id=interaction_id,
            user_id=user_id,
        )
        if pending is None:
            log.debug(
                "Giveaway success message %s was seen, but no matching pending confirmation was found.",
                message.id,
            )
            return

        self._seen_success_messages.add(message.id)
        self._trim_seen_success_messages()
        self._forget_pending(pending)

        await self._start_cooldown(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            user_id=pending.user_id,
            kind=pending.kind,
            source_message_id=pending.message_id,
        )

    def _is_dank_message(self, message: discord.Message) -> bool:
        author_id = getattr(getattr(message, "author", None), "id", None)
        webhook_id = getattr(message, "webhook_id", None)
        return author_id == DANK_MEMER_ID or webhook_id == DANK_MEMER_ID

    def _message_is_pending_candidate(self, message: discord.Message) -> bool:
        command_name = self._interaction_name_from_message(message).lower()
        if command_name in COMMAND_NAMES:
            return True

        chat_input_type = getattr(discord.MessageType, "chat_input_command", None)
        if chat_input_type is not None and getattr(message, "type", None) != chat_input_type:
            return False

        component_text = "\n".join(
            self._component_texts(getattr(message, "components", None) or [])
        )
        return self._kind_from_giveaway_text(component_text) is not None

    def _track_pending_message(self, message: discord.Message) -> bool:
        if not message.guild:
            return False

        component_text = "\n".join(
            self._component_texts(getattr(message, "components", None) or [])
        )
        kind = self._kind_from_giveaway_text(component_text)

        command_name = self._interaction_name_from_message(message)
        if command_name:
            kind = kind or COMMAND_NAMES.get(command_name.lower())

        if kind is None:
            return False

        user_id = self._interaction_user_id_from_message(message)
        if user_id is None:
            return False

        pending = PendingGiveaway(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            message_id=message.id,
            user_id=user_id,
            kind=kind,
            seen_at=time.time(),
            interaction_id=self._interaction_id_from_message(message),
        )
        self._remember_pending(pending)
        return True

    def _remember_pending(self, pending: PendingGiveaway) -> None:
        self._cleanup_pending()

        self._pending_by_message[
            (pending.guild_id, pending.channel_id, pending.message_id)
        ] = pending

        if pending.interaction_id is not None:
            self._pending_by_interaction[
                (pending.guild_id, pending.interaction_id)
            ] = pending

    def _forget_pending(self, pending: PendingGiveaway) -> None:
        self._pending_by_message.pop(
            (pending.guild_id, pending.channel_id, pending.message_id),
            None,
        )

        if pending.interaction_id is not None:
            self._pending_by_interaction.pop(
                (pending.guild_id, pending.interaction_id),
                None,
            )

    def _resolve_pending(
        self,
        *,
        guild_id: int,
        channel_id: int,
        reference_message_id: Optional[int],
        interaction_id: Optional[int],
        user_id: Optional[int],
    ) -> Optional[PendingGiveaway]:
        self._cleanup_pending()

        if reference_message_id is not None:
            pending = self._pending_by_message.get(
                (guild_id, channel_id, reference_message_id)
            )
            if pending is not None:
                return pending

        if interaction_id is not None:
            pending = self._pending_by_interaction.get((guild_id, interaction_id))
            if pending is not None:
                return pending

        if user_id is None:
            return None

        matches = [
            pending
            for pending in self._pending_by_message.values()
            if pending.guild_id == guild_id
            and pending.channel_id == channel_id
            and pending.user_id == user_id
            and time.time() - pending.seen_at <= 180
        ]

        if not matches:
            return None

        return max(matches, key=lambda pending: pending.seen_at)

    async def _start_cooldown(
        self,
        *,
        guild_id: int,
        channel_id: int,
        user_id: int,
        kind: str,
        source_message_id: Optional[int] = None,
    ) -> None:
        if kind not in COMMAND_MENTIONS:
            return

        if not await self._reminder_enabled_for(user_id):
            return

        guild_id = int(guild_id)
        channel_id = int(channel_id)
        user_id = int(user_id)
        reminders = await self.config.guild_from_id(guild_id).reminders()
        old_record = reminders.get(str(user_id)) or {}

        if (
            isinstance(old_record, dict)
            and old_record.get("state") == "waiting"
            and self._int_or_none(old_record.get("source_message_id")) == self._int_or_none(source_message_id)
        ):
            return

        if isinstance(old_record, dict) and old_record.get("post_owner") != "core":
            await self._delete_record_post(user_id, old_record)

        remind_at = int(time.time()) + COOLDOWN_SECONDS
        command_mention = COMMAND_MENTIONS[kind]
        copy_text = COMMAND_COPY_TEXT[kind]
        confirmation_text = (
            f"I will remind you to run giveaway <t:{remind_at}:R>\n"
        )
        confirmation_id, post_owner = await self._replace_reminder_post(
            user_id=user_id,
            channel_id=channel_id,
            content=confirmation_text,
            reference_message_id=source_message_id,
            reference_guild_id=guild_id,
        )

        schedule_id = f"{confirmation_id}:{remind_at}:waiting"
        reminders[str(user_id)] = {
            "user_id": user_id,
            "channel_id": channel_id,
            "kind": kind,
            "remind_at": remind_at,
            "message_id": confirmation_id,
            "source_message_id": source_message_id,
            "source_channel_id": channel_id,
            "state": "waiting",
            "schedule_id": schedule_id,
            "post_owner": post_owner,
        }
        await self.config.guild_from_id(guild_id).reminders.set(reminders)

        self._schedule_task(guild_id, user_id, remind_at, schedule_id)

    def _schedule_task(
        self,
        guild_id: int,
        user_id: int,
        remind_at: int,
        schedule_id: str,
    ) -> None:
        key = (int(guild_id), int(user_id))

        old_task = self._tasks.pop(key, None)
        if old_task is not None:
            old_task.cancel()

        self._tasks[key] = self.bot.loop.create_task(
            self._wait_and_remind(int(guild_id), int(user_id), int(remind_at), str(schedule_id))
        )

    async def _wait_and_remind(
        self,
        guild_id: int,
        user_id: int,
        remind_at: int,
        schedule_id: str,
    ) -> None:
        try:
            await asyncio.sleep(max(0, int(remind_at) - time.time()))

            reminders = await self.config.guild_from_id(int(guild_id)).reminders()
            record = reminders.get(str(user_id))

            if not record or int(record.get("remind_at", 0)) != int(remind_at):
                return

            stored_schedule_id = record.get("schedule_id")
            if stored_schedule_id is not None and str(stored_schedule_id) != str(schedule_id):
                return

            if record.get("state") != "waiting":
                return

            if not await self._reminder_enabled_for(user_id):
                await self._delete_record_post(user_id, record)
                reminders.pop(str(user_id), None)
                await self.config.guild_from_id(int(guild_id)).reminders.set(reminders)
                return

            channel_id = self._int_or_none(record.get("channel_id"))
            source_message_id = self._int_or_none(record.get("source_message_id"))
            kind = str(record.get("kind") or "")
            command_mention = COMMAND_MENTIONS.get(kind)

            if not channel_id or not command_mention:
                reminders.pop(str(user_id), None)
                await self.config.guild_from_id(int(guild_id)).reminders.set(reminders)
                return

            if record.get("post_owner") != "core":
                await self._delete_record_post(user_id, record)

            copy_text = COMMAND_COPY_TEXT.get(kind, "/giveaway create")
            reminder_text = (
                f"<@{user_id}>, you can run {command_mention}\n"
            )
            reminder_id, post_owner = await self._replace_reminder_post(
                user_id=int(user_id),
                channel_id=int(channel_id),
                content=reminder_text,
                mention_user_id=int(user_id),
                reference_message_id=source_message_id,
                reference_guild_id=int(guild_id),
            )

            record["message_id"] = int(reminder_id)
            record["state"] = "ready"
            record["post_owner"] = post_owner
            record["schedule_id"] = f"{reminder_id}:{int(remind_at)}:ready"
            reminders[str(user_id)] = record
            await self.config.guild_from_id(int(guild_id)).reminders.set(reminders)

        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception(
                "Failed to send giveaway reminder for guild %s user %s",
                guild_id,
                user_id,
            )
        finally:
            self._tasks.pop((int(guild_id), int(user_id)), None)

    def _v2_payload(
        self,
        content: str,
        *,
        mention_user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "flags": COMPONENTS_V2_FLAG,
            "components": [
                {
                    "id": 1,
                    "type": 17,
                    "accent_color": None,
                    "spoiler": False,
                    "components": [
                        {
                            "id": 2,
                            "type": 10,
                            "content": str(content),
                        }
                    ],
                }
            ],
            "allowed_mentions": {"parse": []},
        }

        if mention_user_id is not None:
            payload["allowed_mentions"]["users"] = [str(int(mention_user_id))]

        return payload

    async def _send_v2_message(
        self,
        channel_id: int,
        content: str,
        *,
        mention_user_id: Optional[int] = None,
        reference_message_id: Optional[int] = None,
        reference_guild_id: Optional[int] = None,
    ) -> int:
        payload = self._v2_payload(content, mention_user_id=mention_user_id)

        core = self.bot.get_cog("NebulaReminderCore")
        sender = getattr(core, "send_v2_message", None) if core is not None else None

        if sender is not None:
            return int(
                await sender(
                    int(channel_id),
                    content,
                    reference_message_id=reference_message_id,
                    reference_guild_id=reference_guild_id,
                    mention_user_id=mention_user_id,
                    payload=payload,
                )
            )

        if reference_message_id is not None:
            payload["message_reference"] = {
                "message_id": int(reference_message_id),
                "channel_id": int(channel_id),
                "fail_if_not_exists": False,
            }

            if reference_guild_id is not None:
                payload["message_reference"]["guild_id"] = int(reference_guild_id)

        data = await self.bot.http.request(
            Route("POST", "/channels/{channel_id}/messages", channel_id=int(channel_id)),
            json=payload,
        )
        return int(data["id"])

    async def _replace_reminder_post(
        self,
        *,
        user_id: int,
        channel_id: int,
        content: str,
        mention_user_id: Optional[int] = None,
        reference_message_id: Optional[int] = None,
        reference_guild_id: Optional[int] = None,
    ) -> tuple[int, str]:
        payload = self._v2_payload(content, mention_user_id=mention_user_id)

        core = self.bot.get_cog("NebulaReminderCore")
        replacer = getattr(core, "replace_reminder_post", None) if core is not None else None

        if replacer is not None:
            message_id = await replacer(
                int(user_id),
                REMINDER_POST_KEY,
                int(channel_id),
                content,
                reference_message_id=reference_message_id,
                reference_guild_id=reference_guild_id,
                mention_user_id=mention_user_id,
                payload=payload,
            )
            return int(message_id), "core"

        message_id = await self._send_v2_message(
            int(channel_id),
            content,
            mention_user_id=mention_user_id,
            reference_message_id=reference_message_id,
            reference_guild_id=reference_guild_id,
        )
        return int(message_id), "local"

    async def _delete_record_post(self, user_id: int, record: dict[str, Any]) -> None:
        core = self.bot.get_cog("NebulaReminderCore")

        if record.get("post_owner") == "core":
            deleter = getattr(core, "delete_tracked_reminder_post", None) if core is not None else None
            if deleter is not None:
                await deleter(int(user_id), REMINDER_POST_KEY)
                return

        channel_id = self._int_or_none(record.get("channel_id"))
        message_id = self._int_or_none(record.get("message_id"))

        if channel_id and message_id:
            await self._delete_message(channel_id, message_id)

        clearer = getattr(core, "clear_reminder_post", None) if core is not None else None
        if clearer is not None:
            await clearer(int(user_id), REMINDER_POST_KEY)

    async def _delete_message(self, channel_id: int, message_id: int) -> None:
        core = self.bot.get_cog("NebulaReminderCore")
        deleter = getattr(core, "delete_message", None) if core is not None else None

        if deleter is not None:
            await deleter(int(channel_id), int(message_id))
            return

        try:
            await self.bot.http.request(
                Route(
                    "DELETE",
                    "/channels/{channel_id}/messages/{message_id}",
                    channel_id=int(channel_id),
                    message_id=int(message_id),
                )
            )
        except discord.NotFound:
            return
        except discord.Forbidden:
            log.warning(
                "Missing permission to delete giveaway reminder message %s in channel %s",
                message_id,
                channel_id,
            )
        except discord.HTTPException:
            log.exception(
                "Failed to delete giveaway reminder message %s in channel %s",
                message_id,
                channel_id,
            )

    def _message_has_created_success(self, message: discord.Message) -> bool:
        if "Created your giveaway!" in (message.content or ""):
            return True

        text = "\n".join(
            self._component_texts(getattr(message, "components", None) or [])
        )
        return "Created your giveaway!" in text

    def _kind_from_giveaway_text(self, text: str) -> Optional[str]:
        lowered = text.lower()

        if "pending confirmation" not in lowered:
            return None

        if "giveaway your items" in lowered:
            return "items"

        if "giveaway your coins" in lowered:
            return "coins"

        return None

    def _interaction_metadata_from_message(self, message: discord.Message) -> Any:
        return getattr(message, "interaction_metadata", None)

    def _interaction_name_from_message(self, message: discord.Message) -> str:
        meta = self._interaction_metadata_from_message(message)
        if meta is None:
            return ""

        name = getattr(meta, "name", None)
        if name is not None:
            return str(name).strip()

        if isinstance(meta, dict):
            return str(meta.get("name") or "").strip()

        return ""

    def _interaction_id_from_message(self, message: discord.Message) -> Optional[int]:
        meta = self._interaction_metadata_from_message(message)
        if meta is None:
            return None

        if isinstance(meta, dict):
            parsed = self._int_or_none(meta.get("id"))
            if parsed is not None:
                return parsed

        value = getattr(meta, "id", None)
        parsed = self._int_or_none(value)
        if parsed is not None:
            return parsed

        match = INTERACTION_ID_RE.search(repr(meta))
        return int(match.group(1)) if match else None

    def _interaction_user_id_from_message(self, message: discord.Message) -> Optional[int]:
        meta = self._interaction_metadata_from_message(message)
        if meta is None:
            return None

        if isinstance(meta, dict):
            user = meta.get("user") or {}
            if isinstance(user, dict):
                parsed = self._int_or_none(user.get("id"))
                if parsed is not None:
                    return parsed

        user = getattr(meta, "user", None)
        user_id = self._int_or_none(getattr(user, "id", None))
        if user_id is not None:
            return user_id

        match = INTERACTION_USER_ID_RE.search(repr(meta))
        return int(match.group(1)) if match else None

    def _reference_message_id_from_message(self, message: discord.Message) -> Optional[int]:
        reference = getattr(message, "reference", None)
        if reference and reference.message_id:
            return int(reference.message_id)
        return None

    def _component_texts(self, components: Any) -> list[str]:
        texts: list[str] = []

        if not components:
            return texts

        for component in components:
            if isinstance(component, dict):
                content = component.get("content")
                if content:
                    texts.append(str(content))

                texts.extend(self._component_texts(component.get("components") or []))
                texts.extend(self._component_texts(component.get("children") or []))

                accessory = component.get("accessory")
                if accessory:
                    texts.extend(self._component_texts([accessory]))

                continue

            content = getattr(component, "content", None)
            if content:
                texts.append(str(content))

            for attr in ("components", "children"):
                nested = getattr(component, attr, None)
                if nested:
                    texts.extend(self._component_texts(nested))

            accessory = getattr(component, "accessory", None)
            if accessory:
                texts.extend(self._component_texts([accessory]))

        return texts

    def _cleanup_pending(self) -> None:
        cutoff = time.time() - 180

        expired_message_keys = [
            key
            for key, pending in self._pending_by_message.items()
            if pending.seen_at < cutoff
        ]
        for key in expired_message_keys:
            self._pending_by_message.pop(key, None)

        expired_interaction_keys = [
            key
            for key, pending in self._pending_by_interaction.items()
            if pending.seen_at < cutoff
        ]
        for key in expired_interaction_keys:
            self._pending_by_interaction.pop(key, None)

    def _trim_seen_success_messages(self) -> None:
        if len(self._seen_success_messages) <= 500:
            return

        self._seen_success_messages.clear()

    @staticmethod
    def _int_or_none(value: Any) -> Optional[int]:
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None



async def setup(bot):
    await bot.add_cog(GiveawayReminder(bot))
