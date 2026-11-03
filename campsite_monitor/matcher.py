"""Turn per-site free nights into bookable stays that satisfy a search."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from datetime import date, timedelta

from .models import Opening, SiteAvailability

WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


@dataclass
class StayRule:
    start: date  # first possible check-in
    end: date  # last possible check-out
    nights: int = 1
    check_in_days: set[int] = field(default_factory=set)  # empty = any weekday
    include_sites: list[str] = field(default_factory=list)  # glob patterns on site name
    exclude_sites: list[str] = field(default_factory=list)
    site_type_contains: list[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, raw: dict) -> StayRule:
        days = set()
        for d in raw.get("check_in_days", []):
            key = str(d).strip().lower()[:3]
            if key not in WEEKDAYS:
                raise ValueError(f"unknown weekday {d!r}")
            days.add(WEEKDAYS[key])
        start = _to_date(raw["start"])
        end = _to_date(raw["end"])
        nights = int(raw.get("nights", 1))
        if nights < 1:
            raise ValueError("nights must be >= 1")
        if end <= start:
            raise ValueError("end must be after start")
        return cls(
            start=start,
            end=end,
            nights=nights,
            check_in_days=days,
            include_sites=[str(s) for s in raw.get("include_sites", [])],
            exclude_sites=[str(s) for s in raw.get("exclude_sites", [])],
            site_type_contains=[str(s).lower() for s in raw.get("site_types", [])],
        )

    def site_allowed(self, avail: SiteAvailability) -> bool:
        name = avail.site.name
        if self.include_sites and not any(fnmatch.fnmatch(name, p) for p in self.include_sites):
            return False
        if any(fnmatch.fnmatch(name, p) for p in self.exclude_sites):
            return False
        if self.site_type_contains:
            stype = avail.site.site_type.lower()
            if not any(t in stype for t in self.site_type_contains):
                return False
        return True

    def check_ins(self, today: date | None = None) -> list[date]:
        today = today or date.today()
        first = max(self.start, today)
        out = []
        d = first
        while d + timedelta(days=self.nights) <= self.end:
            if not self.check_in_days or d.weekday() in self.check_in_days:
                out.append(d)
            d += timedelta(days=1)
        return out


def _to_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def find_openings(
    campground: str, sites: list[SiteAvailability], rule: StayRule, today: date | None = None
) -> list[Opening]:
    check_ins = rule.check_ins(today)
    openings = []
    for avail in sites:
        if not rule.site_allowed(avail):
            continue
        for ci in check_ins:
            if all(ci + timedelta(days=i) in avail.free_nights for i in range(rule.nights)):
                openings.append(Opening(campground, avail.site, ci, rule.nights))
    openings.sort(key=lambda o: (o.check_in, o.site.name))
    return openings
