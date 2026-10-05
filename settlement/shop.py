"""The shop: the produce the buildings trade through.

Buildings hand over what they have too much of and take back kinds they are
short of, so the shop is what lets variety move around the settlement. It has
a roof like the buildings, runs itself on its own panels, and needs no water --
so what its cistern catches is there to give.
"""
from settlement.infrastructure import Infrastructure
from settlement.produce import Produce


class Shop(Infrastructure):
    # - storage limit for produce
    capacity = 500          # kg of produce

    # - what the shop burns on itself in a week
    energy_use = 50         # kWh, refrigeration and lighting

    # - what the shop opens with, of every crop
    opening_kg = 5

    def __init__(self, crops, manager=None):
        super().__init__()

        # - the shop opens on a little of every crop: variety rather than volume,
        #   small enough to be eaten before it rots, and ageing from the day the run starts
        self.stock = Produce(self.capacity)
        opening = []

        for crop in crops:
            opening.append({"crop": crop, "kg": self.opening_kg, "picked": 0})
        
        self.stock.take(opening)

        # - the shop's agent, handed in; none means it is not run by an agent
        self.manager = manager

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
