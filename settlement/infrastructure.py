"""Infrastructure: a roof that catches the weather, and what it can hold.

Anything in the settlement with panels and a cistern -- the buildings and the
shop both -- collects the same way and pays out the same way.
"""


class Infrastructure:
    # - roof space in square metres
    roof_area = 200
    panel_area = 60

    # - yield in a week at intensity 1.0
    panel_yield = 7.28      # kWh per square metre of panel
    rain_yield = 83.3       # litres per square metre of roof

    # - storage limits
    battery = 300           # kWh
    tank = 20000            # litres of rainwater

    def __init__(self):
        # - a year starts half full, so there is something to manage from week one
        self.energy = self.battery // 2
        self.water = self.tank // 2

        # - storages already below the alarm line, so they ring once, not every day
        self.low = set()

        # - the day this place is next due its routine check; an agent can bring it forward
        self.next_check = 0

    def collect(self, weather, fraction=1.0):
        # - sun and rain go into storage, a fraction of the week's at a time
        # - anything above capacity is lost

        collected_energy = round(weather.intensity["sun"] * self.panel_area * self.panel_yield * fraction)
        collected_water = round(weather.intensity["rain"] * self.roof_area * self.rain_yield * fraction)

        self.energy = min(self.energy + collected_energy, self.battery)
        self.water = min(self.water + collected_water, self.tank)

    def spend(self, energy=0, water=0):
        # - gives what the storage holds
        # - a gap is unmet need

        energy_given = min(energy, self.energy)
        water_given = min(water, self.water)

        self.energy -= energy_given
        self.water -= water_given

        return {"energy": energy_given, "water": water_given}

    def levels(self):
        # - how full each storage is, from 0 to 1
        return {"battery": self.energy / self.battery, "tank": self.water / self.tank}

    def receive(self, energy=0, water=0):
        # - takes what fits, and says how much it took

        energy_taken = min(energy, self.battery - self.energy)
        water_taken = min(water, self.tank - self.water)

        self.energy += energy_taken
        self.water += water_taken

        return {"energy": energy_taken, "water": water_taken}
