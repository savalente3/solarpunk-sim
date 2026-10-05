"""Run a year of the settlement and record it, with one line a week in the terminal
and the whole run shown live in the browser.

    python main.py --seed 0 --condition no-memory

writes three files per run, each week as it finishes, so a run can be read
while it is going:

    data/seed-0-no-memory.jsonl   for code: a _meta line, then one line per week
    data/seed-0-no-memory.csv     for graphs: one flat row per place per day
    data/seed-0-no-memory.txt     for reading: the whole run written out week by week

While it runs, the settlement can be watched live: main.py serves the
visualisation itself and prints the address to open.
"""
import argparse
import csv
import json
import random
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from agents.building_managers import BuildingManagers
from agents.llm_model import LLMModel, ModelUnavailable
from agents.config.model_config import model_configs
from agents.prompts import allotment_manager, building_manager, shop_manager
from agents.shop_manager import ShopManager
from live import Watcher
from settlement.allotment import Allotment
from settlement.community_board import describe, heading, remembered
from settlement.building import Building
from settlement.community import Community
from settlement.shop import Shop


# - weeks in a year, for the progress line
weeks = len(Community.seasons) * Community.season_weeks

columns = [
    "seed", "condition", "week", "day", "day_of_year", "season", "place", "model", "alive",
    "battery_pct", "tank_pct", "food_pct", "greywater_pct",
    "energy", "water", "greywater", "food_kg", "stock_kg", "crops_held",
    "beds_growing", "beds_empty", "allotment_kg", "days_without_water", "days_without_food",
    "allowed_energy", "allowed_water", "allowed_food", "beds_water", "beds_greywater", "beds_energy",
]


def held_kg(held):
    # - kg held across every crop, from a storage's summary
    total = 0
    for lot in held.values():
        total += lot["kg"]
    return total


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
                "model": meta["models"][place],
                "energy": now["energy"],
                "water": now["water"],
                "battery_pct": now["levels"]["battery"],
                "tank_pct": now["levels"]["tank"],
            }

            if place == "shop":
                stock = now["stock"]
                row["stock_kg"] = round(held_kg(stock), 2)
                row["crops_held"] = len(stock)
            else:
                food = now["food"]
                produce = now["allotment_produce"]
                row["alive"] = now["alive"]
                row["food_pct"] = now["levels"]["food"]
                row["greywater_pct"] = now["levels"]["greywater"]
                row["greywater"] = now["greywater"]
                row["food_kg"] = round(held_kg(food), 2)
                row["crops_held"] = len(food)
                row["beds_growing"] = sum(now["beds"]["growing"].values())
                row["beds_empty"] = now["beds"]["empty"]
                row["allotment_kg"] = round(held_kg(produce), 2)
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
    parser.add_argument("--condition", choices=("no-memory", "memory"), default="no-memory")
    parser.add_argument("--resume", action="store_true", help="carry on a paused run from where it stopped")
    arguments = parser.parse_args()

    # - LangSmith tracing, if switched on in .env
    load_dotenv()

    rng = random.Random(arguments.seed)

    # - which model runs which place
    # - the two building models swap buildings on odd seeds, so each model runs
    #   each building on half the seeds and neither building's luck favours one
    profiles = {"1": "gpt_oss_local", "2": "gemma_local", "shop": "nemotron_local"}
    if arguments.seed % 2 == 1:
        profiles["1"], profiles["2"] = profiles["2"], profiles["1"]
    configs = {}

    for place, profile in profiles.items():
        configs[place] = model_configs[profile]

    # - each roof opens on two crops drawn from the six, fixed by the seed
    # - each building gets its two agents on its model
    buildings = []
    for place in ("1", "2"):
        buildings.append(Building(place, rng.sample(Allotment.crops, 2), BuildingManagers(place, configs[place])))

    # - the shop opens on a little of every crop, and is run by its own agent
    shop = Shop(Allotment.crops, ShopManager(configs["shop"]))
    community = Community(buildings, shop)

    # - the memory condition: the building managers are shown the community board,
    #   everything that has happened in the settlement so far
    if arguments.condition == "memory":
        community.remember = remembered

    # - three files per run: data for code, a table for graphs, and the printout for reading
    # - model names only, not the whole configs
    folder = Path(__file__).parent / "data"
    folder.mkdir(parents=True, exist_ok=True)
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
        meta["models"][place] = config["model"]

    # - the agents' standing instructions, as given, so every run records them
    meta["instructions"] = {
        "building manager": building_manager("1"),
        "allotment manager": allotment_manager("1"),
        "shop": shop_manager(),
    }

    # - resuming a paused run: the weeks it already has are run again with the
    #   answers it recorded, before the file is started afresh, and the models
    #   take over from the week it paused in
    if arguments.resume:
        exchanges = []
        recorded_weeks = 0
        earlier = folder / f"{name}.jsonl"
        if earlier.exists():
            for line in earlier.read_text().splitlines():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "events" not in record:
                    continue
                recorded_weeks += 1
                for event in record["events"]:
                    if event["event"] == "exchange":
                        exchanges.append(event)
        LLMModel.replay(exchanges)
        meta["resumed_after_week"] = recorded_weeks
        print(f"resuming: {recorded_weeks} weeks on file, their {len(exchanges)} answers given again before the models take over")

    # - the live view: everything the settlement does is passed to the browser as it happens
    watcher = Watcher(Path(__file__).parent)
    community.listener = watcher.tell
    watcher.tell("run", meta)

    with open(folder / f"{name}.jsonl", "w") as data, open(folder / f"{name}.txt", "w") as text, \
            open(folder / f"{name}.csv", "w", newline="") as table:
        data.write(json.dumps({"_meta": meta}) + "\n")
        data.flush()

        sheet = csv.DictWriter(table, fieldnames=columns)
        sheet.writeheader()

        text.write(heading(meta) + "\n\n")
        print(f"seed {arguments.seed} · {arguments.condition}")
        print(f"watch it live: {watcher.address() or 'no free port, so no live view this time'}")

        try:
            for record in community.run_year(rng):
                data.write(json.dumps(record) + "\n")
                data.flush()

                sheet.writerows(rows(record, meta))
                table.flush()

                text.write(describe(record) + "\n\n")
                text.flush()

                # - the terminal only says how far the run has got, and who is still there
                standing = []
                for place, building in record["buildings"].items():
                    standing.append(f"building {place} " + ("alive" if building["alive"] else "gone"))
                print(f"week {record['week'] + 1} of {weeks} · {record['season']} · " + ", ".join(standing))

        # - a model that cannot be reached stops the run cleanly: every finished
        #   week is already on disk
        except ModelUnavailable as error:
            paused = f"PAUSED    {error}"
            print(paused)
            text.write(paused + "\n")
            watcher.tell("paused", str(error))

    # - a moment for the browsers to hear the end before the view closes with the run
    watcher.tell("end", {"weeks": weeks})
    time.sleep(3)
    print(f"written to data/{name}.jsonl, .csv and .txt")
