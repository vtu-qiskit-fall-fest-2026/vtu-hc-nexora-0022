"""Campus zones used by the demo. Replace the numbers with real campus data."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Zone:
    name: str
    population: int   # people present in the zone during peak heat hours
    risk: int         # heat-risk level, 1 (low) to 5 (severe)
    units: int        # cooling units needed (fans, misting sets, shaded rest area)

    @property
    def exposure(self) -> float:
        """People-risk exposure that cooling this zone covers."""
        return self.population * self.risk / 100.0


DEFAULT_ZONES = [
    Zone("Central Library", 400, 2, 2),
    Zone("Hostel Block A", 650, 4, 3),
    Zone("Sports Ground", 300, 5, 2),
    Zone("Main Auditorium", 500, 3, 3),
    Zone("Cafeteria Court", 350, 4, 1),
    Zone("Engineering Block", 600, 3, 3),
]
DEFAULT_BUDGET = 7   # cooling units available
