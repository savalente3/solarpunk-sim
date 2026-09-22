"""A building: what it collects from the weather, and what it can hold.

The battery and the tank belong to the building. The allotment on its roof
draws from them too, which is what the two managers have to agree on.
"""
from agents.building_managers import BuildingManagers
from settlement.allotment import Allotment


class Building:
    # - roof space in square metres
    # - beds take what the panels leave
    roof_area = 200
    panel_area = 60

    # - yield at intensity 1.0
    panel_yield = 1.04      # kWh per square metre of panel
    rain_yield = 11.9       # litres per square metre of roof

    # - storage limits
    battery = 120           # kWh
    tank = 3000             # litres

    # - what the tenants want in a day
    tenant_needs = {"energy": 30, "water": 200, "food": 3}

    def __init__(self, name, model_config):
        self.name = name

        # - a season starts on a full tank, not on an empty one
        self.energy = self.battery
        self.water = self.tank

        self.allotment = Allotment(self.roof_area - self.panel_area)
        self.managers = BuildingManagers(name, model_config)

    def needs(self, rate):
        # - rate comes from the day, same for every building
        
        wanted = {}
        for name, amount in self.tenant_needs.items():
            wanted[name] = round(amount * rate)

        return wanted

    def collect(self, weather):
        # - sun and rain go into store
        # - anything above capacity is lost

        collected_energy = round(weather.intensity["sun"] * self.panel_area * self.panel_yield)
        collected_water = round(weather.intensity["rain"] * self.roof_area * self.rain_yield)

        self.energy = min(self.energy + collected_energy, self.battery)
        self.water = min(self.water + collected_water, self.tank)

    def spend(self, energy=0, water=0):
        # - gives what the store holds
        # - a gap is unmet need
        
        energy_given = min(energy, self.energy)
        water_given = min(water, self.water)

        self.energy -= energy_given
        self.water -= water_given

        return {"energy": energy_given, "water": water_given}

    def __repr__(self):
        return f"Building({self.name!r}, energy={self.energy}, water={self.water})"
