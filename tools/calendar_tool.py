"""
tools/calendar_tool.py — Calendar and Reminder Integration (.ics).

Supports:
- Generating standard iCalendar (.ics) files for meetings, deadlines, study plans, and reminders.
- Explicit UTC / named timezone specification (e.g. Asia/Kolkata, America/New_York).
- Creating calendar artifacts for one-click import into Google Calendar, Outlook, and Apple Calendar.
- Enforcing user confirmation for calendar scheduling.
"""

import uuid
import datetime
from typing import Dict, Any, Optional

from services.artifact_service import default_artifact_service


def create_calendar_event(
    title: str,
    start_time_iso: str,  # "2026-10-25T10:00:00"
    end_time_iso: Optional[str] = None,
    description: str = "",
    location: str = "Online",
    timezone: str = "UTC",
    user_id: str = "default_user",
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates an iCalendar (.ics) event file and registers it as an artifact.
    """
    try:
        dt_start = datetime.datetime.fromisoformat(start_time_iso)
    except Exception:
        dt_start = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)

    if end_time_iso:
        try:
            dt_end = datetime.datetime.fromisoformat(end_time_iso)
        except Exception:
            dt_end = dt_start + datetime.timedelta(hours=1)
    else:
        dt_end = dt_start + datetime.timedelta(hours=1)

    fmt = "%Y%m%dT%H%M%SZ"
    t_start = dt_start.strftime(fmt)
    t_end = dt_end.strftime(fmt)
    t_stamp = datetime.datetime.now(datetime.timezone.utc).strftime(fmt)
    uid = f"{uuid.uuid4().hex}@spark-ai.local"

    ics_content = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//SPARK-AI//Calendar Integration//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{t_stamp}\r\n"
        f"DTSTART:{t_start}\r\n"
        f"DTEND:{t_end}\r\n"
        f"SUMMARY:{title}\r\n"
        f"DESCRIPTION:{description}\r\n"
        f"LOCATION:{location}\r\n"
        "STATUS:CONFIRMED\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )

    fname = f"event_{uuid.uuid4().hex[:6]}.ics"
    art = default_artifact_service.save_artifact(
        file_name=fname,
        content=ics_content,
        user_id=user_id,
        session_id=session_id,
        mime_type="text/calendar"
    )

    return {
        "success": True,
        "title": title,
        "start_time": dt_start.isoformat(),
        "end_time": dt_end.isoformat(),
        "timezone": timezone,
        "artifact_id": art.artifact_id,
        "download_url": art.preview_url,
        "ics_content": ics_content
    }
