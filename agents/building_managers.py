"""A building is run by two agents on the same model: the allotment manager says
what the beds need, and the building manager decides for the whole building."""
from agents.llm_model import LLMModel
from agents.decisions import AllotmentAnswer, BuildingDecision
from agents.prompts import allotment_manager, allotment_message, building_manager, manager_message, wake_message


class BuildingManagers:

    def __init__(self, name, model_config):
        self.name = name
        # - both agents run on the building's one model
        self.model = LLMModel(model_config)
        self.allotment_agent = self.model.agent(AllotmentAnswer)
        self.manager_agent = self.model.agent(BuildingDecision)

        # - what the manager last decided, what of it could not be carried out,
        #   and what the shop last said to this building
        self.previous = None
        self.refused = []
        self.shop_reply = None

    def decide(self, sees, why, said, board=None):
        # - the allotment manager says what the beds need, then the building manager decides
        # - in the memory condition the building manager also reads the community board
        # - each exchange is handed to said() the moment it comes back, so it can be
        #   recorded and watched live
        # - returns the decision, or None if it could not be read
        place = f"building {self.name}"
        message = wake_message(sees, why)

        answer, heard = self.model.ask(
            self.allotment_agent,
            allotment_manager(self.name),
            allotment_message(message, self.shop_reply),
            "allotment manager",
            place,
            sees,
        )
        said(heard)

        decision, decided = self.model.ask(
            self.manager_agent,
            building_manager(self.name),
            manager_message(message, answer, self.previous, self.refused, self.shop_reply, board),
            "building manager",
            place,
            sees,
        )

        said(decided)

        if decision is not None:
            self.previous = decision
        return decision
