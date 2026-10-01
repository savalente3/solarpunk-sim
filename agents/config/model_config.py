"""Model configs for init_chat_model: the three models the settlement runs on.

All three run on this machine through Ollama's OpenAI-compatible endpoint, so
model_provider is "openai" and none needs a key (api_key_env is None; a
profile for a hosted model would name the .env variable holding its key).
The models never leave the computer (LangSmith tracing, if
switched on in .env, still copies each prompt and answer to LangSmith).
`structured` is how the answer shape is held -- some models manage it as a
tool call, others only when it is enforced as they write. `reasoning_effort`
keeps thinking to a minimum: "none" switches it off for Gemma and Nemotron,
and "low" is the least gpt-oss allows -- it cannot switch reasoning off.
`max_tokens` caps each answer, the same for every model: above all but the
rarest long answer, but a model caught in a loop stops within a few minutes
instead of writing until the request times out and the run pauses.
"""
import os

from dotenv import load_dotenv

model_configs = {
    # - local, through Ollama: building 1, building 2 and the shop
    "gpt_oss_local": {
        "model": "gpt-oss:20b",
        "model_provider": "openai",
        "base_url": "http://localhost:11434/v1",
        "api_key_env": None,
        "temperature": 0.0,
        "timeout": 600,
        "max_retries": 2,
        "max_tokens": 8192,
        "structured": "json_schema",
        "reasoning_effort": "low",
    },
    "gemma_local": {
        "model": "gemma4:26b",
        "model_provider": "openai",
        "base_url": "http://localhost:11434/v1",
        "api_key_env": None,
        "temperature": 0.0,
        "timeout": 600,
        "max_retries": 2,
        "max_tokens": 8192,
        "structured": "json_schema",
        "reasoning_effort": "none",
    },
    "nemotron_local": {
        "model": "nemotron-3.5-lightning",
        "model_provider": "openai",
        "base_url": "http://localhost:11434/v1",
        "api_key_env": None,
        "temperature": 0.0,
        "timeout": 600,
        "max_retries": 2,
        "max_tokens": 8192,
        "structured": "json_schema",
        "reasoning_effort": "none",
    },
}


def load_models():
    load_dotenv()

    models = {}
    for name, config in model_configs.items():
        config = dict(config)
        key = config.pop("api_key_env")
        # - a local model needs no key, but the client wants one; a hosted
        #   model without its key in .env is skipped
        if key is None:
            config["api_key"] = "local"
        elif not os.environ.get(key):
            continue
        else:
            config["api_key"] = os.environ[key]
        models[name] = config
    return models
