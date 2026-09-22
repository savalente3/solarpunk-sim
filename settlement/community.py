"""The community: the buildings and the store, on one plane.

The buildings grow and consume, the store moves produce between them. This is
what holds them together, and what runs the weeks.
"""
from settlement.weather import Weather


class Community:
    # - how far tenant needs swing either way in a week
    variation = 0.25

    def __init__(self, buildings, store):
        self.buildings = buildings
        self.store = store

    def run_week(self, week, rng):
        # - each building gets its own weather and its own rate
        skies = {}
        tanks = {}
        wanted = {}
        
        for building in self.buildings:
            weather = Weather(rng)
            rate = 1 + rng.uniform(-self.variation, self.variation)

            building.collect(weather)

            skies[building.name] = weather.intensity
            tanks[building.name] = {"energy": building.energy, "water": building.water}
            wanted[building.name] = building.needs(rate)

        # - managers agree a split
        # - allotment is watered, grows, harvested
        # - tenants take what they need
        # - building trades produce for variety

        return {
            "week": week,
            "weather": skies,
            "tenants": wanted,
            "buildings": tanks,
        }

    def __repr__(self):
        names = ", ".join(building.name for building in self.buildings)
        return f"Community(buildings=[{names}], store={self.store!r})"
