"""Core data types shared by providers, the matcher and notifiers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Campsite:
    """One bookable site (or cabin) inside a campground."""

    site_id: str
    name: str
    loop: str = ""
    site_type: str = ""
    booking_url: str = ""


@dataclass
class SiteAvailability:
    """The nights a single site is free within the requested window."""

    site: Campsite
    free_nights: set[date] = field(default_factory=set)


@dataclass(frozen=True)
class Opening:
    """A concrete stay that can be booked right now."""

    campground: str
    site: Campsite
    check_in: date
    nights: int

    @property
    def check_out(self) -> date:
        from datetime import timedelta

        return self.check_in + timedelta(days=self.nights)

    @property
    def key(self) -> str:
        """Stable identifier used to avoid notifying twice for the same opening."""
        return f"{self.campground}|{self.site.site_id}|{self.check_in.isoformat()}|{self.nights}"

    def describe(self) -> str:
        loop = f" ({self.site.loop})" if self.site.loop else ""
        return (
            f"{self.campground}: site {self.site.name}{loop} "
            f"{self.check_in:%a %b %d} -> {self.check_out:%a %b %d} "
            f"({self.nights} night{'s' if self.nights != 1 else ''})"
        )
