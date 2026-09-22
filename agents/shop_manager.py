"""The shop is run by one agent."""
from langchain.chat_models import init_chat_model


class ShopManager:

    def __init__(self, model_config):
        self.agent = self.make_agent(model_config)

    def make_agent(self, model_config):
        return init_chat_model(**model_config)

    def ask(self, agent, prompt):
        return agent.invoke(prompt).content
