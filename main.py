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

from agents.config.model_config import load_models
from settlement.allotment import Allotment
from settlement.building import Building
from settlement.community import Community
from settlement.shop import Shop


def pairs(values):
    parts = []
    for key, value in values.items():
        parts.append(f"{key} {value}")
    return ", ".join(parts)


def happened(event):
    # - one line saying what kind of thing happened, and to what
    if event["event"] == "alarm":
        line = round(Community.alarm_level * 100)
        return f"ALARM    {event['storage']} dropped below {line}% (now {event['level']}%)"

    if event["event"] == "wake":
        who = "shop agent" if event["place"] == "shop" else "manager"
        how = "by the alarm" if event["trigger"] == "alarm" else "on the 3-day check"
        return f"WAKE     {who} woken {how}: " + ", ".join(event["why"])

    if event["event"] == "tenants died":
        return f"DEATH    tenants died: {event['cause']}"

    if event["event"] == "bed died":
        return f"LOST     bed died of drought: {event['lost']}"

    if event["event"] == "rotted":
        return f"ROTTED   {event['lost']} went off"

    return event["event"]


def heading(meta):
    # - what the run is, at the top of the printout
    lines = [f"seed {meta['seed']} | {meta['condition']} | {meta['date']}"]

    models = []
    crops = []
    for place in ("1", "2", "shop"):
        name = place if place == "shop" else f"building {place}"
        models.append(f"{name} {meta['models'][place] or 'no agent'}")
        crops.append(f"{name} " + ", ".join(meta["crops"][place]))

    lines.append("models: " + " | ".join(models))
    lines.append("crops:  " + " | ".join(crops))
    return "\n".join(lines)


def held(summary):
    # - produce by crop, with the age of its oldest lot
    if not summary:
        return "nothing held"
    parts = []
    for crop, lot in summary.items():
        parts.append(f"{crop} {lot['kg']} kg ({lot['oldest_days']} days old)")
    return ", ".join(parts)


def seen(sees):
    # - what an agent was shown when it woke, a few lines under the wake
    levels = []
    for storage, level in sees["levels"].items():
        levels.append(f"{storage} {level}%")
    lines = ["sees  storage   " + " | ".join(levels)]

    if "stock" in sees:
        lines.append("      stock     " + held(sees["stock"]))
    else:
        beds = sees["beds"]
        growing = []
        grown = []
        for crop, count in beds["growing"].items():
            growing.append(f"{crop} {count}")
        for bed in beds["beds"]:
            if bed is not None:
                grown.append(bed["grown"])
        furthest = f" | furthest along {max(grown)}%" if grown else ""

        tenants = []
        for need in ("water", "food"):
            short = sees["tenants"][f"days_without_{need}"]
            if short:
                tenants.append(f"{short} days short of {need}")

        lines.append("      food      " + held(sees["food"]))
        lines.append(f"      beds      {sum(beds['growing'].values())} growing: " + ", ".join(growing) + f" | {beds['empty']} empty" + furthest)
        lines.append("      allotment " + held(sees["allotment_produce"]))
        lines.append("      tenants   " + (", ".join(tenants) or "fine"))

    weather = sees["weather"]
    rain = f"rain {weather['rain']}" if weather["rain"] else "no rain"
    lines.append(f"      weather   sun {weather['sun']}, {rain} | {sees['season']}, week {sees['week']}")
    return lines


columns = [
    "seed", "condition", "week", "day", "day_of_year", "season", "place", "alive",
    "battery_pct", "tank_pct", "food_pct", "greywater_pct",
    "energy", "water", "greywater", "food_kg", "stock_kg", "crops_held",
    "beds_growing", "beds_empty", "allotment_kg", "days_without_water", "days_without_food",
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

            yield row


def describe(record):
    lines = [f"Week {record['week']} ({record['season']})"]

    # - what happened, day by day, place by place
    days = {}
    for event in record["events"]:
        place = "shop" if event["place"] == "shop" else f"building {event['place']}"
        days.setdefault(event["day"], {}).setdefault(place, []).append(event)

    for day, places in days.items():
        lines.append(f"  day {day}")
        for place, happenings in places.items():
            lines.append(f"    {place}")
            for event in happenings:
                lines.append(f"      {happened(event)}")
                if "sees" in event:
                    for line in seen(event["sees"]):
                        lines.append(f"               {line}")

    # - where everything stands when the week is over
    lines.append("  end of week")

    for name, tanks in record["buildings"].items():
        if not tanks["alive"]:
            lines.append("    " + f"Building {name}:".ljust(13) + "empty, tenants gone")
            continue

        lines.append("    " + f"Building {name}:".ljust(13) + pairs(tanks))
        lines.append("      " + "weather:".ljust(16) + pairs(record["weather"][name]))

        for who in ("residents", "beds"):
            lines.append("      " + f"{who} want:".ljust(16) + pairs(record["wanted"][name][who]))
            lines.append("      " + f"{who} got:".ljust(16) + pairs(record["given"][name][who]))

        for picked in record["harvested"][name]:
            lines.append("      " + "harvested:".ljust(16) + f"{picked['kg']} kg {picked['crop']}")

    lines.append("    " + "Shop:".ljust(13) + pairs(record["shop"]))
    return "\n".join(lines)


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
    buildings = [
        Building("1", configs["1"], rng.sample(Allotment.crops, 2)),
        Building("2", configs["2"], rng.sample(Allotment.crops, 2)),
    ]

    # - the shop opens on the crops neither roof grows
    grown = set(buildings[0].food.kinds()) | set(buildings[1].food.kinds())
    others = []
    for crop in Allotment.crops:
        if crop not in grown:
            others.append(crop)
    shop = Shop(configs["shop"], others)
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

    with open(folder / f"{name}.jsonl", "w") as data, open(folder / f"{name}.txt", "w") as text, \
            open(folder / f"{name}.csv", "w", newline="") as table:
        data.write(json.dumps({"_meta": meta}) + "\n")

        sheet = csv.DictWriter(table, fieldnames=columns)
        sheet.writeheader()

        top = heading(meta)
        print(top + "\n")
        text.write(top + "\n\n")

        for record in community.run_year(rng):
            data.write(json.dumps(record) + "\n")
            data.flush()

            sheet.writerows(rows(record, meta))
            table.flush()

            week = describe(record)
            print(week + "\n")
            text.write(week + "\n\n")
            text.flush()

    print(f"written to data/{name}.jsonl, .csv and .txt")
