"""The allotment: the beds on the roof, what grows in them, what they yield.

The allotment keeps what it harvests. The water and the power come out of the
building, and the allotment trades its produce for them -- which is what the
two managers have to agree on.
"""
from settlement.produce import Produce


class Allotment:
    # - every crop grows and drinks the same, only the name differs
    crops = ("tomato", "carrot", "potato", "broccoli", "beans", "lettuce")

    # - one bed holds one crop, and a roof grows a few kinds at most at once
    bed_area = 10           # square metres
    crop_limit = 3

    # - what the beds want
    irrigation_rate = 35    # litres per square metre on a dry week
    energy_rate = 15        # kWh a week to run the allotment's automation
    seed_thirst = 0.2   # share a bare bed drinks against a ripe one

    # - the cycle
    growth_weeks = 3        # weeks from seed to ripe
    crop_yield = 1          # kg per square metre

    # - a bed getting less than this share of what it needs is having a dry day,
    #   and enough dry days in a row kill it
    dry_share = 0.5
    wilt_days = 7

    def __init__(self, area, crops):
        self.area = area
        self.beds = [None] * (area // self.bed_area)
        self.produce = Produce()

        # - the roof starts worked, the building's crops alternating across the beds
        for index in range(len(self.beds)):
            self.plant(index, crops[index % len(crops)])

    def needs(self, weather, fraction=1.0):
        # - rain waters the beds
        # - thirst grows with the crop
        # - the allotment runs either way
        # - the fraction is how much of the week

        water = 0
        if weather.intensity["rain"] == 0:
            for bed in self.beds:
                if bed is not None:
                    share = self.seed_thirst + (1 - self.seed_thirst) * bed["maturity"]
                    water += self.bed_area * self.irrigation_rate * share * fraction

        return {"water": round(water, 2), "energy": round(self.energy_rate * fraction, 2)}

    def plant(self, index, crop):
        # - a bare bed starts at nothing
        # - says whether it planted: an unknown crop, or a new kind past the
        #   limit, is refused

        growing = set()
        for bed in self.beds:
            if bed is not None:
                growing.add(bed["crop"])

        if crop not in self.crops:
            return False
        if crop not in growing and len(growing) >= self.crop_limit:
            return False

        self.beds[index] = {"crop": crop, "maturity": 0.0, "dry": 0}
        return True

    def grow(self, weather, water_given, energy_given, fraction=1.0):
        # - short water means slow growth
        # - short power means the automation tends the beds less
        # - a bed kept short too long dies, and what it had grown is lost
        # - the fraction is how much of the week has passed

        wanted = self.needs(weather, fraction)
        watered = 1.0 if wanted["water"] == 0 else min(1.0, water_given / wanted["water"])
        powered = min(1.0, energy_given / wanted["energy"])
        share = watered * powered
        died = []

        for index, bed in enumerate(self.beds):
            if bed is None:
                continue

            if share < self.dry_share:
                bed["dry"] += 1
            else:
                bed["dry"] = 0

            if bed["dry"] >= self.wilt_days:
                lost = round(self.bed_area * self.crop_yield * bed["maturity"], 2)
                died.append({"crop": bed["crop"], "kg": lost})
                self.beds[index] = None
                continue

            bed["maturity"] = min(1.0, bed["maturity"] + share * fraction / self.growth_weeks)

        return died

    def summary(self):
        # - the beds at a glance: what is growing and how many of each, what
        #   stands empty, and each bed's crop, growth and dry days
        growing = {}
        beds = []
        furthest = None
        driest = 0
        for bed in self.beds:
            if bed is None:
                beds.append(None)
                continue
            growing[bed["crop"]] = growing.get(bed["crop"], 0) + 1
            beds.append({"crop": bed["crop"], "grown": round(bed["maturity"] * 100), "dry_days": bed["dry"]})
            furthest = max(furthest or 0, round(bed["maturity"] * 100))
            driest = max(driest, bed["dry"])

        return {
            "growing": growing,
            "empty": len(self.bare()),
            "furthest": furthest,
            "driest": driest,
            "driest_dies_in": self.wilt_days - driest if driest else None,
            "beds": beds,
        }

    def bare(self):
        # - which beds are empty, waiting to be planted
        empty = []

        for index, bed in enumerate(self.beds):
            if bed is None:
                empty.append(index)

        return empty

    def ripe(self):
        # - which beds are ready to pick
        ready = []

        for index, bed in enumerate(self.beds):
            if bed is not None and bed["maturity"] >= 1.0:
                ready.append(index)

        return ready

    def harvest(self, index, today):
        # - clear the bed and keep what it grew, dated the day it was picked

        bed = self.beds[index]
        self.beds[index] = None

        kg = self.bed_area * self.crop_yield
        self.produce.take([{"crop": bed["crop"], "kg": kg, "picked": today}])

        return {"crop": bed["crop"], "kg": kg}

    def __repr__(self):
        return f"Allotment(area={self.area} m2, beds={len(self.beds)}, produce={self.produce.total()} kg)"
