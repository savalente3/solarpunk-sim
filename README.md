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

Runs one year -- four seasons of twelve weekly ticks -- printing one line a
week, and serves a live view of the settlement: open the address it prints to
watch every wake, answer, trade and death the moment it happens (`live.py`).
The run is written to `data/version3/seed-0-no-memory.jsonl`: a `_meta` line
(version, seed, condition, date, model names, opening crops), then one line per
week, flushed as it goes -- plus a `.csv` for graphs and a `.txt` to read. The
same seed always gives the same weather and the same opening crops.

`--condition` is `no-memory` or `memory`: in a memory run each building manager
is also shown the community board, everything that has happened in the
settlement so far.

If a model stops answering, the run pauses with every finished week on disk.
Run the same command with `--resume` to carry on: the weeks already on file are
run again with the answers they recorded -- in seconds, and exactly as before --
and the models take over from the week it paused in.

## Layout

```
agents/       the agents, their instructions and answer shapes, and the model config
settlement/   weather, infrastructure, buildings, allotments, produce, the shop, the week
data/         one folder per design version, three files per run
main.py       entry point: runs a year and records it
live.py       the live view: serves the visualisation and streams the run to it
evaluation.py measures every finished run, compares them seed by seed, draws the graphs
NOTES.md      design decisions, sources and limitations, for the report
```

The visualisation itself (`visualisation/`) is kept local and is not part of
the repository.

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
on disk. The design decisions behind all of this are in NOTES.md.
