"""The allotment: the beds on the roof, what grows in them, what they yield.

The allotment holds no resources of its own -- the water and the power come
out of the building, which is what the two managers have to agree on.
"""


class Allotment:
    # - every crop grows and drinks the same, only the name differs
    crops = ("tomato", "carrot", "potato", "broccoli", "beans", "lettuce")

    # - one bed holds one crop
    bed_area = 10           # square metres

    # - what the beds want
    irrigation_rate = 63    # litres per square metre on a dry week
    energy_rate = 70        # kWh a week to run the allotment
    seedling_thirst = 0.2   # share a bare bed drinks against a ripe one

    # - the cycle
    growth_weeks = 3        # weeks from seed to ripe
    shelf_weeks = 2         # weeks a ripe bed stands before it dies
    crop_yield = 1          # kg per square metre

    def __init__(self, area):
        self.area = area
        self.beds = [None] * (area // self.bed_area)

    def needs(self, weather):
        # - rain waters the beds
        # - thirst grows with the crop
        # - the allotment runs either way

        water = 0
        if weather.intensity["rain"] == 0:
            for bed in self.beds:
                if bed is not None:
                    share = self.seedling_thirst + (1 - self.seedling_thirst) * bed["maturity"]
                    water += round(self.bed_area * self.irrigation_rate * share)

        return {"water": water, "energy": self.energy_rate}

    def plant(self, index, crop):
        # - a bare bed starts at nothing
        self.beds[index] = {"crop": crop, "maturity": 0.0, "standing": 0}

    def grow(self, weather, water_given):
        # - short water means slow growth
        # - ripe beds stand and then die

        wanted = self.needs(weather)["water"]
        share = 1.0 if wanted == 0 else min(1.0, water_given / wanted)
        died = []

        for index, bed in enumerate(self.beds):
            if bed is None:
                continue

            if bed["maturity"] < 1.0:
                bed["maturity"] = min(1.0, bed["maturity"] + share / self.growth_weeks)

            else:
                bed["standing"] += 1

                if bed["standing"] > self.shelf_weeks:
                    died.append(bed["crop"])
                    self.beds[index] = None

        return died

    def ripe(self):
        # - which beds are ready to pick
        ready = []

        for index, bed in enumerate(self.beds):
            if bed is not None and bed["maturity"] >= 1.0:
                ready.append(index)

        return ready

    def harvest(self, index):
        # - clear the bed and hand over what it grew

        bed = self.beds[index]
        self.beds[index] = None

        return {"crop": bed["crop"], "kg": self.bed_area * self.crop_yield}

    def __repr__(self):
        return f"Allotment(area={self.area} m2, beds={len(self.beds)})"
