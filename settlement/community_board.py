"""The community board: the settlement written out in words.

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


def listed(items):
    # - produce as kg and crop, one after another
    parts = []
    
    for item in items:
        parts.append(f"{item['kg']} kg {item['crop']}")
    
    return ", ".join(parts)


def total(lots):
    # - kg across a list of lots, harvests or beds
    kg = 0
    
    for lot in lots:
        kg += lot["kg"]
    
    return kg


def per_day(beds):
    # - what the beds need or get each day
    return f"{beds['water_per_day']} L water, {beds['greywater_per_day']} L greywater, {beds['energy_per_day']} kWh"


def plantings(plant):
    parts = []
    
    for planting in plant:
        parts.append(f"{planting['crop']} in {planting['beds']} beds")
    return ", ".join(parts)


def shortage(tenants):
    # - how long the tenants have gone short, and how long they have left
    short = []
    
    for need in ("water", "food"):
        
        if f"{need}_dies_in" in tenants:
            days = tenants[f"days_without_{need}"]
            short.append(f"{days} days with almost no {need} → die in {tenants[need + '_dies_in']} days")
    
    return "; ".join(short) or "fine"


def seen(sees):
    # - a place as it stands, as its agent is shown it
    levels = []
    
    for storage, level in sees["levels"].items():
        levels.append(f"{storage} {level}%")
    
    lines = ["storage           " + " | ".join(levels)]

    amounts = [f"energy {sees['energy']} kWh", f"water {sees['water']} L"]
    
    if "greywater" in sees:
        amounts.append(f"greywater {sees['greywater']} L")
    
    lines.append("amounts           " + " | ".join(amounts))

    coming = sees["coming_in"]
    rain = f"{coming['water']} L of rain" if coming["water"] else "no rain"
    lines.append(f"coming in         about {coming['energy']} kWh of sun and {rain} a day this week")

    if "stock" in sees:
        lines.append("stock             " + held(sees["stock"]))
        return lines

    tenants = sees["need_per_day"]["tenants"]
    beds = sees["need_per_day"]["beds"]
    
    lines.append(
        f"needs             tenants {tenants['energy']} kWh, {tenants['water']} L water, {tenants['food']} kg food a day"
        f" | beds {beds['water']} L water, {beds['energy']} kWh a day"
    )

    rules = sees["rules"]
    allowed = rules["tenants"]
    
    if rules["beds"] is None:
        supply = "take what they need"
    else:
        supply = f"get {rules['beds']['water']} L water, {rules['beds']['greywater']} L greywater, {rules['beds']['energy']} kWh a day"
    
    lines.append(
        f"rules             tenants may use {percent(allowed['energy'])} energy, {percent(allowed['water'])} water,"
        f" {percent(allowed['food'])} food | beds {supply}"
    )

    lines.append("in food storage   " + held(sees["food"]))

    beds = sees["beds"]
    growing = []
    
    for crop, count in beds["growing"].items():
        growing.append(f"{crop} {count}")
    
    line = f"beds              {sum(beds['growing'].values())} growing"
    
    if growing:
        line += ": " + ", ".join(growing)
    
    line += f" | {beds['empty']} empty"
    
    if beds["furthest"] is not None:
        line += f" | furthest along {beds['furthest']}%"
    
    if beds["driest_dies_in"] is not None:
        line += f" | driest {beds['driest']} dry days → dies in {beds['driest_dies_in']} days"
    
    lines.append(line)

    lines.append("allotment holds   " + (held(sees["allotment_produce"]) if sees["allotment_produce"] else "nothing yet (harvests land here)"))
    lines.append("tenants           " + shortage(sees["tenants"]))

    if "shop" in sees:
        lines.append(f"shop has          water {sees['shop']['water']} L | " + held(sees["shop"]["stock"]))
    
    return lines


def shop_view(sees):
    # - the shop as it stands, and how each building is doing, as the shop is shown it
    lines = [
        f"shop tank         {sees['levels']['tank']}% ({sees['water']} L)",
        "shop stock        " + held(sees["stock"]),
    ]

    for name, building in sees["buildings"].items():
        
        if not building["alive"]:
            lines.append(f"building {name}        empty, tenants gone")
            continue
        
        food = 0
        
        for lot in building["food"].values():
            food += lot["kg"]
        
        growing = ", ".join(building["beds"]["growing"]) or "nothing"
        lines.append(
            f"building {name}        tenants {shortage(building['tenants'])} | tank {building['levels']['tank']}%"
            f" ({building['water']} L) | food storage {round(food, 2)} kg | grows {growing}"
        )
    
    return lines


def requested(request):
    # - what a building manager sent the shop and asked of it; nothing if it asked nothing
    parts = []

    sending = []
    
    for item in request["send_surplus"]:
        if item["kg"]:
            sending.append(f"{item['kg']} kg {item['crop']}")
    
    if sending:
        parts.append("send " + ", ".join(sending))

    if request["water_wanted"]:
        parts.append(f"ask for {request['water_wanted']} L water")

    wanting = []

    for item in request["produce_wanted"]:
        if item["kg"]:
            wanting.append(f"{item['kg']} kg {item['crop']}")
    
    if wanting:
        parts.append("ask for " + ", ".join(wanting))

    lines = []
    
    if parts:
        lines.append("to the shop: " + "; ".join(parts))
    
    if request["message"].strip():
        lines.append(f'to the shop, says: "{request["message"]}"')
    
    return lines


def replied(reply):
    # - what the shop gave, and what it said
    given = []

    if reply["water_given"]:
        given.append(f"{reply['water_given']} L water")
    
    for item in reply["produce_given"]:

        if item["kg"]:
            given.append(f"{item['kg']} kg {item['crop']}")

    lines = ["gives: " + (", ".join(given) or "nothing")]
    growing = []
    
    for item in reply["suggest_planting"]:
        if item["kg"]:
            growing.append(f"{item['kg']} kg {item['crop']}")
    
    if growing:
        lines.append("suggests growing: " + ", ".join(growing))
    
    lines.append(f'says: "{reply["message"]}"')
    lines.append(f'why: "{reply["reasoning"]}"')
    
    return lines


def asked(answer):
    # - what the allotment manager said, in a few lines
    lines = ["beds need a day: " + per_day(answer["beds_need"])]
    
    if answer["plant"]:
        lines.append("plant: " + plantings(answer["plant"]))
    
    lines.append(f'says: "{answer["message"]}"')
    
    return lines


def decided(decision):
    # - what the buildig manager decided, in a few lines
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

    if "shop" in decision:
        lines.extend(requested(decision["shop"]))

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
        elif event["agent"] == "shop":
            label, said = "SHOP", replied(event["answer"])
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

    if kind == "trade":
        parts = []

        if event["sent"]:
            parts.append("sent the shop " + listed(event["sent"]))
        
        if event["water"]:
            parts.append(f"received {event['water']} L water")
        
        if event["produce"]:
            parts.append("received " + listed(event["produce"]))
        
        return ["TRADE     " + ("; ".join(parts) or "nothing changed hands")]

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


def noted(event):
    # - one thing that happened, in a line, as the community board records it:
    #   what was decided, given and traded, and what went wrong -- not what the
    #   agents said to each other, nor wakes, advice, or trades where nothing moved
    place = "the shop" if event["place"] == "shop" else f"building {event['place']}"
    kind = event["event"]

    if kind == "alarm":
        return f"{place}: {event['storage']} dropped below {round(Community.alarm_level * 100)}% ({event['level']}%)"

    if kind == "exchange":
        if event["agent"] == "allotment manager":
            return None
        
        if event["answer"] is None:
            return f"{place}: the {event['agent']}'s answer could not be read"
        
        if event["agent"] == "shop":
            who, said = f"the shop, to {place}", replied(event["answer"])
        else:
            who, said = f"{place}'s building manager", decided(event["answer"])
        
        kept = []
        
        for line in said:
            if not line.startswith(("why:", "check again", "says:", "to the shop, says:")):
                kept.append(line)
        
        return f"{who}: " + "; ".join(kept)

    if kind == "trade":
        parts = []
        
        if event["sent"]:
            parts.append("sent the shop " + listed(event["sent"]))
        
        if event["water"]:
            parts.append(f"received {event['water']} L water")
        
        if event["produce"]:
            parts.append("received " + listed(event["produce"]))
        
        if not parts:
            return None
        
        return f"{place} and the shop: " + "; ".join(parts)

    if kind == "decision":
        if not event["refused"]:
            return None
        
        return f"{place} could not: " + "; ".join(event["refused"])

    if kind == "rotted":
        return f"{place}: {event['lost']} of produce rotted"

    if kind == "bed died":
        return f"{place}: a bed died of drought, {event['lost']} lost"

    if kind == "tenants died":
        return f"{place}: the tenants died ({event['cause']})"

    return None


def summed(record):
    # - one week in a line: the weather, and how each place came through it
    weather = record["weather"]["shop"]
    rain = f"rain {percent(weather['rain'])}" if weather["rain"] > 0 else "dry"
    parts = [f"week {record['week'] + 1} ({record['season']}), sun {percent(weather['sun'])}, {rain}"]

    for name, building in record["buildings"].items():
        said = []
        died = False
        
        for event in record["events"]:
            if event["event"] == "tenants died" and event["place"] == name:
                said.append(f"the tenants died ({event['cause']})")
                died = True
        
        if not building["alive"] and not died:
            parts.append(f"building {name}: empty")
            continue

        harvested = round(total(record["harvested"][name]), 1)
        rotted = round(total(record["rotted"][name]), 1)
        lost = round(total(record["died"][name]), 1)
        
        if harvested:
            said.append(f"harvested {harvested} kg")
        
        if rotted:
            said.append(f"{rotted} kg rotted")
        
        if lost:
            said.append(f"{lost} kg lost to drought")

        thirsty = 0
        hungry = 0
        
        for day in record["days"]:
            tenants = day[name]["tenants"]
            
            if day[name]["alive"] and tenants["days_without_water"] > 0:
                thirsty += 1
            
            if day[name]["alive"] and tenants["days_without_food"] > 0:
                hungry += 1
        
        if thirsty:
            said.append(f"tenants without water {thirsty} days")
        
        if hungry:
            said.append(f"tenants without food {hungry} days")

        sent = 0
        water = 0
        produce = 0
        
        for event in record["events"]:
            
            if event["event"] == "trade" and event["place"] == name:
                sent += total(event["sent"])
                water += event["water"]
                produce += total(event["produce"])
        
        if sent:
            said.append(f"sent the shop {round(sent, 1)} kg")
        
        if water or produce:
            said.append(f"got {round(water)} L water and {round(produce, 1)} kg produce from the shop")

        parts.append(f"building {name}: " + (", ".join(said) or "a quiet week"))

    stock = round(sum(record["shop"]["stock"].values()), 1)
    shop_rotted = round(total(record["rotted"]["shop"]), 1)
    shop = f"the shop: {round(record['shop']['water'])} L water, {stock} kg in stock"
    
    if shop_rotted:
        shop += f", {shop_rotted} kg rotted"
    
    parts.append(shop)
    return " · ".join(parts)


def remembered(history, events):
    # - the community board, as a building manager is shown it in the memory
    #   condition: everything that has happened in the whole settlement so far --
    #   the last two weeks day by day, and one line for each week before them
    lines = ["The community board -- what has happened in the whole settlement so far:"]

    earlier = history[:-2]
    recent = history[-2:]
    
    if earlier:
        lines.append("Earlier weeks, one line each:")
        
        for record in earlier:
            lines.append("  " + summed(record))

    for record in recent:
        lines.append(f"Week {record['week'] + 1} ({record['season']}), day by day:")
        
        for event in record["events"]:
            text = noted(event)
            
            if text:
                lines.append(f"  day {event['day'] + 1} · {text}")
        
        lines.append("  in all: " + summed(record))

    lines.append("This week so far:")
    written = 0
    
    for event in events:
        text = noted(event)
        
        if text:
            lines.append(f"  day {event['day'] + 1} · {text}")
            written += 1
    
    if not written:
        lines.append("  nothing yet")
    
    return lines
