# TradingDesk: Offline Algorithmic Stock Review Engine

TradingDesk is an offline algorithmic stock analysis system that replicates institutional desk roles—**Market Researcher**, **Quantitative Analyst**, and **Risk & Compliance Officer**—using deterministic Python calculations on **Python 3.14.3**.

---

## Project Status: Sprint 0 Baseline

This repository has completed **Sprint 0 (Environment & Tooling Setup)** and is prepared for iterative sprint-by-sprint development.

See the internal [`ROADMAP.md`](file:///ROADMAP.md) for the master blueprint, sprint goals, role assignments, and git instructions.

---

## Directory Structure

```
TradingDeskProject/
├── .venv/                         # Python 3.14.3 Virtual Environment
├── reports/                       # Generated Markdown reports
│   └── .gitkeep
├── src/
│   └── tradingdesk/
│       ├── __init__.py
│       ├── models/                # Domain schemas (Sprint 1)
│       ├── data/                  # Market data providers (Sprint 1)
│       ├── quant/                 # BSM Greeks & Expected Move (Sprint 2)
│       ├── research/              # Offline research & sentiment (Sprint 2)
│       ├── risk/                  # Risk officer & compliance (Sprint 3)
│       └── reporters/             # Terminal UI & Markdown export (Sprint 4)
├── tests/                         # Pytest test suite
│   └── __init__.py
├── pyproject.toml                 # Package configuration
├── requirements.txt               # Pinned dependencies
├── requirements-dev.txt           # Testing & linting tools
└── README.md                      # Project documentation
```

---

## Development Setup

### 1. Environment
Ensure Python 3.14.3 is active:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Run Tests
```powershell
pytest
```

---

## Version History

### v0.1.0 (2026-11-09)
- **Sprint 0 Baseline Skeleton**: Initial release establishing project architecture and tooling.
- **Python 3.14.3 Environment**: Setup virtual environment and packaging configuration with `pyproject.toml`.
- **Modular Architecture**: Created package directory layout for market data ingestion, quantitative analytics, research sentiment, risk compliance, and report generation.
- **Dependency Management**: Pinned production (`requirements.txt`) and development (`requirements-dev.txt`) dependencies.
- **Testing Infrastructure**: Initialized `pytest` test suite with baseline skeleton validation.

