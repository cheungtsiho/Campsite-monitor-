"""Notification channels. Each is optional; console output is always on.

Configure in the ``[notify]`` table of the config file, or via environment
variables (which win, so secrets can stay out of the file):

* ``NTFY_TOPIC``  – push to the ntfy.sh app (``https://ntfy.sh/<topic>`` or a full URL)
* ``WEBHOOK_URL`` – Slack / Discord incoming webhook
* ``SMTP_HOST``, ``SMTP_PORT``, ``SMTP_USER``, ``SMTP_PASSWORD``, ``EMAIL_TO``,
  ``EMAIL_FROM`` – email
"""

from __future__ import annotations

import json
import os
import smtplib
import urllib.request
from email.message import EmailMessage

from .models import Opening


def _summary(openings: list[Opening], limit: int = 20) -> str:
    lines = []
    for o in openings[:limit]:
        lines.append(f"- {o.describe()}\n  {o.site.booking_url}")
    if len(openings) > limit:
        lines.append(f"... and {len(openings) - limit} more")
    return "\n".join(lines)


class Notifier:
    def __init__(self, config: dict | None = None):
        cfg = dict(config or {})
        env = os.environ
        self.ntfy = env.get("NTFY_TOPIC") or cfg.get("ntfy_topic")
        self.webhook = env.get("WEBHOOK_URL") or cfg.get("webhook_url")
        self.smtp_host = env.get("SMTP_HOST") or cfg.get("smtp_host")
        self.smtp_port = int(env.get("SMTP_PORT") or cfg.get("smtp_port") or 587)
        self.smtp_user = env.get("SMTP_USER") or cfg.get("smtp_user")
        self.smtp_password = env.get("SMTP_PASSWORD") or cfg.get("smtp_password")
        self.email_to = env.get("EMAIL_TO") or cfg.get("email_to")
        self.email_from = env.get("EMAIL_FROM") or cfg.get("email_from") or self.smtp_user

    def send(self, openings: list[Opening]) -> list[str]:
        """Send ``openings`` everywhere configured. Returns channel errors."""
        if not openings:
            return []
        title = f"{len(openings)} new campsite opening{'s' if len(openings) != 1 else ''}"
        body = _summary(openings)
        print(f"\n*** {title} ***\n{body}\n", flush=True)
        errors = []
        for channel, fn in (
            ("ntfy", self._ntfy),
            ("webhook", self._webhook),
            ("email", self._email),
        ):
            try:
                fn(title, body, openings)
            except Exception as exc:  # one broken channel must not stop the others
                errors.append(f"{channel}: {exc}")
        return errors

    def _ntfy(self, title: str, body: str, openings: list[Opening]) -> None:
        if not self.ntfy:
            return
        url = self.ntfy if self.ntfy.startswith("http") else f"https://ntfy.sh/{self.ntfy}"
        headers = {"Title": title, "Tags": "camping", "Priority": "high"}
        if openings[0].site.booking_url:
            headers["Click"] = openings[0].site.booking_url
        req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
        urllib.request.urlopen(req, timeout=20).close()

    def _webhook(self, title: str, body: str, openings: list[Opening]) -> None:
        if not self.webhook:
            return
        text = f"*{title}*\n{body}"
        # "text" is read by Slack, "content" by Discord.
        data = json.dumps({"text": text, "content": text[:1900]}).encode()
        req = urllib.request.Request(
            self.webhook, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        urllib.request.urlopen(req, timeout=20).close()

    def _email(self, title: str, body: str, openings: list[Opening]) -> None:
        if not (self.smtp_host and self.email_to):
            return
        msg = EmailMessage()
        msg["Subject"] = title
        msg["From"] = self.email_from or self.email_to
        msg["To"] = self.email_to
        msg.set_content(body)
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            if self.smtp_user:
                smtp.login(self.smtp_user, self.smtp_password or "")
            smtp.send_message(msg)
