# Solarpunk Settlement Simulator

COMP4105 Designing Intelligent Agents — reassessment project.

A solarpunk settlement simulated day by day, under one weather drawn each
week. Two buildings each harvest solar energy and rainwater, and have to spend
both on their tenants and on the allotment on their roof. Each building runs
two agents on the same model: an allotment manager says what the beds need and
what to plant, and a building manager decides for the whole building, with a
budget that is not big enough for both. Ripe beds are picked automatically.
Surplus produce goes to a shop agent that moves produce and water between the
buildings.

The two buildings are identical apart from the model running their agents
(gpt-oss:20b or gemma4:26b) and their two opening crops. The models swap
buildings on odd seeds, so neither building's luck favours one model. The shop
runs on a third model, nemotron-3.5-lightning, in every run.

The question is whether a shared written history -- the community board --
helps the building managers manage the settlement under scarcity.

## Setup

```bash
conda env create -f environment.yml
conda activate solarpunk-sim

ollama pull gpt-oss:20b
ollama pull gemma4:26b
ollama pull nemotron-3.5-lightning

cp .env.example .env    # optional: a LangSmith key, to trace every model call
```

The three models run locally through [Ollama](https://ollama.com) -- keep
`ollama serve` running -- so no API key is needed. A LangSmith key from
[smith.langchain.com](https://smith.langchain.com) with `LANGSMITH_TRACING=true`
shows every model call, with its prompt and answer, on LangSmith's website.

## Run

```bash
python main.py --seed 0 --condition no-memory
```

Runs one year -- four seasons of twelve weeks, seven days each -- printing
one line a week, and serves a live view of the settlement: open the address it prints to
watch every wake, answer, trade and death the moment it happens (`live.py`).
The run is written to `data/seed-0-no-memory.jsonl`: a `_meta` line
(seed, condition, date, model names, opening crops), then one line per
week, flushed as it goes -- plus a `.csv` for graphs and a `.txt` to read. The
same seed always gives the same weather and the same opening crops.

`--condition` is `no-memory` or `memory`: in a memory run each building manager
is also shown the community board, everything that has happened in the
settlement so far.

The experiment in the report is seeds 0 to 5, each in both conditions: 12 runs.

If a model stops answering, the run pauses with every finished week on disk.
Run the same command with `--resume` to carry on: the weeks already on file are
run again with the answers they recorded -- in seconds, and exactly as before --
and the models take over from the week it paused in.

## Evaluate

```bash
python evaluation.py
```

Measures every finished run in `data/`, compares them seed by seed
(memory against no memory for each model, and the two models against each
other in each condition, with Wilcoxon signed-rank tests), and writes
`summary.csv`, `tests.csv` and the graphs into `data/evaluation/`.

## Layout

```
agents/       the agents, their instructions and answer shapes, and the model config
settlement/   weather, infrastructure, buildings, allotments, produce, the shop, the week
data/         three files per run, and evaluation/ with the results
main.py       entry point: runs a year and records it
live.py       the live view: serves the visualisation and streams the run to it
evaluation.py measures every finished run, compares them seed by seed, draws the graphs
```

`visualisation/index.html` is the visualisation UI, served by `live.py`.

## Visualisation

A browser view of the settlement, for following a run rather than measuring it
(the results come from `evaluation.py`, not from here).

- **Live:** `main.py` serves it while a run goes, at the address it prints
  (`http://127.0.0.1:8765/visualisation/`, or the next free port up to 8775).
  Everything streams in as it happens -- each week's weather, every day, alarm,
  wake, answer, trade, rot and death -- and a browser that opens late is sent
  everything so far first.
- **Past runs:** the same page can replay any run in `data/` from its `.jsonl`
  file: choose it from the list, or drop the file on the page, then play,
  pause, change the speed, scrub through the year, or skip to the next time an
  agent is woken. A run still going can be reloaded as it grows.
- **What it shows:** the two buildings and the shop with their storages, beds
  and tenants; the season and weather; each agent's answer and its reasoning;
  and the community board, as a building manager sees it in the memory
  condition. The scene can be moved, turned and zoomed.

Nothing in the visualisation changes a run: `live.py` only listens. `live.py`
and the visualisation were written with AI assistance (Claude, Anthropic).

## What happens in a run

Each week one sky is drawn for the season over the whole settlement, and each
day:

- every roof collects sun and rain into its battery and rainwater tank
- the tenants use their share of energy, water and food; a third of the water
  they use comes back as greywater
- the beds take what the building manager gives them, grow, and ripe beds are
  picked into the allotment's store; produce older than three weeks rots
- a storage falling below 40% wakes its managers at once; otherwise they are
  checked every few days, or when they asked to be

When a building wakes, its allotment manager says what the beds need and what
to plant, and its building manager decides: the tenants' shares, the beds'
supply, what to move into food storage, what to plant, and what to send to or
ask of the shop, whose agent answers there and then. Tenants die after three
days with almost no water or three weeks with almost no food, and the building
stops. A model that cannot be reached pauses the run with every finished week
on disk.

In the memory condition the building manager is also shown the community
board: the last two weeks day by day, and one line for each week before them.
The allotment managers and the shop never see it.
