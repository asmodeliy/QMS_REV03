from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

from models import StatusEnum

STR_DONE_KO = "완료"
STR_INPROG_KO = "진행중"
STR_NOTSTART_KO = "준비중"


class ScheduleEnum(str, Enum):
    NA = "NA"
    NO_DUE = "NO_DUE"
    LATE = "LATE"
    DUE_TODAY = "DUE_TODAY"
    DUE_SOON = "DUE_SOON"
    ON_TRACK = "ON_TRACK"
    DONE = "DONE"


@dataclass
class ScheduleInfo:
    state: ScheduleEnum
    days_left: Optional[int]
    label: str


def _coerce_status(status: StatusEnum | str | None) -> StatusEnum:
    if isinstance(status, StatusEnum):
        return status
    if not status:
        return StatusEnum.NOT_STARTED
    m = StatusEnum._value2member_map_.get(str(status), None)
    if m:
        return m
    s = str(status).strip()
    if s in ("완료",):
        return StatusEnum.COMPLETE
    if s in ("진행중", "진행 중"):
        return StatusEnum.IN_PROGRESS
    if s in ("준비중", "준비 중"):
        return StatusEnum.NOT_STARTED
    if s.upper() in ("N/A", "NA"):
        return StatusEnum.NA
    return StatusEnum.NOT_STARTED


def compute_schedule(due_date: Optional[date], status: StatusEnum | str, *, soon_threshold: int = 3) -> ScheduleInfo:
    status = _coerce_status(status)
    today = date.today()

    if status == StatusEnum.NA:
        return ScheduleInfo(ScheduleEnum.NA, None, "")

    if status == StatusEnum.COMPLETE:
        return ScheduleInfo(ScheduleEnum.DONE, 0 if due_date else None, STR_DONE_KO)

    if due_date is None:
        return ScheduleInfo(ScheduleEnum.NO_DUE, None, "마감일 입력 필요")

    d = (due_date - today).days
    if d < 0:
        return ScheduleInfo(ScheduleEnum.LATE, d, f"{abs (d )}일 지연")
    if d == 0:
        return ScheduleInfo(ScheduleEnum.DUE_TODAY, d, "당일 마감")
    if d <= soon_threshold:
        return ScheduleInfo(ScheduleEnum.DUE_SOON, d, f"마감 임박 (D-{d })")
    return ScheduleInfo(ScheduleEnum.ON_TRACK, d, f"잔여기간 {d }일")


def compute_derived(due_date: Optional[date], status_str: str):

    status = _coerce_status(status_str)
    info = compute_schedule(due_date, status)

    remain_txt = ""
    delay_txt = ""
    signal_txt = ""

    if info.state == ScheduleEnum.NA:
        return "", "", ""
    if info.state == ScheduleEnum.NO_DUE:
        return "", "", "마감일 입력 필요"
    if info.state == ScheduleEnum.DONE:
        return "", "", STR_DONE_KO
    if info.state == ScheduleEnum.LATE:
        return "", f"{abs (info .days_left )}일 지연", "지연중"
    if info.state == ScheduleEnum.DUE_TODAY:
        return "잔여기간 0일", "", "당일 마감"
    if info.state == ScheduleEnum.DUE_SOON:
        return f"잔여기간 {info .days_left }일", "", f"마감 임박 (D-{info .days_left })"
    return (
        f"잔여기간 {info .days_left }일",
        "",
        (STR_INPROG_KO if status == StatusEnum.IN_PROGRESS else STR_NOTSTART_KO),
    )
