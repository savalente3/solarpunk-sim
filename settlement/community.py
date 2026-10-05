"""The community: the buildings and the shop, on one plane.

The buildings grow and consume, the shop moves produce between them. This is
what holds them together, and what runs the days and the weeks.
"""
from functools import partial

from settlement.produce import move
from settlement.weather import Weather


def add(total, amounts):
    # - adds a day's amounts into the week's, crop by crop where there are crops
    for key, value in amounts.items():
        if isinstance(value, dict):
            add(total.setdefault(key, {}), value)
        else:
            total[key] = round(total.get(key, 0) + value, 2)


def weight(lots):
    # - kg across a list of lots
    total = 0

    for lot in lots:
        total += lot["kg"]
    
    return total


class Community:
    # - how far tenant needs swing either way in a week
    variation = 0.25

    # - the year, in the order the weather knows its seasons
    seasons = tuple(Weather.seasons)
    season_weeks = 12

    # - the settlement runs in days
    # - the agents check in every few days, and sooner if a storage falls below the line
    days = 7
    wake_days = 3
    alarm_level = 0.4

    def __init__(self, buildings, shop):
        self.buildings = buildings
        self.shop = shop

        # - whoever is watching the run live, handed in; none means nobody is
        self.listener = None

        # - every finished week, and -- in the memory condition -- what writes them
        #   up as the community board the building managers are shown; handed in,
        #   and none means the managers remember nothing
        self.history = []
        self.remember = None

    def tell(self, kind, what):
        # - let whoever is watching know, the moment it happens
        if self.listener is not None:
            self.listener(kind, what)

    def happened(self, events, event):
        # - record what happened, and tell whoever is watching straight away
        events.append(event)
        self.tell("event", event)

    def run_week(self, week, season, rng):
        # - one sky over the whole settlement: the buildings and the shop stand side
        #   by side, so they share the week's weather
        # - the tenants' needs are drawn for every building, alive or not, so every
        #   condition sees the same draws on the same seed
        sky = Weather(rng, season)
        skies = {"shop": sky}
        rates = {}
        
        for building in self.buildings:
            skies[building.name] = sky
            rates[building.name] = 1 + rng.uniform(-self.variation, self.variation)
        
        self.tell("week", {"week": week, "season": season, "weather": sky.intensity})

        wanted = {}
        given = {}
        picked = {}
        lost = {}
        rotted = {"shop": []}
        
        for building in self.buildings:
            wanted[building.name] = {"residents": {}, "beds": {}}
            given[building.name] = {"residents": {}, "beds": {}}
            
            picked[building.name] = []
            lost[building.name] = []
            rotted[building.name] = []

        events = []
        states = []

        for day in range(self.days):
            self.tell("day begins", {"week": week, "day": day})

            for building in self.buildings:
                if not building.alive:
                    continue

                residents_want, residents_got, beds_want, beds_got, harvested, died, spoiled = self.run_day(
                    building, skies[building.name], rates[building.name], week * self.days + day
                )

                add(wanted[building.name]["residents"], residents_want)
                add(given[building.name]["residents"], residents_got)
                add(wanted[building.name]["beds"], beds_want)
                add(given[building.name]["beds"], beds_got)
                
                picked[building.name].extend(harvested)
                lost[building.name].extend(died)
                rotted[building.name].extend(spoiled)

                if spoiled:
                    kg = round(weight(spoiled), 2)
                    self.happened(events, {"day": day, "place": building.name, "event": "rotted", "lost": f"{kg} kg"})

                for bed in died:
                    self.happened(events, {"day": day, "place": building.name, "event": "bed died", "lost": f"{bed['kg']} kg {bed['crop']}"})

                cause = building.survive(residents_want, residents_got)
                if cause:
                    self.happened(events, {"day": day, "place": building.name, "event": "tenants died", "cause": cause})
                    continue

                for storage in self.fallen(building):
                    level = round(building.levels()[storage] * 100, 1)
                    self.happened(events, {"day": day, "place": building.name, "event": "alarm", "storage": storage, "level": level})

            # - the shop catches its own weather and runs itself on it
            # - it needs no water, so what it catches waits to be given
            self.shop.collect(skies["shop"], 1 / self.days)
            self.shop.spend(energy=self.shop.energy_use / self.days)

            spoiled = self.shop.stock.rot(week * self.days + day)
            rotted["shop"].extend(spoiled)
            
            if spoiled:
                kg = round(weight(spoiled), 2)
                self.happened(events, {"day": day, "place": "shop", "event": "rotted", "lost": f"{kg} kg"})

            for storage in self.fallen(self.shop):
                level = round(self.shop.levels()[storage] * 100, 1)
                self.happened(events, {"day": day, "place": "shop", "event": "alarm", "storage": storage, "level": level})

            today = week * self.days + day
            self.wake(today, day, season, skies, events)

            # - how everything stands at the end of the day, for following the
            #   lead-up to a decision afterwards
            state = {"day": day}
            
            for building in self.buildings:
                state[building.name] = building.snapshot(today)
            
            state["shop"] = self.shop.snapshot(today)
            states.append(state)
            
            self.tell("day ends", {"week": week, "day": day, "state": state})

        weather = {}
        
        for name, sky in skies.items():
            weather[name] = sky.intensity

        tanks = {}
        
        for building in self.buildings:
            tanks[building.name] = {
                "alive": building.alive,
                "energy": round(building.energy, 2),
                "water": round(building.water, 2),
                "greywater": round(building.greywater, 2),
                "food": building.food.kinds(),
                "produce": building.allotment.produce.kinds(),
            }

        record = {
            "week": week,
            "season": season,
            "weather": weather,
            "wanted": wanted,
            "given": given,
            "harvested": picked,
            "died": lost,
            "rotted": rotted,
            "buildings": tanks,
            "shop": {
                "energy": round(self.shop.energy, 2),
                "water": round(self.shop.water, 2),
                "stock": self.shop.stock.kinds(),
            },
            "events": events,
            "days": states,
        }

        self.history.append(record)
        return record

    def run_day(self, building, weather, rate, today):
        # - a seventh of the week: collect, the residents and the beds take
        #   theirs, the beds grow, anything ripe is picked, anything old rots
        fraction = 1 / self.days
        building.collect(weather, fraction)

        # - the tenants use what the manager allows of what they need
        residents_want = building.needs(rate, fraction)
        allowed = {}

        for resource, amount in residents_want.items():
            allowed[resource] = round(amount * building.allowance[resource], 2)

        residents_got = building.spend(**allowed)
        building.recover(residents_got["water"])

        # - the beds get what the manager gives them each day -- greywater first,
        #   and never more than they can use; with no decision yet they take what they need
        beds_want = building.allotment.needs(weather, fraction)
        
        if building.bed_supply is None:
            beds_ask = beds_want
        else:
            grey = min(building.bed_supply["greywater"], beds_want["water"])
            fresh = min(building.bed_supply["water"], beds_want["water"] - grey)
            energy = min(building.bed_supply["energy"], beds_want["energy"])
            beds_ask = {"water": round(fresh, 2), "greywater": round(grey, 2), "energy": round(energy, 2)}

        beds_got = building.spend(**beds_ask)
        building.need_today = {"tenants": residents_want, "beds": beds_want}

        # - fresh and grey are one pool once they reach the beds
        watered = beds_got["water"] + beds_got["greywater"]
        died = building.allotment.grow(weather, watered, beds_got["energy"], fraction)

        # - ripe beds are picked into the allotment's own storage
        harvested = []

        for index in building.allotment.ripe():
            harvested.append(building.allotment.harvest(index, today))

        spoiled = building.food.rot(today) + building.allotment.produce.rot(today)

        return residents_want, residents_got, beds_want, beds_got, harvested, died, spoiled

    def fallen(self, place):
        # - storages that have just dropped below the alarm line
        # - a storage already below does not ring again until it has come back up
        dropped = []

        for storage, level in place.levels().items():
            
            if level < self.alarm_level and storage not in place.low:
                place.low.add(storage)
                dropped.append(storage)
            elif level >= self.alarm_level:
                place.low.discard(storage)

        return dropped

    def wake(self, day_of_year, day, season, skies, events):
        # - who has something to decide today, and why -- no reason, no call
        # - an alarm wakes a place at once; otherwise it is checked every few days,
        #   or when it manager asked to be
        # - a building run by agnts is consulted there and then
        line = round(self.alarm_level * 100)

        places = []

        for building in self.buildings:
            
            if building.alive:
                places.append((building.name, building))
        places.append(("shop", self.shop))

        for name, place in places:
            scheduled = day_of_year >= place.next_check
            if scheduled:
                place.next_check = day_of_year + self.wake_days

            reasons = []
            trigger = "alarm"
            
            for event in events:
                if event["day"] == day and event["place"] == name and event["event"] == "alarm":
                    reasons.append(f"{event['storage']} dropped below {line}%")

            if scheduled and not reasons:
                trigger = "check"
                
                for storage in sorted(place.low):
                    reasons.append(f"{storage} still below {line}%")
                
                if name != "shop" and place.allotment.bare():
                    reasons.append("beds empty")
                
                if name != "shop" and place.check_asked:
                    reasons.append("the check you asked for")

            if scheduled and name != "shop":
                place.check_asked = False

            if reasons:
                # - what the agent is shown when it wakes: the moment, and the place as it stands
                weather = skies[name].intensity
                
                sees = {
                    "week": day_of_year // self.days,
                    "day": day,
                    "season": season,
                    "weather": weather,
                    "coming_in": {
                        "energy": round(weather["sun"] * place.panel_area * place.panel_yield / self.days, 1),
                        "water": round(weather["rain"] * place.roof_area * place.rain_yield / self.days),
                    },
                }
                sees.update(place.snapshot(day_of_year))

                # - a building also sees what the shop holds, so it knows what it could ask for
                if name != "shop":
                    sees["shop"] = {"water": round(self.shop.water, 2), "stock": self.shop.stock.summary(day_of_year)}

                self.happened(events, {"day": day, "place": name, "event": "wake", "trigger": trigger, "why": reasons, "sees": sees})

                if name != "shop" and place.managers is not None:
                    self.consult(place, sees, reasons, day_of_year, day, events)

    def exchanged(self, events, day, place, exchange):
        # - one answer from an agent, recorded and told to whoever is watching
        record = {"day": day, "place": place, "event": "exchange"}
        record.update(exchange)
        self.happened(events, record)

    def consult(self, building, sees, why, day_of_year, day, events):
        # - the allotment manager says what the beds need, the building manager
        #   decides, and the building carries it out
        # - an answer that cannot be read changes nothing: the last decision stays
        # - each answer is recorded, and told to whoever is watching, as soon as it is given
        said = partial(self.exchanged, events, day, building.name)

        # - in the memory condition the building manager is also shown the community board
        board = None
        
        if self.remember is not None:
            board = self.remember(self.history, events)

        decision = building.managers.decide(sees, why, said, board)

        if decision is None:
            refused = ["your last answer could not be read, so your previous decision stayed in force"]
        else:
            refused = building.apply(decision, day_of_year)
            refused.extend(self.trade(building, decision["shop"], sees, day_of_year, day, events))

        self.happened(events, {"day": day, "place": building.name, "event": "decision", "refused": refused})
        building.managers.refused = refused

    def trade(self, building, request, sees, today, day, events):
        # - the building sends the shop its surplus, and the shop answers what it
        #   was asked -- the shop is only called if the building wants something
        # - says what could not be done, for the building manager next time
        refused = []

        sent = []
        
        for item in request["send_surplus"]:
            if item["kg"] == 0:
                continue
            
            kg = move(building.allotment.produce, self.shop.stock, item["crop"], item["kg"])
            
            if kg > 0:
                sent.append({"crop": item["crop"], "kg": kg})
            
            if kg < item["kg"]:
                refused.append(
                    f"send {item['kg']} kg {item['crop']} to the shop: only {kg} kg sent "
                    f"(not that much in the allotment's store, or the shop is full)"
                )

        wants = request["water_wanted"] > 0 or bool(request["message"].strip())
        
        for item in request["produce_wanted"]:
            if item["kg"] > 0:
                wants = True

        if not (sent or wants):
            return refused

        water = 0
        given = []

        if self.shop.manager is not None:
            # - the shop is shown the moment, itself, and how both buildings stand
            shop_sees = {"week": sees["week"], "day": sees["day"], "season": sees["season"]}
            shop_sees.update(self.shop.snapshot(today))
            shop_sees["buildings"] = {}
            
            for other in self.buildings:
                shop_sees["buildings"][other.name] = other.snapshot(today)

            reply, exchange = self.shop.manager.answer(shop_sees, building.name, request, sent)
            self.exchanged(events, day, building.name, exchange)
            building.managers.shop_reply = reply

            if reply is None:
                refused.append("the shop's answer could not be read, so it gave nothing")
            else:
                if reply["water_given"] > 0:
                    taken = building.receive(water=min(reply["water_given"], self.shop.water))
                    self.shop.spend(water=taken["water"])
                    water = round(taken["water"], 2)

                for item in reply["produce_given"]:
                    
                    if item["kg"] == 0:
                        continue
                    
                    kg = move(self.shop.stock, building.food, item["crop"], item["kg"])
                    
                    if kg > 0:
                        given.append({"crop": item["crop"], "kg": kg})

        self.happened(events, {"day": day, "place": building.name, "event": "trade", "sent": sent, "water": water, "produce": given})
        return refused

    def run_season(self, name, first_week, rng):
        # - twelve weeks under the same season, handed back one at a time
        for week in range(first_week, first_week + self.season_weeks):
            yield self.run_week(week, name, rng)

    def run_year(self, rng):
        # - four seasons, and the beds and the stock carry across them
        for index, name in enumerate(self.seasons):
            yield from self.run_season(name, index * self.season_weeks, rng)

    def __repr__(self):
        names = []
        
        for building in self.buildings:
            names.append(building.name)
        
        return f"Community(buildings=[{', '.join(names)}], shop={self.shop!r})"
