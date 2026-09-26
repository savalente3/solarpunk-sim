"""A building: what it collects from the weather, and what it can hold.

The battery and the tank belong to the building. The allotment on its roof
draws from them too, which is what the two managers have to agree on.
"""
from agents.building_managers import BuildingManagers
from settlement.allotment import Allotment
from settlement.infrastructure import Infrastructure
from settlement.produce import Produce


class Building(Infrastructure):
    # - storage limits beyond the roof's
    greywater_tank = 500    # litres recovered off the residents
    food_storage = 200      # kg of produce

    # - what the tenants want in a week
    # - food is the vegetable part of the diet only, about two people's five a day
    tenant_needs = {"energy": 210, "water": 1400, "food": 6}

    # - the share of what the residents wash with that comes back usable
    greywater_share = 0.33

    # - days in a row the tenants can go short before they are gone
    thirst_limit = 3
    hunger_limit = 21

    def __init__(self, name, model_config, crops):
        super().__init__()
        self.name = name

        # - the tenants live or die together, and the building with them
        self.alive = True
        self.days_without_water = 0
        self.days_without_food = 0

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
        # - no model means no agents: a baseline run
        self.managers = BuildingManagers(name, model_config) if model_config else None

    def needs(self, rate, fraction=1.0):
        # - rate comes from the week, the fraction is how much of the week
        
        wanted = {}
        for name, amount in self.tenant_needs.items():
            wanted[name] = round(amount * rate * fraction, 2)

        return wanted

    def survive(self, wanted, got):
        # - a day short of water or food counts, a day with enough resets it
        # - enough short days in a row and the tenants are gone

        eaten = round(sum(got["food"].values()), 2)

        if got["water"] < wanted["water"]:
            self.days_without_water += 1
        else:
            self.days_without_water = 0

        if eaten < wanted["food"]:
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

        return {
            "alive": self.alive,
            "levels": levels,
            "energy": round(self.energy, 2),
            "water": round(self.water, 2),
            "greywater": round(self.greywater, 2),
            "food": self.food.summary(today),
            "tenants": {"days_without_water": self.days_without_water, "days_without_food": self.days_without_food},
            "beds": self.allotment.summary(),
            "allotment_produce": self.allotment.produce.summary(today),
        }

    def __repr__(self):
        return f"Building({self.name!r}, energy={self.energy}, water={self.water}, greywater={self.greywater}, food={self.food.kinds()})"
