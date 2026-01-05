# Levi CLI

> **An AI-native, modular, and ultra-fast CLI agent framework — built for developers, by developers.**

Levi CLI is a next-generation command-line interface powered by LLM orchestration, designed to turn your terminal into an intelligent, self-extending assistant. Built with Python, `uv`, and rich tooling — fast, composable, and production-ready.

---

## ✨ Features

- **⚡ Blazing Fast** — Powered by [`uv`](https://github.com/astral-sh/uv): near-instant dependency resolution, locking (`uv lock`) and syncing (`uv sync`).
- **🧠 AI-First Architecture** — The `soul/` module implements adaptive reasoning, memory-aware sessions, and tool-use planning.
- **🧩 Modular Tool System** — Over 10+ built-in tools: `file`, `shell`, `web`, `todo`, `multiagent`, `think`, `tmail`, `acp`, etc.
- **🧑‍💻 Developer-Centric** — Clean `src/` structure, typed Python (PEP 561), rich CLI UX (`rich`, `prompt-toolkit`), and full testability.
- **🤖 Multi-Agent Ready** — Define and run subagents via `Task` tool; supports ACP (Agent Communication Protocol) and JSON-RPC wire protocol.

---

## 🚀 Quick Start

```powershell
# 1. Ensure Python 3.11+
python --version

# 2. Install dependencies (using uv)
uv sync

# 3. Run Levi CLI interactively
uv run levi

# Or try a one-off command
uv run levi shell "ls -la"
```

> 💡 Tip: Use `levi help` or `levi --help` anytime for full command reference.

---

## 📁 Project Structure

```
src/
├── levi_cli/                 # Main package
│   ├── cli.py                # CLI entrypoint (`levi` command)
│   ├── app.py                # Core application logic
│   ├── session.py            # Stateful session management
│   ├── soul/                 # "Soul" engine: reasoning, memory, tool selection
│   ├── tools/                # All built-in tools (file, web, todo, multiagent...)
│   ├── ui/                   # User interface layer (console, ACP, visualization)
│   ├── utils/                # Shared utilities (logging, path, async helpers)
│   └── wire/                 # Message serialization & transport (JSON-RPC)
├── agents/                   # Agent definitions (YAML configs, system prompts)
└── prompts/                  # Prompt templates (compact, init, etc.)
```

---

## 🛠️ Development

- Edit code in `src/levi_cli/`
- Add new tools in `src/levi_cli/tools/`
- Run tests: `uv run pytest tests/` (if tests exist)
- Update dependencies: `uv lock && uv sync`

---

## 🤝 Contributing

We welcome contributions! Please see [`CONTRIBUTING.md`](CONTRIBUTING.md) (to be added) for guidelines.

---

## 📜 License

MIT License — See [`LICENSE`](LICENSE) for details.

---

> ✨ Built with ❤️ and `uv` • [Levi CLI](https://github.com/your-org/levi-cli)