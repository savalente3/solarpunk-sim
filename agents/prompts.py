"""What the agents are told: who they are, what the tenants and the beds need,
what they can decide, and -- each time they wake -- how things stand.

The same words for every model, so the model is the only thing that differs.
The numbers come from the settlement's own constants, so what the agents are
told cannot drift from what the simulation does.
"""
from settlement.allotment import Allotment
from settlement.community_board import asked, decided, replied, seen, shop_view
from settlement.building import Building
from settlement.community import Community
from settlement.produce import Produce

goal = (
    "You are an AI manager in a solarpunk settlement of two apartment buildings and a shop. "
    "Your goal is the wellbeing of the whole community: keep the tenants alive, and waste as little as possible."
)

tenants_need = f"""What the tenants need, and what happens without it:
- Water, every day → rationed, they cope → almost none for {Building.thirst_limit} days → they die
- Food, every day → rationed, they cope → almost none for {Building.hunger_limit // 7} weeks → they die
- Energy, every day → short, they cope → nobody dies"""

# - how long each crop takes to ripen, fastest first
ripening = []
for crop, weeks in Allotment.growth_weeks.items():
    ripening.append(f"{crop} {weeks} weeks")

beds_need = f"""What the beds on the roof need, and what happens without it:
- Water and power, every day → short, crops grow slower → under half for {Allotment.wilt_days} days → the bed dies and its crop is lost
- Rain waters the beds too: the wetter the week, the less water they need from the building
- A bed gives {Allotment.bed_area * Allotment.crop_yield} kg when ripe; ripe beds are picked into the allotment's store
- With all it needs, a bed ripens after: {", ".join(ripening)}
- Harvested produce keeps {Produce.shelf_days // 7} weeks, then rots; the oldest is always used first
- A roof grows at most {Allotment.crop_limit} kinds at once"""

the_shop = """The shop holds the settlement's reserve, shared by both buildings: spare rainwater, which it does not need itself, and a stock of produce.
- You can send it surplus from the allotment's store, so it does not rot on the roof; the fair return is the same amount of different produce
- You can ask it for water, or for produce you lack
- It answers straight away, but it looks after both buildings, so it may give less than you ask"""

produce_kept = """Where produce is kept:
- Harvests land in the allotment's store
- The tenants only eat from food storage
- Produce can only be moved from the allotment's store into food storage; food already in food storage is already where it needs to be"""


def building_manager(name):
    # - the building manager's standing instructions
    return f"""{goal}

You are the building manager of building {name}. You run its battery, its rainwater tank, its greywater tank and its food storage, and you have the final say over them. Greywater comes back from the tenants' washing and can only go to the beds.

{tenants_need}

{beds_need}

{produce_kept}

{the_shop}

Each time you are woken you decide:
- now: produce to move from the allotment's store into food storage, and what to plant in empty beds
- until you next decide: the share of their normal need the tenants may use, for energy, water and food -- 1 means all they need, 0 means none at all, even when it is sitting in storage -- and what the beds get each day (water, greywater and energy)
- what to ask of the shop: surplus to send it, water or produce you want, and a note to it
- when to check again: in 1, 2 or 3 days; an alarm wakes you sooner if any storage drops below {round(Community.alarm_level * 100)}%
- if there is nothing to move, plant, send or ask for, leave that part empty

The allotment manager tells you first what the beds need. Decide for the good of the whole building."""


def allotment_manager(name):
    # - the allotment manager's standing instructions
    return f"""{goal}

You are the allotment manager of building {name}. You run the beds on its roof. The building manager decides how the building's water, greywater and energy are shared; you tell them what the beds need and what to plant.

{beds_need}

{produce_kept}

Each time you are woken you say:
- what the beds need each day until the next decision: water, greywater and energy
- what to plant in empty beds, as a crop and a number of beds; leave it empty if there is nothing to plant
- a short message to the building manager"""


def shop_manager():
    # - the shop's standing instructions
    # - how much of one harvest a building can eat before it rots
    usable = Building.tenant_needs["food"] * Produce.shelf_days // 7
    return f"""{goal}

You run the shop. It holds the settlement's reserve, shared by both buildings: the rainwater its roof collects, which it does not need itself, and a stock of produce. A building manager calls on you when it wants something: it may send you surplus from its harvest, and ask you for water or for produce it lacks. You look after both buildings -- what you give one, the other cannot have.

{tenants_need}

Your job is variety, not volume:
- When a building sends you surplus, the fair return is the same amount of different produce, so no building eats only what its own roof grows; in a crisis you may give more
- Buildings call on you one at a time; being first earns nothing, so always keep some of every crop, and some water, for the other building
- Each building's tenants eat about {Building.tenant_needs["food"]} kg of produce a week, and produce keeps {Produce.shelf_days // 7} weeks, so a building can use about {usable} kg of a harvest; the rest rots
- Tell each building what to grow next, as crop and kg, so the two roofs grow different kinds and no more than the settlement can eat

About produce:
- The oldest produce is always given first
- A bed on a roof gives {Allotment.bed_area * Allotment.crop_yield} kg when ripe; with all it needs, it ripens after: {", ".join(ripening)}
- A building can only take as much as it has room for

Each time a building calls on you, you decide:
- how much water to give it now, in litres
- what produce to give it now, as crop and kg; leave it empty to give none
- what that building should grow next, as crop and kg; leave it empty for no suggestion
- a short message to that building's managers"""


def wake_message(sees, why):
    # - what an agent is shown when it wakes: the moment, why, and the building as it stands
    week_of_season = sees["week"] % Community.season_weeks + 1
    
    lines = [
        f"It is {sees['season']}, week {week_of_season} of {Community.season_weeks}, day {sees['day'] + 1} of 7.",
        "You were woken because: " + "; ".join(why) + ".",
        "",
    ]

    for line in seen(sees):
        lines.append(line)

    return "\n".join(lines)


def allotment_message(message, shop_reply):
    # - the allotment manager also hears what the shop would like grown
    if shop_reply is None:
        return message
    
    wanted = []
    for item in shop_reply["suggest_planting"]:
        if item["kg"]:
            wanted.append(f"{item['kg']} kg {item['crop']}")
    
    if not wanted:
        return message
    
    return message + "\n\nThe shop would like this building to grow: " + ", ".join(wanted) + "."


def manager_message(message, answer, previous, refused, shop_reply, board=None):
    # - the building manager also hears the allotment manager, and is reminded of
    #   what it decided last time, what could not be carried out, and what the
    #   shop said last time
    # - in the memory condition it also reads the community board
    lines = [message, "", "The allotment manager says:"]
    
    if answer is None:
        lines.append("  (its answer could not be read)")
    else:
        for line in asked(answer):
            lines.append("  " + line)

    lines.append("")
    if previous is None:
        lines.append("You have not decided anything yet: the tenants use all they need and the beds take what they need.")
    else:
        lines.append("Your last decision, still in force until you change it:")
        
        for line in decided(previous):
            lines.append("  " + line)

    if refused:
        lines.append("")
        lines.append("Not carried out last time:")
        
        for refusal in refused:
            lines.append("  - " + refusal)

    if shop_reply is not None:
        lines.append("")
        lines.append("The shop's answer last time:")
        
        for line in replied(shop_reply):
            lines.append("  " + line)

    if board:
        lines.append("")
        
        for line in board:
            lines.append(line)

    return "\n".join(lines)


def shop_message(sees, name, request, sent):
    # - what the shop is shown when a building calls on it: the moment, what
    #   the building sent and asks for, and how the shop and both buildings stand
    week_of_season = sees["week"] % Community.season_weeks + 1
    lines = [f"It is {sees['season']}, week {week_of_season} of {Community.season_weeks}, day {sees['day'] + 1} of 7.", ""]

    lines.append(f"Building {name} calls on you:")
    said = []
    
    if sent:
        arrived = []
        
        for item in sent:
            arrived.append(f"{item['kg']} kg {item['crop']}")
        
        said.append("it has sent you " + ", ".join(arrived) + " (now in your stock)")
    
    if request["water_wanted"]:
        said.append(f"it asks for {request['water_wanted']} L water")
    
    wanted = []
    
    for item in request["produce_wanted"]:
        if item["kg"]:
            wanted.append(f"{item['kg']} kg {item['crop']}")
    
    if wanted:
        said.append("it asks for " + ", ".join(wanted))
    
    if request["message"].strip():
        said.append(f'it says: "{request["message"]}"')
    
    for line in said or ["it asks for nothing"]:
        lines.append("  " + line)

    lines.append("")
    
    for line in shop_view(sees):
        lines.append(line)
    
    return "\n".join(lines)
