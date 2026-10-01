"""The shop is run by one agent, called on by a building manager when it wants
something. It looks after both buildings."""
from agents.llm_model import LLMModel
from agents.decisions import ShopAnswer
from agents.prompts import shop_manager, shop_message


class ShopManager:

    def __init__(self, model_config):
        self.model = LLMModel(model_config)
        self.agent = self.model.agent(ShopAnswer)

    def answer(self, sees, name, request, sent):
        # - a building has called on the shop: it answers, knowing how both buildings stand
        # - returns what it gives, or None if its answer could not be read, and what was said
        return self.model.ask(self.agent, shop_manager(), shop_message(sees, name, request, sent), "shop", "shop", sees)
