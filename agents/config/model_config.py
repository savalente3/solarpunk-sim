"""Model configs for init_chat_model, and the env var each key comes from.

All three providers are OpenAI-compatible
model_provider is "openai" and only base_url changes. 
Keys are located in .env - api_key_env names the variable.
"""
import os

from dotenv import load_dotenv

model_configs = {
    "nemotron_super": {
        "model": "nvidia/nemotron-3-super-120b-a12b",
        "model_provider": "openai",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
        "temperature": 0.0,
        "timeout": 30,
        "max_retries": 2,
    },
    "nemotron_reasoning": {
        "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "model_provider": "openai",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
        "temperature": 0.0,
        "timeout": 30,
        "max_retries": 2,
    },
    "mistral_nemotron": {
        "model": "mistralai/mistral-nemotron",
        "model_provider": "openai",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
        "temperature": 0.0,
        "timeout": 30,
        "max_retries": 2,
    },
    "gpt_oss": {
        "model": "openai/gpt-oss-20b",
        "model_provider": "openai",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
        "temperature": 0.0,
        "timeout": 30,
        "max_retries": 2,
    },
    "gemini": {
        "model": "gemini-3.6-flash",
        "model_provider": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GOOGLE_API_KEY",
        "temperature": 0.0,
        "timeout": 30,
        "max_retries": 2,
    },
}


def load_models():
    load_dotenv()

    models = {}
    for name, config in model_configs.items():
        config = dict(config)
        key = config.pop("api_key_env")
        if not os.environ.get(key):
            continue        # no key for this provider, so skip it
        config["api_key"] = os.environ[key]
        models[name] = config
    return models
