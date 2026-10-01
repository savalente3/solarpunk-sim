"""One week's weather: an intensity for each weather type."""


class Weather:
    """Intensity runs 0.0 to 1.0, as a fraction of the most a building could
    ever collect in a week. Rain falls in most weeks, a little or a lot, as it
    does in Nottingham; a dry week is the exception, and a long dry spell rare.

    The season moves the odds rather than the mechanism: how bright the sun
    gets, how often a week stays dry, and how much rain falls on average.
    Averaged over the four seasons these come back to the yearly figures the
    rates were calibrated against.
    """

    # - the band the sun is drawn from, the odds of a week seeing rain, and the
    #   season's average rain -- the same averages as when rain came all at once
    #   in a few weeks, now spread over most of them
    seasons = {
        "spring": {"sun": (0.25, 0.85), "wet_weeks": 0.75, "rain": 0.14},
        "summer": {"sun": (0.55, 1.00), "wet_weeks": 0.75, "rain": 0.11},
        "autumn": {"sun": (0.05, 0.65), "wet_weeks": 0.86, "rain": 0.21},
        "winter": {"sun": (0.00, 0.60), "wet_weeks": 0.86, "rain": 0.20},
    }

    def __init__(self, rng, season):
        # - the sun is dimmer or brighter by season
        # - a wet week's rain is drawn up to twice what a wet week brings on
        #   average, so over the season it comes back to the season's average

        self.season = season
        odds = self.seasons[season]

        low, high = odds["sun"]
        wettest = 2 * odds["rain"] / odds["wet_weeks"]
        self.intensity = {
            "sun": round(rng.uniform(low, high), 2),
            "rain": round(rng.uniform(0.0, wettest), 2),
        }

        if rng.random() > odds["wet_weeks"]:
            self.intensity["rain"] = 0.0

    def __repr__(self):
        return f"Weather({self.season}, {self.intensity})"
