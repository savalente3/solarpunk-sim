"""A building: what it collects from the weather, and what it can hold.

The battery and the tank belong to the building. The allotment on its roof
draws from them too, which is what the two managers have to agree on.
"""
from settlement.allotment import Allotment
from settlement.infrastructure import Infrastructure
from settlement.produce import Produce, move


class Building(Infrastructure):
    # - storage limits beyond the roof's
    greywater_tank = 500    # litres recovered off the residents
    food_storage = 30       # kg of produce -- about five weeks of eating, more than keeps

    # - what the tenants want in a week
    # - food is the vegetable part of the diet only, about two people's five a day
    tenant_needs = {"energy": 210, "water": 1400, "food": 6}

    # - the share of what the residents wash with that comes back usable
    greywater_share = 0.33

    # - days in a row the tenants can go short before they are gone
    thirst_limit = 3
    hunger_limit = 21

    # - rationed is survivable; below this share of their need, a day counts as going without
    survival_share = 0.25

    def __init__(self, name, crops, managers=None):
        super().__init__()
        self.name = name

        # - the tenants live or die together, and the building with them
        self.alive = True
        self.days_without_water = 0
        self.days_without_food = 0

        # - what the building manager has decided, in force until it decides again:
        #   the share of their need the tenants may use, and what the beds get each day
        # - no bed supply yet means no one has decided, and the beds take what they need
        self.allowance = {"energy": 1.0, "water": 1.0, "food": 1.0}
        self.bed_supply = None

        # - whether the manager asked to be checked on, rather than left to the routine
        self.check_asked = False

        # - what the tenants and the beds needed today, a day's worth each
        self.need_today = None

        # - the food storage starts half full, split across the crops the roof grows,
        #   and ages from the day the run starts
        self.food = Produce(self.food_storage)
        opening = []
        for crop in crops:
            opening.append({"crop": crop, "kg": round(self.food_storage / 2 / len(crops), 2), "picked": 0})
        self.food.take(opening)

        self.greywater = self.greywater_tank // 2

        # - beds take what the panels leave
        self.allotment = Allotment(self.roof_area - self.panel_area, crops)
        # - the building's two agents, handed in; none means a baseline run
        self.managers = managers

    def needs(self, rate, fraction=1.0):
        # - rate comes from the week, the fraction is how much of the week
        
        wanted = {}
        for name, amount in self.tenant_needs.items():
            wanted[name] = round(amount * rate * fraction, 2)

        return wanted

    def survive(self, wanted, got):
        # - a day with almost none of their water or food counts, a day with more resets it
        # - enough of those days in a row and the tenants are gone
        # - wanted is their full need, so rationing above the line is survivable

        eaten = round(sum(got["food"].values()), 2)

        if got["water"] < wanted["water"] * self.survival_share:
            self.days_without_water += 1
        else:
            self.days_without_water = 0

        if eaten < wanted["food"] * self.survival_share:
            self.days_without_food += 1
        else:
            self.days_without_food = 0

        if self.days_without_water >= self.thirst_limit:
            self.alive = False
            return "no water"

        if self.days_without_food >= self.hunger_limit:
            self.alive = False
            return "no food"

        return None

    def levels(self):
        # - the roof's storage, and the food storage
        levels = super().levels()
        levels["food"] = self.food.total() / self.food_storage
        return levels

    def spend(self, energy=0, water=0, food=0, greywater=0):
        # - the roof's storage first, then the food storage and the greywater
        given = super().spend(energy, water)

        # - the tenants eat across the food storage, oldest first within each crop
        eaten = self.food.eat(food)

        greywater_given = min(greywater, self.greywater)
        self.greywater -= greywater_given

        given["food"] = eaten
        given["greywater"] = greywater_given
        return given

    def recover(self, water_used):
        # - what the residents wash with comes back, up to what the tank holds
        recovered = round(water_used * self.greywater_share)
        self.greywater = min(self.greywater + recovered, self.greywater_tank)

    def snapshot(self, today):
        # - what the building looks like right now: what its manager is shown
        levels = {}
        for storage, level in self.levels().items():
            levels[storage] = round(level * 100, 1)
        levels["greywater"] = round(self.greywater / self.greywater_tank * 100, 1)

        # - how long the tenants have gone short, and how long they have left
        tenants = {"days_without_water": self.days_without_water, "days_without_food": self.days_without_food}
        if self.days_without_water:
            tenants["water_dies_in"] = self.thirst_limit - self.days_without_water
        if self.days_without_food:
            tenants["food_dies_in"] = self.hunger_limit - self.days_without_food

        return {
            "alive": self.alive,
            "levels": levels,
            "energy": round(self.energy, 2),
            "water": round(self.water, 2),
            "greywater": round(self.greywater, 2),
            "need_per_day": self.need_today,
            "rules": {"tenants": dict(self.allowance), "beds": dict(self.bed_supply) if self.bed_supply else None},
            "food": self.food.summary(today),
            "tenants": tenants,
            "beds": self.allotment.summary(),
            "allotment_produce": self.allotment.produce.summary(today),
        }

    def apply(self, decision, today):
        # - carry out the manager's decision: what to do now, what holds until it
        #   next decides, and when to check again
        # - says what could not be done, and why, so the manager is told next time
        refused = []

        for request in decision["now"]["move_to_food_storage"]:
            moved = move(self.allotment.produce, self.food, request["crop"], request["kg"])
            if moved < request["kg"]:
                refused.append(
                    f"move {request['kg']} kg {request['crop']} into food storage: "
                    f"only {moved} kg moved (not that much held, or no room)"
                )

        for planting in decision["now"]["plant"]:
            planted = 0
            for index in self.allotment.bare():
                if planted == planting["beds"] or not self.allotment.plant(index, planting["crop"]):
                    break
                planted += 1

            if planted < planting["beds"]:
                if self.allotment.bare():
                    reason = f"a roof grows at most {self.allotment.crop_limit} kinds at once"
                else:
                    reason = "no more empty beds"
                refused.append(f"plant {planting['beds']} beds of {planting['crop']}: only {planted} planted ({reason})")

        tenants = decision["until_next_time"]["tenants"]
        self.allowance = {"energy": tenants["energy"], "water": tenants["water"], "food": tenants["food"]}

        beds = decision["until_next_time"]["beds"]
        self.bed_supply = {
            "water": beds["water_per_day"],
            "greywater": beds["greywater_per_day"],
            "energy": beds["energy_per_day"],
        }

        self.next_check = today + decision["check_again_in_days"]
        self.check_asked = True

        return refused

    def __repr__(self):
        return f"Building({self.name!r}, energy={self.energy}, water={self.water}, greywater={self.greywater}, food={self.food.kinds()})"
