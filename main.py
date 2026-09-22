"""Run some days and print them."""
import random

from agents.config.model_config import load_models
from settlement.building import Building
from settlement.community import Community
from settlement.store import Store


def pairs(values):
    parts = []
    for key, value in values.items():
        parts.append(f"{key} {value}")
    return ", ".join(parts)


def describe(record):
    lines = [f"Day: {record['day']}"]
    for name, tanks in record["buildings"].items():
        lines.append("  " + f"Building {name}:".ljust(13) + pairs(tanks))
        lines.append("    " + "weather:".ljust(11) + pairs(record["weather"][name]))
        lines.append("    " + "tenants:".ljust(11) + pairs(record["tenants"][name]))

    return "\n".join(lines)


if __name__ == "__main__":
    rng = random.Random(0)
    models = load_models()

    buildings = [Building("1", models["nemotron_super"]), Building("2", models["gemini"])]
    store = Store(models["gpt_oss"])
    community = Community(buildings, store)

    for day in range(1):
        print(describe(community.run_day(day, rng)))
        print()

    question = "Say in one sentence who you are."

    for building in buildings:
        print(f"Building {building.name} manager: " + building.managers.ask(building.managers.manager_agent, question))
        print(f"Building {building.name} allotment: " + building.managers.ask(building.managers.allotment_agent, question))

    print("Store manager: " + store.manager.ask(store.manager.agent, question))
