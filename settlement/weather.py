"""One day's weather: an intensity for each weather type."""


class Weather:
    """Intensity runs 0.0 to 1.0, as a fraction of the most a building could
    ever collect in a day. Rain only falls on about one day in three, which
    is what makes dry spells -- and dry spells are what make water scarce.
    """

    types = ("sun", "rain")
    wet_days = 0.33         # rain falls 1 day in 3

    def __init__(self, rng):
        self.intensity = {}
        for name in self.types:
            self.intensity[name] = round(rng.uniform(0.0, 1.0), 2)

        if rng.random() > self.wet_days:
            self.intensity["rain"] = 0.0

    def __repr__(self):
        return f"Weather({self.intensity})"
