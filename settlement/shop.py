"""The shop: the produce the buildings trade through.

Buildings hand over what they have too much of and take back kinds they are
short of, so the shop is what lets variety move around the settlement. It has
a roof like the buildings, runs itself on its own panels, and needs no water --
so what its cistern catches is there to give.
"""
from agents.shop_manager import ShopManager
from settlement.infrastructure import Infrastructure
from settlement.produce import Produce


class Shop(Infrastructure):
    # - storage limit for produce
    capacity = 500          # kg of produce

    # - what the shop burns on itself in a week
    energy_use = 50         # kWh, refrigeration and lighting

    def __init__(self, model_config, crops):
        super().__init__()

        # - the shop opens half full on the crops the roofs don't grow, so there is
        #   variety to offer from day one -- and it ages from the day the run starts
        self.stock = Produce(self.capacity)
        opening = []
        for crop in crops:
            opening.append({"crop": crop, "kg": round(self.capacity / 2 / len(crops), 2), "picked": 0})
        self.stock.take(opening)

        # - no model means no agent: a baseline run
        self.manager = ShopManager(model_config) if model_config else None

    def snapshot(self, today):
        # - what the shop looks like right now: what its agent is shown
        levels = {}
        for storage, level in self.levels().items():
            levels[storage] = round(level * 100, 1)

        return {
            "levels": levels,
            "energy": round(self.energy, 2),
            "water": round(self.water, 2),
            "stock": self.stock.summary(today),
        }

    def __repr__(self):
        return f"Shop(energy={self.energy}, water={self.water}, stock={self.stock.total()}/{self.capacity} kg)"
