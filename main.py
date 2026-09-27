"""Run a year of the settlement, print every week, and record it.

    python main.py --seed 0 --condition baseline

writes three files per run, each week as it finishes, so a run can be read
while it is going:

    data/seed-0-baseline.jsonl   for code: a _meta line, then one line per week
    data/seed-0-baseline.csv     for graphs: one flat row per place per day
    data/seed-0-baseline.txt     for reading: exactly what is printed
"""
import argparse
import csv
import json
import random
from datetime import date
from pathlib import Path

from agents.building_managers import BuildingManagers, ModelUnavailable
from agents.config.model_config import load_models
from agents.prompts import allotment_manager, building_manager
from settlement.allotment import Allotment
from settlement.board import describe, heading
from settlement.building import Building
from settlement.community import Community
from settlement.shop import Shop


columns = [
    "seed", "condition", "week", "day", "day_of_year", "season", "place", "alive",
    "battery_pct", "tank_pct", "food_pct", "greywater_pct",
    "energy", "water", "greywater", "food_kg", "stock_kg", "crops_held",
    "beds_growing", "beds_empty", "allotment_kg", "days_without_water", "days_without_food",
    "allowed_energy", "allowed_water", "allowed_food", "beds_water", "beds_greywater", "beds_energy",
]


def rows(record, meta):
    # - one flat row per place per day, for spreadsheets and plots
    # - a column that does not apply to a place is left empty
    for state in record["days"]:
        for place in ("1", "2", "shop"):
            now = state[place]
            row = {
                "seed": meta["seed"],
                "condition": meta["condition"],
                "week": record["week"],
                "day": state["day"],
                "day_of_year": record["week"] * 7 + state["day"],
                "season": record["season"],
                "place": place,
                "energy": now["energy"],
                "water": now["water"],
                "battery_pct": now["levels"]["battery"],
                "tank_pct": now["levels"]["tank"],
            }

            if place == "shop":
                stock = now["stock"]
                row["stock_kg"] = round(sum(lot["kg"] for lot in stock.values()), 2)
                row["crops_held"] = len(stock)
            else:
                food = now["food"]
                produce = now["allotment_produce"]
                row["alive"] = now["alive"]
                row["food_pct"] = now["levels"]["food"]
                row["greywater_pct"] = now["levels"]["greywater"]
                row["greywater"] = now["greywater"]
                row["food_kg"] = round(sum(lot["kg"] for lot in food.values()), 2)
                row["crops_held"] = len(food)
                row["beds_growing"] = sum(now["beds"]["growing"].values())
                row["beds_empty"] = now["beds"]["empty"]
                row["allotment_kg"] = round(sum(lot["kg"] for lot in produce.values()), 2)
                row["days_without_water"] = now["tenants"]["days_without_water"]
                row["days_without_food"] = now["tenants"]["days_without_food"]

                # - what the manager has decided, in force that day
                allowed = now["rules"]["tenants"]
                row["allowed_energy"] = allowed["energy"]
                row["allowed_water"] = allowed["water"]
                row["allowed_food"] = allowed["food"]
                if now["rules"]["beds"] is not None:
                    row["beds_water"] = now["rules"]["beds"]["water"]
                    row["beds_greywater"] = now["rules"]["beds"]["greywater"]
                    row["beds_energy"] = now["rules"]["beds"]["energy"]

            yield row


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--condition", default="baseline")
    arguments = parser.parse_args()

    rng = random.Random(arguments.seed)

    # - which model runs which place
    # - a baseline run has no agents, so it needs no models and no keys
    profiles = {"1": "nemotron_super", "2": "gemini", "shop": "gpt_oss"}
    configs = {}

    if arguments.condition == "baseline":
        for place in profiles:
            configs[place] = None
    else:
        models = load_models()
        for place, profile in profiles.items():
            if profile not in models:
                raise SystemExit(f"no API key for {profile} -- fill it in .env (see .env.example)")
            configs[place] = models[profile]

    # - each roof opens on two crops drawn from the six, fixed by the seed
    # - each building gets its two agents on its model, or none in a baseline run
    buildings = []
    for place in ("1", "2"):
        managers = BuildingManagers(place, configs[place]) if configs[place] else None
        buildings.append(Building(place, rng.sample(Allotment.crops, 2), managers))

    # - the shop opens on a little of every crop; its agent comes later
    shop = Shop(Allotment.crops)
    community = Community(buildings, shop)

    # - two files per run: data for code, and the printout for reading
    # - model names only, never the configs, which carry the api keys
    folder = Path(__file__).parent / "data"
    folder.mkdir(exist_ok=True)
    name = f"seed-{arguments.seed}-{arguments.condition}"

    meta = {
        "seed": arguments.seed,
        "condition": arguments.condition,
        "date": date.today().isoformat(),
        "models": {},
        "crops": {
            "1": list(buildings[0].food.kinds()),
            "2": list(buildings[1].food.kinds()),
            "shop": list(shop.stock.kinds()),
        },
    }
    for place, config in configs.items():
        meta["models"][place] = config["model"] if config else None

    # - the agents' standing instructions, as given, so every run records them
    if arguments.condition != "baseline":
        meta["instructions"] = {"building manager": building_manager("1"), "allotment manager": allotment_manager("1")}

    with open(folder / f"{name}.jsonl", "w") as data, open(folder / f"{name}.txt", "w") as text, \
            open(folder / f"{name}.csv", "w", newline="") as table:
        data.write(json.dumps({"_meta": meta}) + "\n")

        sheet = csv.DictWriter(table, fieldnames=columns)
        sheet.writeheader()

        top = heading(meta)
        print(top + "\n")
        text.write(top + "\n\n")

        try:
            for record in community.run_year(rng):
                data.write(json.dumps(record) + "\n")
                data.flush()

                sheet.writerows(rows(record, meta))
                table.flush()

                week = describe(record)
                print(week + "\n")
                text.write(week + "\n\n")
                text.flush()

        # - a model that cannot be reached stops the run cleanly: every finished
        #   week is already on disk
        except ModelUnavailable as error:
            paused = f"PAUSED    {error}"
            print(paused)
            text.write(paused + "\n")

    print(f"written to data/{name}.jsonl, .csv and .txt")
