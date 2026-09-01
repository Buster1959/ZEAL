"""Explainable Schedule Adaptation evidence and proposal engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from statistics import median
from typing import Any, Callable
from uuid import uuid4

from ..const import (
    LEARNING_EVIDENCE_THRESHOLD,
    LEARNING_MAX_EVENTS,
    LEARNING_MAX_PROPOSALS,
    LEARNING_OBSERVATION_DAYS,
    LEARNING_RETENTION_DAYS,
    LEARNING_STORAGE_KEY_FMT,
    LEARNING_STORAGE_VERSION,
    LEARNING_TEMPERATURE_TOLERANCE,
    LEARNING_TIMING_WINDOW_MINUTES,
)
from .engine import active_period_at, next_transition_after
from .models import RoomSchedule, ScheduleConfiguration, SchedulePeriod, validate_time


@dataclass(frozen=True, slots=True)
class ClassifiedChange:
    """One unambiguous manual change tied to an immutable schedule period."""

    adaptation_type: str
    adaptation_direction: str
    weekday: str
    period_id: str
    original_time: str
    original_temperature: float
    proposed_time: str
    proposed_temperature: float

    @property
    def pattern_key(self) -> str:
        temperature = round(self.proposed_temperature * 2) / 2
        return "|".join(
            (
                self.adaptation_type,
                self.adaptation_direction,
                self.original_time,
                f"{self.original_temperature:.1f}",
                "-",
                f"{temperature:.1f}",
            )
        )


def room_schedule_revision(configuration: ScheduleConfiguration, room_id: str) -> str:
    """Fingerprint only the room schedule relevant to learning evidence."""
    room = configuration.rooms.get(room_id)
    if room is None:
        raise ValueError("Learning event refers to an unknown room")
    payload = json.dumps(room.to_dict(), sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode()).hexdigest()[:16]


def classify_manual_change(
    configuration: ScheduleConfiguration,
    room_id: str,
    requested_temperature: float,
    when: datetime,
) -> ClassifiedChange | None:
    """Classify a manual target as temperature or earlier/later timing evidence."""
    room = configuration.rooms.get(room_id)
    if room is None:
        return None
    active = active_period_at(room, when)
    following = next_transition_after(room, when)
    if active is None:
        return None
    requested = float(requested_temperature)
    if following is not None:
        until_following = following.starts_at - when
        if (
            timedelta(0) < until_following <= timedelta(
                minutes=LEARNING_TIMING_WINDOW_MINUTES
            )
            and abs(requested - following.period.temperature)
            <= LEARNING_TEMPERATURE_TOLERANCE
            and abs(requested - active.period.temperature)
            >= LEARNING_TEMPERATURE_TOLERANCE
        ):
            return ClassifiedChange(
                adaptation_type="timing",
                adaptation_direction="earlier",
                weekday=following.day,
                period_id=following.period.id,
                original_time=following.period.time,
                original_temperature=following.period.temperature,
                proposed_time=when.strftime("%H:%M"),
                proposed_temperature=following.period.temperature,
            )
    since_active = when - active.starts_at
    if timedelta(0) < since_active <= timedelta(
        minutes=LEARNING_TIMING_WINDOW_MINUTES
    ):
        previous = active_period_at(
            room, active.starts_at - timedelta(microseconds=1)
        )
        if (
            previous is not None
            and abs(requested - previous.period.temperature)
            <= LEARNING_TEMPERATURE_TOLERANCE
            and abs(requested - active.period.temperature)
            >= LEARNING_TEMPERATURE_TOLERANCE
        ):
            return ClassifiedChange(
                adaptation_type="timing",
                adaptation_direction="later",
                weekday=active.day,
                period_id=active.period.id,
                original_time=active.period.time,
                original_temperature=active.period.temperature,
                proposed_time=when.strftime("%H:%M"),
                proposed_temperature=active.period.temperature,
            )
    if abs(requested - active.period.temperature) < LEARNING_TEMPERATURE_TOLERANCE:
        return None
    return ClassifiedChange(
        adaptation_type="temperature",
        adaptation_direction="setpoint",
        weekday=active.day,
        period_id=active.period.id,
        original_time=active.period.time,
        original_temperature=active.period.temperature,
        proposed_time=active.period.time,
        proposed_temperature=requested,
    )


def apply_proposal(
    configuration: ScheduleConfiguration,
    proposal: dict[str, Any],
    *,
    proposed_time: str | None = None,
    proposed_temperature: float | None = None,
) -> ScheduleConfiguration:
    """Apply one proposal to its exact evidenced weekday and period."""
    room_id = str(proposal["room_id"])
    weekday = str(proposal["weekday"])
    period_id = str(proposal["period_id"])
    room = configuration.rooms.get(room_id)
    if room is None or weekday not in room.days:
        raise ValueError("Learning proposal refers to an unknown room or weekday")
    periods = list(room.days[weekday])
    index = next((i for i, period in enumerate(periods) if period.id == period_id), -1)
    if index < 0:
        raise ValueError("Learning proposal period no longer exists")
    current = periods[index]
    if (
        current.time != proposal.get("original_time")
        or abs(
            current.temperature - float(proposal.get("original_temperature"))
        ) > 0.001
    ):
        raise ValueError("Learning proposal conflicts with the current schedule")
    new_time = validate_time(proposed_time or str(proposal["proposed_time"]))
    new_temperature = float(
        proposal["proposed_temperature"]
        if proposed_temperature is None
        else proposed_temperature
    )
    periods[index] = SchedulePeriod(
        current.id,
        current.friendly_name,
        current.name,
        new_time,
        new_temperature,
    )
    updated_room = RoomSchedule(
        room.room_id,
        room.room_name,
        {**room.days, weekday: tuple(periods)},
    )
    return ScheduleConfiguration(
        rooms={**configuration.rooms, room_id: updated_room},
        settings=configuration.settings,
        temperature_unit=configuration.temperature_unit,
    )


class LearningStore:
    """Versioned bounded persistence for evidence and proposals."""

    def __init__(self, hass, entry_id: str, store: Any | None = None) -> None:
        if store is None:
            from homeassistant.helpers.storage import Store

            store = Store[dict[str, object]](
                hass,
                LEARNING_STORAGE_VERSION,
                LEARNING_STORAGE_KEY_FMT.format(entry_id=entry_id),
            )
        self._store = store
        self.events: list[dict[str, Any]] = []
        self.proposals: list[dict[str, Any]] = []

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if not isinstance(data, dict) or data.get("version") != LEARNING_STORAGE_VERSION:
            return
        events = data.get("events")
        proposals = data.get("proposals")
        if isinstance(events, list):
            self.events = [dict(item) for item in events if isinstance(item, dict)][
                -LEARNING_MAX_EVENTS:
            ]
        if isinstance(proposals, list):
            self.proposals = [
                dict(item) for item in proposals if isinstance(item, dict)
            ][-LEARNING_MAX_PROPOSALS:]

    async def async_save(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=LEARNING_RETENTION_DAYS)
        self.events = [
            event
            for event in self.events
            if (timestamp := event.get("timestamp"))
            and datetime.fromisoformat(str(timestamp)) >= cutoff
        ]
        self.events = self.events[-LEARNING_MAX_EVENTS:]
        self.proposals = self.proposals[-LEARNING_MAX_PROPOSALS:]
        await self._store.async_save(
            {
                "version": LEARNING_STORAGE_VERSION,
                "events": self.events,
                "proposals": self.proposals,
            }
        )


class ScheduleLearning:
    """Capture manual intent and create non-mutating schedule proposals."""

    def __init__(
        self,
        store: LearningStore,
        configuration_provider: Callable[[], ScheduleConfiguration],
        revision_provider: Callable[[], str],
        enabled_provider: Callable[[], bool] = lambda: True,
        exclusion_provider: Callable[[str], str | None] = lambda _room_id: None,
        notification_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._store = store
        self._configuration_provider = configuration_provider
        self._revision_provider = revision_provider
        self._enabled_provider = enabled_provider
        self._exclusion_provider = exclusion_provider
        self._notification_callback = notification_callback

    async def async_record_change(
        self,
        *,
        room_id: str,
        requested_temperature: float,
        source: str,
        when: datetime,
        outcome: str = "applied",
    ) -> dict[str, Any] | None:
        """Persist one qualified event and return a new proposal if detected."""
        if outcome != "applied":
            return None
        if not self._enabled_provider():
            return None
        configuration = self._configuration_provider()
        classified = classify_manual_change(
            configuration, room_id, requested_temperature, when
        )
        if classified is None:
            return None
        event = {
            "event_id": uuid4().hex,
            "timestamp": when.isoformat(),
            "local_date": when.date().isoformat(),
            "room_id": room_id,
            "source": source,
            "requested_temperature": float(requested_temperature),
            "schedule_revision": self._revision_provider(),
            "room_schedule_revision": room_schedule_revision(configuration, room_id),
            "adaptation_type": classified.adaptation_type,
            "adaptation_direction": classified.adaptation_direction,
            "weekday": classified.weekday,
            "period_id": classified.period_id,
            "original_time": classified.original_time,
            "original_temperature": classified.original_temperature,
            "proposed_time": classified.proposed_time,
            "proposed_temperature": classified.proposed_temperature,
            "pattern_key": classified.pattern_key,
            "outcome": outcome,
        }
        excluded_reason = self._exclusion_provider(room_id)
        if excluded_reason:
            event["outcome"] = "excluded"
            event["excluded_reason"] = excluded_reason
        self._store.events.append(event)
        proposal = None if excluded_reason else self._detect(event, when)
        if proposal is not None:
            self._store.proposals.append(proposal)
        await self._store.async_save()
        if self._notification_callback is not None:
            self._notification_callback(self.snapshot())
        return proposal

    def _detect(
        self, latest: dict[str, Any], now: datetime
    ) -> dict[str, Any] | None:
        cutoff = now - timedelta(days=LEARNING_OBSERVATION_DAYS)
        matches = [
            event
            for event in self._store.events
            if event.get("room_id") == latest["room_id"]
            and event.get("outcome") == "applied"
            and event.get("pattern_key") == latest["pattern_key"]
            and event.get("room_schedule_revision")
            == latest["room_schedule_revision"]
            and datetime.fromisoformat(str(event["timestamp"])) >= cutoff
        ]
        dismissed = [
            proposal
            for proposal in self._store.proposals
            if proposal.get("pattern_key") == latest["pattern_key"]
            and proposal.get("room_schedule_revision")
            == latest["room_schedule_revision"]
            and proposal.get("status") == "dismissed"
            and proposal.get("decided_at")
        ]
        if dismissed:
            dismissed_at = max(
                datetime.fromisoformat(str(item["decided_at"]))
                for item in dismissed
            )
            matches = [
                event
                for event in matches
                if datetime.fromisoformat(str(event["timestamp"])) > dismissed_at
            ]
        by_date: dict[str, dict[str, Any]] = {}
        for event in matches:
            by_date[str(event["local_date"])] = event
        if len(by_date) < LEARNING_EVIDENCE_THRESHOLD:
            return None
        if any(
            proposal.get("pattern_key") == latest["pattern_key"]
            and proposal.get("room_schedule_revision")
            == latest["room_schedule_revision"]
            and proposal.get("status") in ("new", "snoozed", "accepted")
            for proposal in self._store.proposals
        ):
            return None
        evidence = sorted(by_date.values(), key=lambda item: str(item["timestamp"]))
        proposed_temperature = round(
            median(float(item["proposed_temperature"]) for item in evidence) * 2
        ) / 2
        proposed_time = latest["proposed_time"]
        if latest["adaptation_type"] == "timing":
            minutes = sorted(
                int(str(item["proposed_time"])[:2]) * 60
                + int(str(item["proposed_time"])[3:5])
                for item in evidence
            )
            middle = int(median(minutes))
            proposed_time = f"{middle // 60:02d}:{middle % 60:02d}"
        return {
            "proposal_id": uuid4().hex,
            "created_at": now.isoformat(),
            "status": "new",
            "room_id": latest["room_id"],
            "weekday": latest["weekday"],
            "period_id": latest["period_id"],
            "adaptation_type": latest["adaptation_type"],
            "adaptation_direction": latest["adaptation_direction"],
            "schedule_revision": latest["schedule_revision"],
            "room_schedule_revision": latest["room_schedule_revision"],
            "pattern_key": latest["pattern_key"],
            "original_time": latest["original_time"],
            "original_temperature": latest["original_temperature"],
            "proposed_time": proposed_time,
            "proposed_temperature": proposed_temperature,
            "evidence_ids": [item["event_id"] for item in evidence],
            "evidence_count": len(evidence),
            "confidence": "high" if len(evidence) >= 5 else "medium",
        }

    def snapshot(self) -> dict[str, Any]:
        """Return detached learning state for API consumers."""
        return {
            "version": LEARNING_STORAGE_VERSION,
            "events": [dict(item) for item in self._store.events],
            "proposals": [dict(item) for item in self._store.proposals],
        }

    def proposal(self, proposal_id: str) -> dict[str, Any]:
        """Return one mutable stored proposal or raise a safe lookup error."""
        proposal = next(
            (
                item
                for item in self._store.proposals
                if item.get("proposal_id") == proposal_id
            ),
            None,
        )
        if proposal is None:
            raise ValueError("Unknown learning proposal")
        return proposal

    async def async_set_status(
        self,
        proposal_id: str,
        status: str,
        *,
        decided_at: datetime,
        decided_by: str,
        snoozed_until: datetime | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist one authorised proposal decision."""
        if status not in {"accepted", "dismissed", "snoozed", "reverted", "conflicted"}:
            raise ValueError("Unsupported learning proposal status")
        proposal = self.proposal(proposal_id)
        if proposal.get("status") not in {"new", "snoozed", "accepted"}:
            raise ValueError("Learning proposal is no longer actionable")
        proposal["status"] = status
        proposal["decided_at"] = decided_at.isoformat()
        proposal["decided_by"] = decided_by
        proposal["snoozed_until"] = (
            snoozed_until.isoformat() if snoozed_until is not None else None
        )
        if details:
            proposal.update(details)
        await self._store.async_save()
        if self._notification_callback is not None:
            self._notification_callback(self.snapshot())
        return dict(proposal)


def sync_persistent_notification(hass, entry_id: str, state: dict[str, Any]) -> None:
    """Maintain one aggregated Home Assistant notification per ZEAL instance."""
    from homeassistant.components import persistent_notification
    from homeassistant.util import dt as dt_util

    notification_id = f"zeal_learning_{entry_id}"
    now = dt_util.now()
    actionable = [
        proposal
        for proposal in state.get("proposals", [])
        if proposal.get("status") == "new"
        or (
            proposal.get("status") == "snoozed"
            and proposal.get("snoozed_until")
            and datetime.fromisoformat(str(proposal["snoozed_until"])) <= now
        )
    ]
    if not actionable:
        persistent_notification.async_dismiss(hass, notification_id)
        return
    count = len(actionable)
    persistent_notification.async_create(
        hass,
        f"ZEAL has {count} learning suggestion{'s' if count != 1 else ''} ready "
        "for review. No schedule will change without confirmation.\n\n"
        "[Review in ZEAL](/zeal)",
        "ZEAL Learning",
        notification_id,
    )
