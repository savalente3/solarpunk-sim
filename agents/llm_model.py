"""The LLM model the agents think with, and how they ask it.

The building managers and the shop call their models the same way: each answer
held to a shape, each call named for LangSmith, a model that cannot be reached
stopping the run, and an answer that cannot be read recorded as such.
"""
import time

import openai
from langchain.chat_models import init_chat_model
from langchain_core.rate_limiters import InMemoryRateLimiter


class ModelUnavailable(Exception):
    """The model could not be reached even after retrying: the run stops here."""


class LLMModel:
    # - at most this many calls a minute, so no model is flooded
    calls_per_minute = 10

    # - answers an earlier try of this run recorded, waiting to be given again,
    #   in the same order, when a paused run resumes -- one queue for each agent
    recorded = {}

    def __init__(self, model_config):
        # - how this model's answers are held to a shape is set per model
        # - Ollama only reads the cap on an answer's length under its old name,
        #   max_tokens; the client renames it on the way, so it is sent as it is
        config = dict(model_config)
        self.structured = config.pop("structured", "function_calling")
        cap = config.pop("max_tokens", None)
        
        if cap is not None:
            config["extra_body"] = {"max_tokens": cap}

        limiter = InMemoryRateLimiter(
            requests_per_second=self.calls_per_minute / 60,
            check_every_n_seconds=0.1,
            max_bucket_size=1,
        )
        self.chat = init_chat_model(**config, rate_limiter=limiter)

    def agent(self, shape):
        # - an agent on this model, its answers held to one shape
        return self.chat.with_structured_output(shape, method=self.structured, include_raw=True)

    @classmethod
    def replay(cls, exchanges):
        # - resuming a paused run: the answers it recorded are handed back in order
        #   instead of asking the models again, so the settlement comes out the same
        #   week for week until the recording runs out and the models take over
        
        for exchange in exchanges:
            if exchange["agent"] == "shop":
                key = ("shop", "shop")
            else:
                key = (f"building {exchange['place']}", exchange["agent"])
            cls.recorded.setdefault(key, []).append(exchange)

    def ask(self, agent, instructions, message, who, place, sees):
        # - one call: the answer as a plain dict, or None if it could not be read,
        #   and a record of exactly what was shown and what came back
        # - named and tagged, so each call can be found in LangSmith by place,
        #   agent, week and day
        # - a model that cannot be reached stops the run; an answer that came
        #   back but cannot be read is only recorded, and changes nothing

        # - a recorded answer is only given again if the agent is shown exactly what
        #   it was shown before; if not, the run has gone another way, and every
        #   answer from here on comes from the models
        waiting = self.recorded.get((place, who))
        if waiting:
            before = waiting.pop(0)
            
            if before["shown"] == message:
                exchange = {}
                
                for key in ("agent", "shown", "answer", "unreadable", "tokens_in", "tokens_out", "seconds"):
                    exchange[key] = before.get(key)
                return before["answer"], exchange
            
            self.recorded.clear()
            print(f"resume: the {who} of {place} is shown something new, so the models take over from here")

        started = time.monotonic()
        answer = None
        unreadable = None
        usage = {}

        try:
            reply = agent.invoke(
                [("system", instructions), ("human", message)],
                config={
                    "run_name": f"{place} · {who} · week {sees['week']} day {sees['day']}",
                    "tags": [place, who, sees["season"]],
                    "metadata": {
                        "place": place,
                        "agent": who,
                        "week": sees["week"],
                        "day": sees["day"],
                        "season": sees["season"],
                    },
                },
            )
        except openai.InternalServerError as error:
            # - Ollama answers with a server error when it cannot parse what the
            #   model wrote: that is an answer that cannot be read, not a model
            #   that cannot be reached
            if "error parsing" not in str(error):
                raise ModelUnavailable(f"the {who} of {place} could not be reached: {error}")
            unreadable = str(error)[:500]
        
        except openai.APIError as error:
            raise ModelUnavailable(f"the {who} of {place} could not be reached: {error}")
        
        except (ValueError, openai.OpenAIError) as error:
            unreadable = str(error)[:500]
        
        else:
            usage = reply["raw"].usage_metadata or {}
            
            if reply["parsed"] is not None:
                answer = reply["parsed"].model_dump()
            elif reply["parsing_error"] is not None:
                unreadable = str(reply["parsing_error"])
            else:
                unreadable = "no answer in the required shape: " + str(reply["raw"].content)[:300]

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
