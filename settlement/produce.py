"""Produce: harvested crops held lot by lot, each lot knowing when it was picked.

The allotment, the food storage and the shop all hold produce the same way. Keeping
the day each lot was picked is what lets produce age -- and what lets whoever
holds it hand over what is nearest to going off first.
"""


class Produce:
    # - how long a picked crop keeps before it rots, the same for every crop
    shelf_days = 21

    def __init__(self, capacity=None):
        self.capacity = capacity    # kg, or None for no limit
        self.lots = []              # {"crop", "kg", "picked"}, oldest first

    def total(self):
        # - kg held, all crops
        total = 0
        for lot in self.lots:
            total += lot["kg"]
        return round(total, 2)

    def kinds(self):
        # - kg held of each crop
        kinds = {}
        for lot in self.lots:
            kinds[lot["crop"]] = round(kinds.get(lot["crop"], 0) + lot["kg"], 2)
        return kinds

    def free_storage(self):
        # - how many more kg can go in before the storage is full
        if self.capacity is None:
            return float("inf")
        return max(0, round(self.capacity - self.total(), 2))

    def take(self, lots):
        # - lots coming in keep the day they were picked
        # - takes what fits, and says what it took
        taken = []

        for lot in lots:
            kg = round(min(lot["kg"], self.free_storage()), 2)
            if kg <= 0:
                break

            self.lots.append({"crop": lot["crop"], "kg": kg, "picked": lot["picked"]})
            taken.append({"crop": lot["crop"], "kg": kg, "picked": lot["picked"]})

        self.lots.sort(key=lambda lot: lot["picked"])
        return taken

    def give(self, crop, kg):
        # - hands over up to kg of a crop, oldest first, so what is nearest to
        #   going off leaves first
        given = []

        for lot in list(self.lots):
            if kg <= 0:
                break
            if lot["crop"] != crop:
                continue

            part = round(min(kg, lot["kg"]), 2)
            given.append({"crop": crop, "kg": part, "picked": lot["picked"]})

            lot["kg"] = round(lot["kg"] - part, 2)
            kg = round(kg - part, 2)

            if lot["kg"] <= 0:
                self.lots.remove(lot)

        return given

    def eat(self, kg):
        # - eaten across the crops in proportion to what is held, oldest first
        #   within each crop -- says how much of each was eaten
        # - the last crop takes whatever rounding left, so exactly what was
        #   asked for is eaten, or everything if there is less
        held = self.total()
        wanted = round(min(kg, held), 2)
        kinds = self.kinds()
        eaten = {}
        so_far = 0

        for index, (crop, amount) in enumerate(kinds.items()):
            if index == len(kinds) - 1:
                share = round(wanted - so_far, 2)
            else:
                share = round(amount / held * wanted, 2)

            if share > 0:
                given = 0
                for lot in self.give(crop, share):
                    given += lot["kg"]
                eaten[crop] = round(given, 2)
                so_far = round(so_far + given, 2)

        return eaten

    def summary(self, today):
        # - kg held of each crop, and how many days old its oldest lot is
        summary = {}
        for lot in self.lots:
            crop = lot["crop"]
            if crop not in summary:
                age = today - lot["picked"]
                summary[crop] = {"kg": 0, "oldest_days": age, "rots_in": self.shelf_days - age}
            summary[crop]["kg"] = round(summary[crop]["kg"] + lot["kg"], 2)
        return summary

    def rot(self, today):
        # - lots past their shelf life are thrown away -- says what was lost
        rotted = []

        for lot in list(self.lots):
            if today - lot["picked"] >= self.shelf_days:
                rotted.append(lot)
                self.lots.remove(lot)

        return rotted


def move(giver, receiver, crop, kg):
    # - produce from one storage to another: no more than the giver holds or the
    #   receiver has free storage for, each lot keeping its age -- nothing made, nothing lost
    lots = giver.give(crop, min(kg, receiver.free_storage()))
    receiver.take(lots)

    moved = 0
    for lot in lots:
        moved += lot["kg"]
    return round(moved, 2)
