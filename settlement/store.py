"""The community store: the produce the buildings trade through.

Buildings hand over what they have too much of and take back kinds they are
short of, so the store is what lets variety move around the settlement.
"""
from agents.shop_manager import ShopManager


class Store:
    # - storage limit
    capacity = 500          # kg of produce

    def __init__(self, model_config):
        self.stock = {}     # crop name -> kg held

        self.manager = ShopManager(model_config)

    def __repr__(self):
        held = sum(self.stock.values())
        return f"Store(stock={held}/{self.capacity} kg)"
