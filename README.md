<div align="center">

# osx01

### A compact local coding agent powered by Ollama and open-source language models.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](#requirements)
[![Ollama](https://img.shields.io/badge/Inference-Ollama-111111?style=flat-square)](#how-it-works)
[![OpenAI SDK](https://img.shields.io/badge/API-OpenAI--compatible-412991?style=flat-square&logo=openai&logoColor=white)](#how-it-works)
[![Rich](https://img.shields.io/badge/UI-Rich-009485?style=flat-square)](#terminal-dashboard)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

**Inspect files · Search code · Edit projects · Run shell commands · Work fully locally**

[Overview](#overview) · [Features](#features) · [Quick Start](#quick-start) · [Safety](#security-and-safety) · [Architecture](#architecture)

</div>

## Overview

osx01 is a minimal autonomous coding-agent prototype that runs against a local [Ollama](https://ollama.com/) model through its OpenAI-compatible API. It gives a tool-capable model access to a focused set of project operations: reading, searching, writing, editing, directory inspection, and shell execution.

The repository intentionally keeps the implementation small. The core agent loop lives in one Python module, while an optional Rich-based dashboard displays task progress, tool activity, subsystem counters, and the final response.

No cloud model or hosted agent service is required.

## Features

- Local inference through Ollama.
- OpenAI-compatible tool-calling loop.
- Configurable model through the `OSX01_MODEL` environment variable.
- Configurable Ollama endpoint through `OLLAMA_HOST`.
- File reading with line numbers.
- Exact-string file editing and complete file writing.
- Recursive glob and regular-expression search.
- Shell command execution with timeouts and captured output.
- Optional live terminal dashboard built with Rich.
- Callback-based agent runner for custom interfaces and integrations.

## Terminal Dashboard

`osx01_ui.py` wraps the same agent engine in a sci-fi terminal dashboard. It shows the active model, current step, elapsed time, tool usage, recent activity, and an animated frequency display.

A verified screenshot has not been committed yet. The project documentation deliberately avoids mock product imagery; when a visual is added, it should be captured directly from the running terminal UI.

## Requirements

- Python 3.10 or newer
- [Ollama](https://ollama.com/)
- A local model that supports tool calling

The default model is `qwen2.5-coder:7b`.

## Quick Start

### 1. Install Ollama and download a model

```bash
ollama pull qwen2.5-coder:7b
```

### 2. Clone and prepare the project

```bash
git clone https://github.com/levomm/osx01.git
cd osx01
python -m venv .venv
```

Activate the virtual environment:

```bash
# Linux or macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

### 3. Run the agent

```bash
python osx01.py "Inspect this project and summarize its architecture"
```

Run the dashboard version:

```bash
python osx01_ui.py "Find duplicated logic and propose a safe refactor"
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OSX01_MODEL` | `qwen2.5-coder:7b` | Model used by the agent |

Example:

```bash
OSX01_MODEL=qwen2.5-coder:14b python osx01.py "Review the Python files"
```

## How It Works

1. The user task and system instructions are sent to the configured Ollama model.
2. The model may request one or more declared tools.
3. osx01 validates the tool-call arguments, executes the matching Python function, and returns the result to the model.
4. The loop continues until the model returns a final answer or reaches the configured step limit.

## Available Tools

| Tool | Purpose |
|---|---|
| `bash` | Run a shell command with a timeout |
| `read_file` | Read a UTF-8 text file with line numbers |
| `write_file` | Create or overwrite a file |
| `edit_file` | Replace one exact, unique text segment |
| `ls` | List directory contents |
| `glob` | Find files using a glob pattern |
| `grep` | Search file contents using a regular expression |

## Architecture

```text
osx01.py
├── Ollama/OpenAI-compatible client
├── local project tools
├── tool schemas and dispatcher
└── autonomous agent loop

osx01_ui.py
├── shared runtime state
├── agent callbacks
├── Rich terminal dashboard
└── background execution thread
```

## Security and Safety

> **Warning:** osx01 can execute shell commands and modify files with the permissions of the account that runs it.

Use it only inside projects and environments you are prepared to change. Review model-generated operations, keep important work under version control, and do not run the agent with administrator or root privileges.

The current prototype uses `subprocess.run(..., shell=True)`. This is powerful by design and should not be exposed as a network service or used on untrusted prompts without additional sandboxing, command policies, path restrictions, and explicit approval gates.

Recommended precautions:

- run it inside a disposable repository or container;
- commit or back up work before starting;
- use a low-privilege OS account;
- never place secrets in the working directory;
- review `git diff` after every task.

## Project Status

osx01 is an early proof of concept, not a production-ready coding agent. The core local tool-calling workflow is implemented, but automated tests, sandboxing, structured logging, cancellation, approval policies, and broader cross-platform validation are still needed.

## License

Released under the [MIT License](LICENSE).
