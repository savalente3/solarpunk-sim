"""A building is run by two agents on the same model, with different roles."""
from langchain.chat_models import init_chat_model


class BuildingManagers:

    def __init__(self, name, model_config):
        self.name = name

        self.manager_agent = self.make_agent(model_config)
        self.allotment_agent = self.make_agent(model_config)

    def make_agent(self, model_config):
        return init_chat_model(**model_config)

    def ask(self, agent, prompt):
        return agent.invoke(prompt).content
