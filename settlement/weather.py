"""One week's weather: an intensity for each weather type."""


class Weather:
    """Intensity runs 0.0 to 1.0, as a fraction of the most a building could
    ever collect in a week. Rain only falls in about one week in three, which
    is what makes dry spells -- and dry spells are what make water scarce.

    The season moves the odds rather than the mechanism: how bright the sun
    gets, and how often the rain comes. Averaged over the four seasons these
    come back to the yearly figures the rates were calibrated against.
    """

    # - the band the sun is drawn from, and the odds of a week seeing rain
    seasons = {
        "spring": {"sun": (0.25, 0.85), "wet_weeks": 0.28},
        "summer": {"sun": (0.55, 1.00), "wet_weeks": 0.22},
        "autumn": {"sun": (0.05, 0.65), "wet_weeks": 0.42},
        "winter": {"sun": (0.00, 0.60), "wet_weeks": 0.40},
    }

    def __init__(self, rng, season):
        # - the sun is dimmer or brighter by season
        # - the rain falls as hard whenever it comes, just less often

        self.season = season
        odds = self.seasons[season]

        low, high = odds["sun"]
        self.intensity = {
            "sun": round(rng.uniform(low, high), 2),
            "rain": round(rng.uniform(0.0, 1.0), 2),
        }

        if rng.random() > odds["wet_weeks"]:
            self.intensity["rain"] = 0.0

    def __repr__(self):
        return f"Weather({self.season}, {self.intensity})"
