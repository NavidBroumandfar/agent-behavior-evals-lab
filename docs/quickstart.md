# Quickstart

Agent Behavior Evals Lab is local-first and deterministic by default.

## Requirements

- Python 3.10 or newer
- No credentials for the deterministic gate
- Optional: Docker for the containerized check

## Fresh Clone

```bash
git clone https://github.com/NavidBroumandfar/agent-behavior-evals-lab.git
cd agent-behavior-evals-lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[dev]"
python3 scripts/dev.py check
```

Equivalent Makefile path:

```bash
make quickstart
```

## CLI

After installing the project in a virtual environment:

```bash
agent-evals check
agent-evals test
agent-evals lint
agent-evals run-baseline
agent-evals report
agent-evals version
```

The CLI wraps existing local scripts. It does not add live model execution.

## Docker Check

```bash
docker build -t agent-behavior-evals-lab .
docker run --rm agent-behavior-evals-lab
```

## What The Gate Does Not Do

The deterministic quality gate does not call model providers, run local models,
execute OpenClaw or Hermes, use credentials, collect network data, or perform
external actions.
