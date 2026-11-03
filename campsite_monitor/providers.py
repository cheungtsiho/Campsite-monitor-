"""Availability providers.

* ``RecreationGov`` – federal sites (NPS, USACE, USFS) booked on recreation.gov.
* ``ReserveCalifornia`` – California State Parks, booked on reservecalifornia.com.

Both talk to the same unauthenticated JSON endpoints the booking websites use.
They are undocumented and may change; keep polling gentle (every few minutes).
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

from .http import request_json
from .models import Campsite, SiteAvailability

FetchJson = Callable[..., Any]


def _month_starts(start: date, end: date) -> list[date]:
    """First day of every month touched by the half-open range [start, end)."""
    months = []
    cur = start.replace(day=1)
    while cur < end:
        months.append(cur)
        cur = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
    return months


def _parse_day(value: str) -> date:
    value = value.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", value):
        return date.fromisoformat(value[:10])
    return datetime.strptime(value[:10], "%m/%d/%Y").date()


class RecreationGov:
    name = "recreation.gov"
    BASE = "https://www.recreation.gov/api/camps/availability/campground/{id}/month"
    BOOKING = "https://www.recreation.gov/camping/campsites/{site_id}"

    def __init__(self, fetch_json: FetchJson = request_json, pause: float = 1.0):
        self.fetch_json = fetch_json
        self.pause = pause

    def availability(self, campground_id: str, start: date, end: date) -> list[SiteAvailability]:
        """Free nights for every site in ``campground_id`` within [start, end)."""
        sites: dict[str, SiteAvailability] = {}
        for i, month in enumerate(_month_starts(start, end)):
            if i and self.pause:
                time.sleep(self.pause)
            url = self.BASE.format(id=campground_id) + f"?start_date={month:%Y-%m-%d}T00:00:00.000Z"
            payload = self.fetch_json(url, headers={"Referer": "https://www.recreation.gov/"})
            for site_id, raw in (payload or {}).get("campsites", {}).items():
                site_id = str(raw.get("campsite_id", site_id))
                entry = sites.get(site_id)
                if entry is None:
                    entry = SiteAvailability(
                        Campsite(
                            site_id=site_id,
                            name=str(raw.get("site", site_id)),
                            loop=str(raw.get("loop") or ""),
                            site_type=str(raw.get("campsite_type") or ""),
                            booking_url=self.BOOKING.format(site_id=site_id),
                        )
                    )
                    sites[site_id] = entry
                for stamp, status in (raw.get("availabilities") or {}).items():
                    night = _parse_day(stamp)
                    if status == "Available" and start <= night < end:
                        entry.free_nights.add(night)
        return list(sites.values())


def _normalize(text: str) -> str:
    text = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    words = {"mt": "mount", "sp": "state park", "sb": "state beach", "sra": "state recreation area"}
    return " ".join(words.get(w, w) for w in text.split())


def _as_list(value: Any) -> list[dict]:
    if isinstance(value, dict):
        return [v for v in value.values() if isinstance(v, dict)]
    return [v for v in (value or []) if isinstance(v, dict)]


class ReserveCalifornia:
    name = "reservecalifornia"
    BASE = "https://california-rdr.prod.cali.rd12.recreation-management.tylerapp.com"
    GRID = BASE + "/rdr/search/grid"
    PLACES = BASE + "/rdr/fd/places"
    FACILITIES = BASE + "/rdr/fd/facilities"
    BOOKING = "https://www.reservecalifornia.com/park/{place_id}/{facility_id}"

    def __init__(self, fetch_json: FetchJson = request_json, pause: float = 1.0):
        self.fetch_json = fetch_json
        self.pause = pause
        self._places: list[dict] | None = None
        self._facilities: list[dict] | None = None

    # -- discovery -----------------------------------------------------------
    def places(self) -> list[dict]:
        if self._places is None:
            self._places = _as_list(self.fetch_json(self.PLACES))
        return self._places

    def facilities(self) -> list[dict]:
        if self._facilities is None:
            self._facilities = _as_list(self.fetch_json(self.FACILITIES))
        return self._facilities

    def search(self, park: str | list[str], facility: str | list[str] | None = None) -> list[dict]:
        """Facilities whose park name contains any of ``park`` (and facility name
        contains any of ``facility``, if given). Returns dicts with ids and names."""
        parks = [_normalize(p) for p in ([park] if isinstance(park, str) else park)]
        facs = None
        if facility:
            facs = [_normalize(f) for f in ([facility] if isinstance(facility, str) else facility)]
        place_names = {
            int(p["PlaceId"]): str(p.get("Name", ""))
            for p in self.places()
            if any(q in _normalize(str(p.get("Name", ""))) for q in parks)
        }
        out = []
        for f in self.facilities():
            place_id = f.get("PlaceId")
            if place_id is None or int(place_id) not in place_names:
                continue
            fname = str(f.get("Name", ""))
            if facs and not any(q in _normalize(fname) for q in facs):
                continue
            out.append(
                {
                    "place_id": int(place_id),
                    "park": place_names[int(place_id)],
                    "facility_id": int(f["FacilityId"]),
                    "facility": fname,
                }
            )
        return out

    # -- availability --------------------------------------------------------
    def availability(
        self, facility_id: int | str, start: date, end: date, place_id: int | str | None = None
    ) -> list[SiteAvailability]:
        """Free nights for every unit in ``facility_id`` within [start, end)."""
        today = date.today()
        query_start = max(start, today - timedelta(days=1))
        body = {
            "IsADA": False,
            "MinVehicleLength": 0,
            "UnitCategoryId": 0,
            "StartDate": f"{query_start:%m-%d-%Y}",
            "EndDate": f"{end:%m-%d-%Y}",
            "WebOnly": True,
            "UnitTypesGroupIds": [],
            "SleepingUnitId": 0,
            "UnitSort": "orderby",
            "InSeasonOnly": True,
            "FacilityId": str(facility_id),
            "RestrictADA": False,
        }
        payload = self.fetch_json(self.GRID, method="POST", body=body) or {}
        facility = payload.get("Facility") or {}
        booking = (
            self.BOOKING.format(place_id=place_id, facility_id=facility_id)
            if place_id
            else "https://www.reservecalifornia.com/"
        )
        result = []
        for unit_id, unit in (facility.get("Units") or {}).items():
            if unit.get("AllowWebBooking") is False:
                continue
            entry = SiteAvailability(
                Campsite(
                    site_id=str(unit.get("UnitId", unit_id)),
                    name=str(unit.get("ShortName") or unit.get("Name") or unit_id),
                    loop=str(facility.get("Name") or ""),
                    site_type=str(unit.get("Name") or ""),
                    booking_url=booking,
                )
            )
            for stamp, sl in (unit.get("Slices") or {}).items():
                night = _parse_day(str(sl.get("Date") or stamp))
                if sl.get("IsFree") and not sl.get("IsBlocked") and start <= night < end:
                    entry.free_nights.add(night)
            result.append(entry)
        return result
