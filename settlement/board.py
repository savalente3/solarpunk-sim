"""The board: the settlement written out in words.

The same words go into the printout, the text file and the agents' prompts, so
what an agent is shown is exactly what a person reading the run would see.
"""
from settlement.community import Community


def pairs(values):
    parts = []
    for key, value in values.items():
        parts.append(f"{key} {value}")
    return ", ".join(parts)


def percent(share):
    return f"{round(share * 100)}%"


def held(summary):
    # - produce by crop, with the age of its oldest lot and how long before it rots
    if not summary:
        return "nothing held"
    parts = []
    for crop, lot in summary.items():
        parts.append(f"{crop} {lot['kg']} kg ({lot['oldest_days']} days old → rots in {lot['rots_in']} days)")
    return ", ".join(parts)


def per_day(beds):
    # - what the beds need or get each day
    return f"{beds['water_per_day']} L water, {beds['greywater_per_day']} L greywater, {beds['energy_per_day']} kWh"


def plantings(plant):
    parts = []
    for planting in plant:
        parts.append(f"{planting['crop']} in {planting['beds']} beds")
    return ", ".join(parts)


def seen(sees):
    # - a place as it stands, as its agent is shown it
    levels = []
    for storage, level in sees["levels"].items():
        levels.append(f"{storage} {level}%")
    lines = ["storage   " + " | ".join(levels)]

    amounts = [f"energy {sees['energy']} kWh", f"water {sees['water']} L"]
    if "greywater" in sees:
        amounts.append(f"greywater {sees['greywater']} L")
    lines.append("amounts   " + " | ".join(amounts))

    coming = sees["coming_in"]
    rain = f"{coming['water']} L of rain" if coming["water"] else "no rain"
    lines.append(f"coming in about {coming['energy']} kWh of sun and {rain} a day this week")

    if "stock" in sees:
        lines.append("stock     " + held(sees["stock"]))
        return lines

    tenants = sees["need_per_day"]["tenants"]
    beds = sees["need_per_day"]["beds"]
    lines.append(
        f"needs     tenants {tenants['energy']} kWh, {tenants['water']} L water, {tenants['food']} kg food a day"
        f" | beds {beds['water']} L water, {beds['energy']} kWh a day"
    )

    rules = sees["rules"]
    allowed = rules["tenants"]
    if rules["beds"] is None:
        supply = "take what they need"
    else:
        supply = f"get {rules['beds']['water']} L water, {rules['beds']['greywater']} L greywater, {rules['beds']['energy']} kWh a day"
    lines.append(
        f"rules     tenants may use {percent(allowed['energy'])} energy, {percent(allowed['water'])} water,"
        f" {percent(allowed['food'])} food | beds {supply}"
    )

    lines.append("food      " + held(sees["food"]))

    beds = sees["beds"]
    growing = []
    for crop, count in beds["growing"].items():
        growing.append(f"{crop} {count}")
    line = f"beds      {sum(beds['growing'].values())} growing"
    if growing:
        line += ": " + ", ".join(growing)
    line += f" | {beds['empty']} empty"
    if beds["furthest"] is not None:
        line += f" | furthest along {beds['furthest']}%"
    if beds["driest_dies_in"] is not None:
        line += f" | driest {beds['driest']} dry days → dies in {beds['driest_dies_in']} days"
    lines.append(line)

    lines.append("allotment " + held(sees["allotment_produce"]))

    short = []
    for need in ("water", "food"):
        if f"{need}_dies_in" in sees["tenants"]:
            days = sees["tenants"][f"days_without_{need}"]
            short.append(f"{days} days with almost no {need} → die in {sees['tenants'][need + '_dies_in']} days")
    lines.append("tenants   " + ("; ".join(short) or "fine"))
    return lines


def asked(answer):
    # - what the allotment manager said, in a few lines
    lines = ["beds need a day: " + per_day(answer["beds_need"])]
    if answer["plant"]:
        lines.append("plant: " + plantings(answer["plant"]))
    lines.append(f'says: "{answer["message"]}"')
    return lines


def decided(decision):
    # - what the building manager decided, in a few lines
    tenants = decision["until_next_time"]["tenants"]
    lines = [
        f"tenants may use {percent(tenants['energy'])} energy, {percent(tenants['water'])} water, {percent(tenants['food'])} food",
        "beds get a day: " + per_day(decision["until_next_time"]["beds"]),
    ]

    now = []
    for request in decision["now"]["move_to_food_storage"]:
        now.append(f"move {request['kg']} kg {request['crop']} into food storage")
    if decision["now"]["plant"]:
        now.append("plant " + plantings(decision["now"]["plant"]))
    if now:
        lines.append("now: " + "; ".join(now))

    lines.append(f"check again in {decision['check_again_in_days']} days")
    lines.append(f'why: "{decision["reasoning"]}"')
    return lines


def happened(event):
    # - what kind of thing happened, and to what: a label, then a line or a few
    kind = event["event"]

    if kind == "alarm":
        line = round(Community.alarm_level * 100)
        return [f"ALARM     {event['storage']} dropped below {line}% (now {event['level']}%)"]

    if kind == "wake":
        who = "shop agent" if event["place"] == "shop" else "managers"
        how = "by the alarm" if event["trigger"] == "alarm" else "on a check"
        return [f"WAKE      {who} woken {how}: " + ", ".join(event["why"])]

    if kind == "exchange":
        if event["answer"] is None:
            return [f"UNREADABLE the {event['agent']}'s answer could not be read: {event['unreadable']}"]
        if event["agent"] == "allotment manager":
            label, said = "ALLOTMENT", asked(event["answer"])
        else:
            label, said = "MANAGER", decided(event["answer"])
        lines = [label.ljust(10) + said[0]]
        for line in said[1:]:
            lines.append(" " * 10 + line)
        return lines

    if kind == "decision":
        lines = []
        for refusal in event["refused"]:
            lines.append("REFUSED   " + refusal)
        return lines

    if kind == "tenants died":
        return [f"DEATH     tenants died: {event['cause']}"]

    if kind == "bed died":
        return [f"LOST      bed died of drought: {event['lost']}"]

    if kind == "rotted":
        return [f"ROTTED    {event['lost']} went off"]

    return [kind]


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


def describe(record):
    # - a week: what happened day by day, place by place, then where everything stands
    lines = [f"Week {record['week']} ({record['season']})"]

    days = {}
    for event in record["events"]:
        place = "shop" if event["place"] == "shop" else f"building {event['place']}"
        days.setdefault(event["day"], {}).setdefault(place, []).append(event)

    for day, places in days.items():
        lines.append(f"  day {day}")
        for place, happenings in places.items():
            lines.append(f"    {place}")
            for event in happenings:
                for line in happened(event):
                    lines.append(f"      {line}")
                if "sees" in event:
                    shown = seen(event["sees"])
                    lines.append(" " * 16 + "sees  " + shown[0])
                    for line in shown[1:]:
                        lines.append(" " * 22 + line)

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
