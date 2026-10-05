"""How the models looked after their tenants, with and without memory: every
finished run in data/ measured, compared seed by seed, and drawn.

    python evaluation.py

Writes into data/evaluation/:

    summary.csv          one row per place per run: how the tenants fared, what
                         the roof grew and wasted, what was traded
    tests.csv            paired comparisons, seed by seed: memory against no
                         memory for each model, and gpt-oss against Gemma in
                         each condition
    survival.png         weeks the tenants survived, run by run
    wellbeing.png        days without water or food, and the share of need met
    waste.png            what the roofs grew against what rotted or was lost
    memory_effect.png    each seed's change from no memory to memory
    shop.png             what the shop gave each model's building
    year_seed_N.png      one seed's year day by day: tanks and food storage

Only reads the run files: nothing is run and no model is called. A run still
going is left out of the tests and the graphs, and said so.
"""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import rankdata, wilcoxon

from settlement.community import Community

# - weeks in a whole run, to tell a finished run from one still going
weeks_in_year = len(Community.seasons) * Community.season_weeks

conditions = ("no-memory", "memory")

# - the models as the graphs call them, and their colours -- the same as the live view
models = ("gpt-oss", "gemma")
colours = {"gpt-oss": "#e8845c", "gemma": "#6fa3e8", "shop": "#a6d25a"}
names = {"gpt-oss": "gpt-oss", "gemma": "Gemma"}

columns = [
    "seed", "condition", "place", "model", "label", "weeks_recorded", "finished",
    "survived", "survived_weeks", "death_cause",
    "water_short_days", "food_short_days", "short_days",
    "water_met", "food_met", "energy_met", "rationed_days",
    "harvested_kg", "rotted_kg", "lost_kg", "wasted_kg", "wasted_share", "kinds_eaten",
    "sent_kg", "water_got", "produce_got_kg", "water_given", "produce_given_kg",
    "calls", "unreadable",
]

# - the measures compared between conditions and between models
tested = [
    ("survived_weeks", "weeks survived"),
    ("short_days", "days without water or food"),
    ("water_met", "% of water need met"),
    ("food_met", "% of food need met"),
    ("energy_met", "% of energy need met"),
    ("rationed_days", "days rationed"),
    ("wasted_kg", "kg rotted or lost"),
    ("kinds_eaten", "kinds of crop eaten a week"),
]


def label(model):
    # - the short name a model goes by in the tables and graphs
    if "gpt" in model:
        return "gpt-oss"
    
    if "gemma" in model:
        return "gemma"
    
    return model


def kg(held):
    # - total kg of a list of lots, a {crop: kg} mapping, or a {crop: {"kg": ...}} mapping
    total = 0

    if isinstance(held, dict):
        
        for value in held.values():
            
            if isinstance(value, dict):
                total += value.get("kg", 0)
            else:
                total += value
    else:

        for lot in held:
            total += lot["kg"]

    return total


def percent(part, whole):
    # - part of whole as a percentage, or nothing if there was no whole
    if not whole:
        return ""
    
    return round(100 * part / whole, 1)


def read_run(path):
    # - the run's _meta, and every week written so far
    # - a run still going may end mid-line, so a line that cannot be read is skipped
    meta = None
    weeks = []

    for line in path.read_text().splitlines():
        
        if not line.strip():
            continue
        
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        
        if "_meta" in record:
            meta = record["_meta"]
        else:
            weeks.append(record)

    return meta, weeks


def measure_building(meta, weeks, place):
    # - one building's row: how its tenants fared, what its roof grew and
    #   wasted, what it traded, and how its models answered
    row = {
        "seed": meta["seed"],
        "condition": meta["condition"],
        "place": place,
        "model": meta["models"][place],
        "label": label(meta["models"][place]),
        "weeks_recorded": len(weeks),
        "finished": len(weeks) == weeks_in_year,
    }

    # - when the tenants died, if they did
    died_at = None
    cause = ""
    
    for week in weeks:
        
        for event in week["events"]:
            
            if event["event"] == "tenants died" and event["place"] == place:
                died_at = week["week"] + (event["day"] + 1) / Community.days
                cause = event["cause"]
    
    row["survived"] = died_at is None
    row["survived_weeks"] = len(weeks) if died_at is None else round(died_at, 2)
    row["death_cause"] = cause

    # - day by day while they lived: going without, and being held short
    water_short = 0
    food_short = 0
    rationed = 0
    
    for week in weeks:
        
        for day in week["days"]:
            state = day[place]
            
            if not state["alive"]:
                continue
            
            if state["tenants"]["days_without_water"] > 0:
                water_short += 1
            
            if state["tenants"]["days_without_food"] > 0:
                food_short += 1
            
            for share in state["rules"]["tenants"].values():
                if share < 1:
                    rationed += 1
                    break

    row["water_short_days"] = water_short
    row["food_short_days"] = food_short
    row["short_days"] = water_short + food_short
    row["rationed_days"] = rationed

    # - week by week: what the tenants needed against what they got, and what
    #   the roof grew, rotted and lost
    wanted = {"energy": 0, "water": 0, "food": 0}
    got = {"energy": 0, "water": 0, "food": 0}
    harvested = 0
    rotted = 0
    lost = 0
    kinds = []
    
    for week in weeks:
        need = week["wanted"][place]["residents"]
        given = week["given"][place]["residents"]
        
        for resource in wanted:
            wanted[resource] += need.get(resource, 0)
        
        got["energy"] += given.get("energy", 0)
        got["water"] += given.get("water", 0)
        got["food"] += kg(given.get("food", {}))
        
        harvested += kg(week["harvested"][place])
        rotted += kg(week["rotted"][place])
        lost += kg(week["died"][place])

        if need.get("food", 0) > 0:
            eaten = 0
            
            for amount in given.get("food", {}).values():
                if amount > 0.05:
                    eaten += 1
            
            kinds.append(eaten)

    row["water_met"] = percent(got["water"], wanted["water"])
    row["food_met"] = percent(got["food"], wanted["food"])
    row["energy_met"] = percent(got["energy"], wanted["energy"])
    row["harvested_kg"] = round(harvested, 1)
    row["rotted_kg"] = round(rotted, 1)
    row["lost_kg"] = round(lost, 1)
    row["wasted_kg"] = round(rotted + lost, 1)
    row["wasted_share"] = percent(rotted + lost, harvested)
    row["kinds_eaten"] = round(sum(kinds) / len(kinds), 2) if kinds else ""

    # - trades with the shop, and the calls made for this building's two agents
    sent = 0
    water_got = 0
    produce_got = 0
    calls = 0
    unreadable = 0

    for week in weeks:

        for event in week["events"]:
            if event["place"] != place:
                continue

            if event["event"] == "trade":
                sent += kg(event["sent"])
                water_got += event["water"]
                produce_got += kg(event["produce"])

            if event["event"] == "exchange" and event["agent"] != "shop":
                calls += 1

                if event["answer"] is None:
                    unreadable += 1

    row["sent_kg"] = round(sent, 1)
    row["water_got"] = round(water_got)
    row["produce_got_kg"] = round(produce_got, 1)

    row["calls"] = calls
    row["unreadable"] = unreadable
    
    return row


def measure_shop(meta, weeks):
    # - the shop's row: what it gave both buildings, what rotted on its shelves, its calls
    row = {
        "seed": meta["seed"],
        "condition": meta["condition"],
        "place": "shop",
        "model": meta["models"]["shop"],
        "label": "shop",
        "weeks_recorded": len(weeks),
        "finished": len(weeks) == weeks_in_year,
    }

    water_given = 0
    produce_given = 0
    rotted = 0
    calls = 0
    unreadable = 0
    
    for week in weeks:
        rotted += kg(week["rotted"]["shop"])
        
        for event in week["events"]:
            
            if event["event"] == "trade":
                water_given += event["water"]
                produce_given += kg(event["produce"])
            
            if event["event"] == "exchange" and event["agent"] == "shop":
                calls += 1
                
                if event["answer"] is None:
                    unreadable += 1
    
    row["water_given"] = round(water_given)
    row["produce_given_kg"] = round(produce_given, 1)
    row["rotted_kg"] = round(rotted, 1)
    
    row["calls"] = calls
    row["unreadable"] = unreadable
    
    return row


def compare(rows):
    # - paired comparisons, seed by seed, over the finished runs:
    #   memory against no memory for each model, and gpt-oss against Gemma in
    #   each condition -- a Wilcoxon signed-rank test on each measure
    found = {}
    
    for row in rows:
        if row["place"] != "shop" and row["finished"]:
            found[(row["condition"], row["seed"], row["label"])] = row

    seeds = []
    
    for key in found:
        if key[1] not in seeds:
            seeds.append(key[1])
    
    seeds.sort()

    # - each comparison: what it compares, within what, and the pairs of rows, one per seed
    pairs = []
    
    for model in models:
        keys = []
        
        for seed in seeds:
            keys.append((("no-memory", seed, model), ("memory", seed, model)))
        
        pairs.append(("no memory → memory", names[model], keys))
    
    for condition in conditions:
        keys = []
        
        for seed in seeds:
            keys.append(((condition, seed, "gpt-oss"), (condition, seed, "gemma")))
        
        pairs.append(("gpt-oss → Gemma", condition, keys))

    tests = []
    for comparison, within, keys in pairs:
        
        for measure, meaning in tested:
            first = []
            second = []
            
            for key_first, key_second in keys:
                
                if key_first in found and key_second in found:
                    first_value = found[key_first][measure]
                    second_value = found[key_second][measure]
                    
                    if first_value != "" and second_value != "":
                        first.append(first_value)
                        second.append(second_value)

            changes = []
            differences = []
            
            for first_value, second_value in zip(first, second):
                
                changes.append(second_value - first_value)
                
                if second_value != first_value:
                    differences.append(second_value - first_value)

            test = {
                "comparison": comparison, "within": within, "measure": meaning, "pairs": len(first),
                "median_first": median(first), "median_second": median(second),
                "median_change": median(changes),
                "change_min": round(min(changes), 2) if changes else "",
                "change_max": round(max(changes), 2) if changes else "",
                "rank_biserial": rank_biserial(differences),
                "p_value": "", "note": "",
            }

            if len(first) < 2:
                test["note"] = "too few pairs"
            elif not differences:
                test["note"] = "no difference on any seed"
            else:
                test["p_value"] = round(float(wilcoxon(first, second, zero_method="wilcox").pvalue), 3)
                
                if len(first) < 6:
                    test["note"] = "under 6 pairs: p cannot fall below 0.05"
            
            tests.append(test)
    
    return tests


def median(values):
    # - the middle value, or nothing for no values
    if not values:
        return ""
    
    ordered = sorted(values)
    middle = len(ordered) // 2
    
    if len(ordered) % 2:
        return round(ordered[middle], 2)
    
    return round((ordered[middle - 1] + ordered[middle]) / 2, 2)


def rank_biserial(differences):
    # - the effect size of a paired Wilcoxon test: the ranks of the seeds that
    #   went up, less the ranks of those that went down, over all the ranks
    # - 1 when every seed went up, -1 when every seed went down, 0 when they balance
    # - ties are left out, as the test leaves them out
    
    if not differences:
        return ""
    
    ranks = rankdata([abs(difference) for difference in differences])
    up = 0
    down = 0
    
    for difference, rank in zip(differences, ranks):
        if difference > 0:
            up += rank
        else:
            down += rank
    
    return round(float((up - down) / (up + down)), 2)


def seeds_of(rows):
    # - the seeds among these rows, in order
    seeds = []
    
    for row in rows:
        if row["seed"] not in seeds:
            seeds.append(row["seed"])
    
    seeds.sort()
    
    return seeds


def finished_rows(rows):
    # - the buildings of every finished run, the only ones the graphs draw
    kept = []
    
    for row in rows:
        if row["place"] != "shop" and row["finished"]:
            kept.append(row)

    return kept


def grouped(axis, rows, measure, title, unit):
    # - one measure: a bar for each model in each condition, at the median over
    #   the seeds, the same summary the text and the tests report, with every
    #   seed as a dot on it
    width = 0.36

    for index, condition in enumerate(conditions):
        
        for offset, model in ((-width / 2, "gpt-oss"), (width / 2, "gemma")):
            values = []
            
            for row in rows:
                if row["condition"] == condition and row["label"] == model and row[measure] != "":
                    values.append(row[measure])
            
            if not values:
                continue
            
            centre = index + offset
            axis.bar(centre, median(values), width * 0.9, color=colours[model], alpha=0.55, label=names[model] if index == 0 else None)
            
            for position, value in enumerate(values):
                axis.scatter(centre + (position - (len(values) - 1) / 2) * 0.04, value, s=18, color=colours[model], edgecolor="#1b2420", linewidth=0.6, zorder=3)
    
    axis.set_xticks(range(len(conditions)))
    axis.set_xticklabels(["no memory", "memory"])
    
    axis.set_title(title)
    axis.set_ylabel(unit)
    
    axis.grid(axis="y", alpha=0.25)


def draw_survival(rows, folder):
    # - weeks the tenants survived, seed by seed, in each condition; a cross where they died
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    seeds = seeds_of(rows)
    width = 0.38
    
    for axis, condition in zip(axes, conditions):
        
        for offset, model in ((-width / 2, "gpt-oss"), (width / 2, "gemma")):
            
            for row in rows:
                
                if row["condition"] != condition or row["label"] != model:
                    continue
                
                centre = seeds.index(row["seed"]) + offset
                axis.bar(centre, row["survived_weeks"], width * 0.92, color=colours[model], label=names[model] if row["seed"] == seeds[0] else None)
                
                if not row["survived"]:
                    axis.scatter(centre, row["survived_weeks"] + 1.2, marker="x", color="#1b2420", s=28, zorder=3)
        
        axis.axhline(weeks_in_year, color="#1b2420", linewidth=0.8, linestyle=":")
        axis.set_xticks(range(len(seeds)))
        ticks = []
        
        for seed in seeds:
            ticks.append(f"seed {seed}")
        
        axis.set_xticklabels(ticks)
        axis.set_title("no memory" if condition == "no-memory" else "memory")
        axis.grid(axis="y", alpha=0.25)
    
    axes[0].set_ylabel("weeks the tenants survived (of 48)")
    axes[0].set_ylim(0, weeks_in_year + 4)
    
    handles, labels = axes[0].get_legend_handles_labels()
    
    figure.legend(handles, labels, frameon=False, loc="upper right", ncol=2)
    figure.suptitle("Survival: × marks where the tenants died")
    figure.tight_layout(rect=(0, 0, 1, 0.95))
    figure.savefig(folder / "survival.png", dpi=200)
    
    plt.close(figure)


def draw_wellbeing(rows, folder):
    # - days without, and the share of each need met, by model and condition
    figure, axes = plt.subplots(1, 4, figsize=(15, 4.2))
    
    grouped(axes[0], rows, "short_days", "Days without water or food", "days")
    grouped(axes[1], rows, "water_met", "Water need met", "%")
    grouped(axes[2], rows, "food_met", "Food need met", "%")
    grouped(axes[3], rows, "energy_met", "Energy need met", "%")
    
    axes[0].legend(frameon=False)
    
    figure.suptitle("Tenants' wellbeing while they lived: bars are the median over seeds, dots each seed")
    figure.tight_layout()
    figure.savefig(folder / "wellbeing.png", dpi=200)
    
    plt.close(figure)


def draw_waste(rows, folder):
    # - what the roofs grew, and what rotted or was lost
    figure, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    
    grouped(axes[0], rows, "harvested_kg", "Harvested", "kg")
    grouped(axes[1], rows, "wasted_kg", "Rotted or lost to drought", "kg")
    grouped(axes[2], rows, "rationed_days", "Days the tenants were rationed", "days")
    
    axes[0].legend(frameon=False)
    
    figure.suptitle("Growing and wasting: bars are the median over seeds, dots each seed")
    figure.tight_layout()
    figure.savefig(folder / "waste.png", dpi=200)
    
    plt.close(figure)


def draw_memory_effect(rows, folder):
    # - each seed's change from no memory to memory, one line per seed, for each model
    measures = [("survived_weeks", "weeks survived"), ("short_days", "days without water or food"), ("wasted_kg", "kg rotted or lost")]
    figure, axes = plt.subplots(1, len(measures), figsize=(13, 4.2))
    
    for axis, (measure, meaning) in zip(axes, measures):
        
        for offset, model in ((-0.06, "gpt-oss"), (0.06, "gemma")):
            before = {}
            after = {}
            
            for row in rows:
                if row["label"] != model or row[measure] == "":
                    continue
                
                if row["condition"] == "no-memory":
                    before[row["seed"]] = row[measure]
                else:
                    after[row["seed"]] = row[measure]
            
            first_line = True
            
            for seed in sorted(before):
                if seed not in after:
                    continue
                
                axis.plot([0 + offset, 1 + offset], [before[seed], after[seed]], color=colours[model], marker="o", markersize=4, linewidth=1.3, alpha=0.85, label=names[model] if first_line else None)
                axis.annotate(f"{seed}", (1 + offset, after[seed]), textcoords="offset points", xytext=(5, -3), fontsize=7, color=colours[model])
                first_line = False
        
        axis.set_xticks([0, 1])
        axis.set_xticklabels(["no memory", "memory"])
        axis.set_xlim(-0.35, 1.35)
        axis.set_title(meaning)
        axis.grid(axis="y", alpha=0.25)
    
    axes[0].legend(frameon=False)
    
    figure.suptitle("What memory changed, seed by seed (numbers are seeds)")
    figure.tight_layout()
    figure.savefig(folder / "memory_effect.png", dpi=200)
    
    plt.close(figure)


def draw_shop(rows, folder):
    # - what the shop gave each model's building, as water and as produce
    figure, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    
    grouped(axes[0], rows, "water_got", "Water from the shop", "litres")
    grouped(axes[1], rows, "produce_got_kg", "Produce from the shop", "kg")
    
    axes[0].legend(frameon=False)
    
    figure.suptitle("What each model's building got from the shop")
    figure.tight_layout()
    figure.savefig(folder / "shop.png", dpi=200)
    
    plt.close(figure)


def draw_year(seed, runs, folder):
    # - one seed's year, day by day: each building's rainwater tank and food
    #   storage, with and without memory, and a cross where its tenants died
    figure, axes = plt.subplots(2, 2, figsize=(13, 6.5), sharex=True)
    
    for column, condition in enumerate(conditions):
        
        if (seed, condition) not in runs:
            continue
        
        meta, weeks = runs[(seed, condition)]
        
        for place in ("1", "2"):
            
            model = label(meta["models"][place])
            days = []
            tank = []
            food = []
            died = None
            
            for week in weeks:
                
                for day in week["days"]:
                    state = day[place]
                    
                    if not state["alive"]:
                        if died is None:
                            died = week["week"] * Community.days + day["day"]
                        continue
                    
                    days.append(week["week"] * Community.days + day["day"])
                    tank.append(state["levels"]["tank"])
                    food.append(kg(state["food"]))
            
            axes[0][column].plot(days, tank, color=colours[model], linewidth=1.1, label=f"{names[model]} (building {place})")
            axes[1][column].plot(days, food, color=colours[model], linewidth=1.1)
            
            if died is not None:
                axes[0][column].scatter(died, 0, marker="x", color=colours[model], s=40, zorder=3)
                axes[1][column].scatter(died, 0, marker="x", color=colours[model], s=40, zorder=3)
        
        axes[0][column].set_title("no memory" if condition == "no-memory" else "memory")
        axes[0][column].axhline(Community.alarm_level * 100, color="#1b2420", linewidth=0.7, linestyle=":")
        axes[0][column].legend(frameon=False, fontsize=8)
    
    for column in range(2):
        
        for boundary in range(1, len(Community.seasons)):
            for row in range(2):
                axes[row][column].axvline(boundary * Community.season_weeks * Community.days, color="#1b2420", linewidth=0.5, alpha=0.3)
        
        axes[1][column].set_xlabel("day of the year (lines mark the seasons)")
        axes[0][column].grid(alpha=0.2)
        axes[1][column].grid(alpha=0.2)
    
    axes[0][0].set_ylabel("rainwater tank (%)")
    axes[1][0].set_ylabel("food storage (kg)")
    
    figure.suptitle(f"Seed {seed}, day by day: × marks where the tenants died, the dotted line the 40% alarm")
    figure.tight_layout()
    figure.savefig(folder / f"year_seed_{seed}.png", dpi=200)
    plt.close(figure)


if __name__ == "__main__":
    source = Path(__file__).parent / "data"
    folder = source / "evaluation"
    folder.mkdir(exist_ok=True)

    # - every run, measured
    rows = []
    runs = {}
    for path in sorted(source.glob("seed-*.jsonl")):
        meta, weeks = read_run(path)
        if meta is None or not weeks:
            continue
        runs[(meta["seed"], meta["condition"])] = (meta, weeks)
        rows.append(measure_building(meta, weeks, "1"))
        rows.append(measure_building(meta, weeks, "2"))
        rows.append(measure_shop(meta, weeks))

    going = []
    for (seed, condition), (meta, weeks) in sorted(runs.items()):
        if len(weeks) < weeks_in_year:
            going.append(f"seed {seed} {condition} ({len(weeks)} weeks)")

    with open(folder / "summary.csv", "w", newline="") as table:
        sheet = csv.DictWriter(table, fieldnames=columns)
        sheet.writeheader()
        sheet.writerows(rows)

    tests = compare(rows)
    with open(folder / "tests.csv", "w", newline="") as table:
        sheet = csv.DictWriter(table, fieldnames=list(tests[0].keys()))
        sheet.writeheader()
        sheet.writerows(tests)

    # - the graphs, from finished runs only
    finished = finished_rows(rows)
    draw_survival(finished, folder)
    draw_wellbeing(finished, folder)
    draw_waste(finished, folder)
    draw_memory_effect(finished, folder)
    draw_shop(finished, folder)
    
    
    for seed in seeds_of(finished):
        finished_runs = {}
        for condition in conditions:
            if (seed, condition) in runs and len(runs[(seed, condition)][1]) == weeks_in_year:
                finished_runs[(seed, condition)] = runs[(seed, condition)]
        draw_year(seed, finished_runs, folder)

    
    print(f"{len(runs)} runs measured, written to data/evaluation/")
    
    if going:
        print("still going, left out of the tests and graphs: " + ", ".join(going))
    
    print()
    print(f"{'comparison':<20} {'within':<10} {'measure':<28} {'pairs':>5} {'median first':>13} {'median second':>14} {'p':>6}")
    
    for test in tests:
        print(f"{test['comparison']:<20} {test['within']:<10} {test['measure']:<28} {test['pairs']:>5} "
              f"{str(test['median_first']):>13} {str(test['median_second']):>14} {str(test['p_value']):>6}  {test['note']}")
