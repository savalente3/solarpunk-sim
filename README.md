# Solarpunk Settlement Simulator

COMP4105 Designing Intelligent Agents — reassessment project.

A settlement simulated in weekly ticks. Two buildings each harvest solar
energy and rainwater from the week's weather, and have to spend both on their
residents and on the allotment on their roof. Each building runs two agents on
the same model — a building manager speaking for the residents, and an
allotment manager deciding what to plant, irrigate and harvest — which must
agree how to divide a budget that is not big enough for both. Surplus produce
goes to a shop agent that moves it between the buildings.

The two buildings are identical apart from which model family runs their
agents, so building 1 against building 2 is a model comparison.

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
python main.py --seed 0 --condition baseline
```

Runs one year -- four seasons of twelve weekly ticks -- and prints every week:
each building's storage, weather, what the residents and the beds asked for and
got, and anything harvested, then the shop. The same run is written to
`data/seed-0-baseline.jsonl`: a `_meta` line (seed, condition, date, model
names, opening crops), then one line per week, flushed as it goes. The same
seed always gives the same weather and the same opening crops.

## Layout

```
agents/       the agents, and the model config they are built from
settlement/   weather, infrastructure, buildings, allotments, the shop, the week
data/         one JSONL file per run
main.py       entry point
NOTES.md      design decisions, sources and limitations, for the report
```

## What actually runs

Each week, for each building:

- weather is drawn for the season, and the roof collects sun and rain into
  the battery and the rainwater tank
- the residents take their energy, water and food; a third of the water they
  use comes back into the greywater tank
- the beds take the water and power they need -- none on a week with rain
- the beds grow, slower when short of water or power, and ripe beds are
  harvested into the allotment's own storage

and the shop collects its own weather and runs itself on its panels.

Energy and water move between storages through `receive` and `spend`; produce,
held lot by lot and ageing, through `move()`. Those doors are what the agents
will use -- the agents themselves make no decisions yet, and nothing moves
between the buildings, the allotments and the shop.

Known: NVIDIA's free tier is shared capacity and drops requests under load, so
the season loop will need to survive a failed call rather than crash.
