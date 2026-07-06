"""Email the search summary. Credentials come from environment variables only
(never stored in code or committed — see CLAUDE.md section 7):

  SMTP_USER  sender address, e.g. you@gmail.com
  SMTP_PASS  password — for Gmail use an App Password
             (Google Account -> Security -> 2-Step Verification -> App passwords)
  SMTP_HOST  optional, default smtp.gmail.com
  SMTP_PORT  optional, default 587 (STARTTLS)

The email body is the same self-contained HTML report the CLI generates,
with a plain-text fallback of the top listings.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .report import render


class EmailNotConfigured(Exception):
    pass


def _plain_summary(payload, limit=10):
    profile = payload.get("profile") or {}
    listings = payload.get("listings") or []
    lines = [
        f"Sihina Niwahana — {len(listings)} matching listings for "
        f"{'/'.join(profile.get('propertyTypes') or [])} to "
        f"{profile.get('purpose', '?')} in {', '.join(profile.get('areas') or [])}",
        "",
    ]
    for i, l in enumerate(listings[:limit], 1):
        lines.append(f"{i}. {l['title']}")
        lines.append(f"   {l.get('priceText') or 'price not stated'} | "
                     f"{l.get('area')} | {l.get('propertyType')}")
        lines.append(f"   {l['url']}")
        lines.append("")
    if len(listings) > limit:
        lines.append(f"... and {len(listings) - limit} more.")
    return "\n".join(lines)


def send_summary(to_addr, payload):
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    if not user or not password:
        raise EmailNotConfigured(
            "Email is not configured. Set the SMTP_USER and SMTP_PASS "
            "environment variables (for Gmail, SMTP_PASS is an App Password) "
            "and restart the server.")
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))

    profile = payload.get("profile") or {}
    n = len(payload.get("listings") or [])
    subject = (f"Property search: {n} matches — "
               f"{'/'.join(profile.get('propertyTypes') or [])} in "
               f"{', '.join(profile.get('areas') or [])}")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg.attach(MIMEText(_plain_summary(payload), "plain", "utf-8"))
    msg.attach(MIMEText(render(payload), "html", "utf-8"))

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.sendmail(user, [to_addr], msg.as_string())
