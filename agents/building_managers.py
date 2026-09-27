"""A building is run by two agents on the same model: the allotment manager says
what the beds need, and the building manager decides for the whole building."""
import time

import openai
from langchain.chat_models import init_chat_model
from langchain_core.rate_limiters import InMemoryRateLimiter

from agents.decisions import AllotmentAnswer, BuildingDecision
from agents.prompts import allotment_manager, building_manager, manager_message, wake_message


class ModelUnavailable(Exception):
    # - the model could not be reached even after retrying: the run stops here
    pass


class BuildingManagers:
    # - calls a minute to one model, kept under the free tiers' limits
    calls_per_minute = 10

    # - how the answer shapes are enforced: as a tool the model must call
    structured = "function_calling"

    def __init__(self, name, model_config):
        self.name = name

        limiter = InMemoryRateLimiter(
            requests_per_second=self.calls_per_minute / 60,
            check_every_n_seconds=0.1,
            max_bucket_size=1,
        )
        model = init_chat_model(**model_config, rate_limiter=limiter)

        self.allotment_agent = model.with_structured_output(AllotmentAnswer, method=self.structured, include_raw=True)
        self.manager_agent = model.with_structured_output(BuildingDecision, method=self.structured, include_raw=True)

        # - what the manager last decided, and what of it could not be carried out
        self.previous = None
        self.refused = []

    def decide(self, sees, why):
        # - the allotment manager says what the beds need, then the building manager decides
        # - returns what was said, and the decision -- or None if it could not be read
        message = wake_message(sees, why)

        answer, heard = self.ask(self.allotment_agent, allotment_manager(self.name), message, "allotment manager")
        decision, decided = self.ask(
            self.manager_agent,
            building_manager(self.name),
            manager_message(message, answer, self.previous, self.refused),
            "building manager",
        )

        if decision is not None:
            self.previous = decision
        return [heard, decided], decision

    def ask(self, agent, instructions, message, who):
        # - one call: the answer as a plain dict, or None if it could not be read,
        #   and a record of exactly what was shown and what came back
        started = time.monotonic()
        try:
            reply = agent.invoke([("system", instructions), ("human", message)])
        except openai.APIError as error:
            raise ModelUnavailable(f"the {who} of building {self.name} could not be reached: {error}")

        answer = None
        unreadable = None
        if reply["parsed"] is not None:
            answer = reply["parsed"].model_dump()
        elif reply["parsing_error"] is not None:
            unreadable = str(reply["parsing_error"])
        else:
            unreadable = "no answer in the required shape: " + str(reply["raw"].content)[:300]

        usage = reply["raw"].usage_metadata or {}
        exchange = {
            "agent": who,
            "shown": message,
            "answer": answer,
            "unreadable": unreadable,
            "tokens_in": usage.get("input_tokens"),
            "tokens_out": usage.get("output_tokens"),
            "seconds": round(time.monotonic() - started, 1),
        }
        return answer, exchange
