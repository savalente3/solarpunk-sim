# Solarpunk Settlement Simulator

COMP4105 Designing Intelligent Agents — reassessment project.

Two identical buildings each harvest solar energy and rainwater, and must
spend both on their residents and on their rooftop allotment. Each building
runs two agents on the same model: a building manager and an allotment
manager. Surplus produce goes to a shop agent that redistributes stock and
is responsible for keeping produce diverse.

High-yield crops are the rational individual choice, but a settlement that
grows only tomatoes eats badly — and only the shop sees both allotments.

## Setup

```bash
conda env create -f environment.yml
conda activate solarpunk-sim

cp .env.example .env    # then fill in NVIDIA_API_KEY and GOOGLE_API_KEY
```

Keys: [build.nvidia.com](https://build.nvidia.com) (free credits, no card) and
[aistudio.google.com/apikey](https://aistudio.google.com/apikey) (free tier).

## Run

```bash
python main.py
```

## Layout

```
agents/       building and shop agents, model config
settlement/   the model: weather, building, day
main.py       entry point
```

## Where the numbers come from

Areas are a design choice -- 200 m2 of roof, 60 m2 of panels, 140 m2 of beds.
The rates are real UK figures:

| quantity            | figure                            | source |
| ------------------- | --------------------------------- | ------ |
| rainfall            | 715.6 mm/yr, Nottingham 1991-2020 | [Met Office, Watnall](https://www.metoffice.gov.uk/research/climate/maps-and-data/location-specific-long-term-averages/gcrje93b8) |
| rooftop PV yield    | 950 kWh/kWp/yr, approx 0.52 kWh/m2/day | [MCS MIS 3002](https://payaca.com/uk/solar-yield-calculator) |
| vegetable irrigation| 30-50 L/m2/week, approx 5 L/m2/day dry | [RHS](https://rhs170.rhs.org.uk/vegetables/watering) |
| allotment yield     | 1 kg/m2/season                    | [Univ. of Sussex, Brighton allotments](https://www.britishecologicalsociety.org/city-allotments-match-farming-productivity-per-square-metre/) |

`panel_yield` and `rain_yield` in `settlement/building.py` are the rates on
the brightest and wettest day, so an average day (intensity 0.5) gives the
real-world average: 31 kWh and 392 litres.

## Models

One model per role. Buildings run different families so that building 1 vs
building 2 is a model comparison.

| role       | profile          | model                             |
| ---------- | ---------------- | --------------------------------- |
| building 1 | `nemotron_super` | nvidia/nemotron-3-super-120b-a12b |
| building 2 | `gemini`         | gemini-3.6-flash                  |
| shop       | `gpt_oss`        | openai/gpt-oss-20b                |

Nemotron and gpt-oss are open weights, Gemini is proprietary.

`model_configs` in `agents/config/model_config.py` also lists
`nemotron_reasoning` and `mistral_nemotron`. Both are unreliable on NVIDIA's
free tier -- they answer once and then time out or return 500. Left in place
in case the capacity situation changes.

## Status

- [x] `Weather` — one day's sun and rain intensity, seeded
- [x] `Building` — collects energy and water from the weather
- [x] agents constructed from model config, and answering
- [ ] residents and plots — something for the stores to be spent on
- [ ] structured output — agents return numbers, not prose
- [ ] managers agree the energy/water split
- [ ] allotment plants / waters / harvests
- [ ] residents consume, surplus to shop
- [ ] `Season` — loop days, write JSONL
- [ ] metrics, conditions, statistics and figures

Known: NVIDIA's free tier is shared capacity and drops requests under load,
so the season loop will need to handle a failed call rather than crash.
