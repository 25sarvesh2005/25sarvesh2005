## Sarvesh Sharma · Systems & AI Engineer

I build backend systems, data/BI engines, and applied AI tools in **Python**, **TypeScript**, **FastAPI**, and **PostgreSQL**—focused on concurrency safety, deterministic evaluation, and reproducible CI.

[sarvesh.sh7890@gmail.com](mailto:sarvesh.sh7890@gmail.com) · **Live:** [Whitfield WMS](https://warehouse-management-system-jade-seven.vercel.app) · [SmartRIS 6G Simulator](https://smartris.vercel.app)

---

### Interactive Boss Raid

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/25sarvesh2005/25sarvesh2005/output/assets/battle-dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/25sarvesh2005/25sarvesh2005/output/assets/battle-light.svg" />
    <img src="https://raw.githubusercontent.com/25sarvesh2005/25sarvesh2005/output/assets/battle-light.svg" width="100%" alt="Interactive Dungeon Raid Battle Arena on @25sarvesh2005" />
  </picture>
</div>

<p align="center">
  <a href="https://github.com/25sarvesh2005/25sarvesh2005/issues/new?title=raid%7Cstrike&body=Optional+battle+cry+(max+58+chars):+">
    <img src="./assets/static/btn-strike.svg" width="196" alt="Strike Boss (16-28 DMG)" />
  </a>
  &nbsp;
  <a href="https://github.com/25sarvesh2005/25sarvesh2005/issues/new?title=raid%7Coverclock&body=Optional+battle+cry+(max+58+chars):+">
    <img src="./assets/static/btn-overclock.svg" width="196" alt="Overclock Crit (26-44 DMG)" />
  </a>
  &nbsp;
  <a href="https://github.com/25sarvesh2005/25sarvesh2005/issues/new?title=raid%7Cbuff&body=Optional+battle+cry+(max+58+chars):+">
    <img src="./assets/static/btn-buff.svg" width="196" alt="Focus Buff (+10 Next Hit)" />
  </a>
  &nbsp;
  <a href="https://github.com/25sarvesh2005/25sarvesh2005/issues/new?title=raid%7Ctavern&body=Leave+a+short+hello+for+the+profile+log:+">
    <img src="./assets/static/btn-tavern.svg" width="196" alt="Sign Guestbook Note" />
  </a>
</p>

<p align="center">
  <sub>Click any action above and submit the pre-filled Issue to play—GitHub Actions processes your roll, updates the battle log, and closes the Issue in ~15 seconds. New repository commits also auto-strike the active boss (`3x DMG`).</sub>
</p>

---

### Selected Engineering Work

| System | Engineering Focus | Primary Stack | Verification |
| :--- | :--- | :--- | :--- |
| [**Whitfield WMS**](https://github.com/25sarvesh2005/WAREHOUSE-MANAGEMENT-SYSTEM) · [Live](https://warehouse-management-system-jade-seven.vercel.app) | Multi-tenant double-entry inventory engine using PostgreSQL `SELECT FOR UPDATE` row locking, FastMCP server tools, and voice intake | Python · FastAPI · React 19 · TypeScript · PostgreSQL | Live · CI |
| [**RepoScore**](https://github.com/25sarvesh2005/REPO-Score) | Isolated Docker execution sandbox + AST/Semgrep/OSV static & security checks driving a deterministic 10-dimension repository scorer | Python · FastAPI · Next.js · Docker · Redis | CI · MIT |
| [**RevenueOS**](https://github.com/25sarvesh2005/RevenueOS) | Automated Kimball star-schema ETL, DAX/`.pbit` Power BI workbook compiler, anomaly detection, and packaged Electron desktop UI | Python · Electron · FastAPI · PostgreSQL | CI · Desktop |
| [**CityCareClinic**](https://github.com/25sarvesh2005/CityCareClinic) | Multi-tenant clinical scheduling platform unified across a React 19 app, ChromaDB RAG, FastMCP server, and Telegram patient bot | Python · React 19 · TanStack · MongoDB | CI · MIT |
| [**SmartRIS**](https://github.com/25sarvesh2005/SMARTRIS) · [Live](https://smartris.vercel.app) | Reconfigurable Intelligent Surface (RIS) & 6G holographic beamforming physics simulator | Python · FastAPI · React · TypeScript | Live · CI |
| [**VeriRAG**](https://github.com/25sarvesh2005/VeriRAG) | Dual dense + BM25 Reciprocal Rank Fusion retriever with cross-encoder reranking and claim-level entailment checks | Python · FastAPI · PyTorch · SentenceTransformers | CI · MIT |

Additional shipped projects: [**telephony_ai**](https://github.com/25sarvesh2005/telephony_ai) (FastAPI + SQLAlchemy outbound recovery telephony), [**AIAUTOPILOT_FORM**](https://github.com/25sarvesh2005/AIAUTOPILOT_FORM) (Electron + Playwright + Gemini document-to-form automation), and [**canteenapp**](https://github.com/25sarvesh2005/canteenapp) (Kotlin + Jetpack Compose + Firebase Android app).

---

### Core Stack

| Area | Tools & Frameworks |
| :--- | :--- |
| **Backend & Storage** | `Python` · `FastAPI` · `Pydantic v2` · `SQLAlchemy` · `Alembic` · `PostgreSQL` · `MongoDB` · `Redis` |
| **AI & Retrieval** | `Google Gemini` · `PyTorch` · `SentenceTransformers` · `BM25` · `ChromaDB` · `FastMCP` · `Playwright` |
| **Frontend & Desktop** | `TypeScript` · `React 18/19` · `Next.js` · `TanStack` · `Vite` · `Tailwind CSS` · `Electron` |
| **Testing & Delivery** | `Docker` · `GitHub Actions` · `Pytest` · `Ruff` · `Mypy` · `ESLint` |

---

### GitHub Telemetry & Earned Milestones

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/25sarvesh2005/25sarvesh2005/output/assets/trainer-dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/25sarvesh2005/25sarvesh2005/output/assets/trainer-light.svg" />
    <img src="https://raw.githubusercontent.com/25sarvesh2005/25sarvesh2005/output/assets/trainer-light.svg" width="100%" alt="GitHub Telemetry & Earned Milestones for @25sarvesh2005" />
  </picture>
</div>

<details>
<summary>Telemetry formula &amp; 20-minute sync details</summary>

[`scripts/fetch_github_data.py`](scripts/fetch_github_data.py) and [`scripts/compute_gamification.py`](scripts/compute_gamification.py) aggregate only repositories owned by `@25sarvesh2005` (excluding forks, external collaborator repos, and self-stars) every 20 minutes via [`.github/workflows/refresh-profile.yml`](.github/workflows/refresh-profile.yml).

- **XP formula:** `(Contributions × 2) + (Active Days × 5) + (Merged PRs × 35) + (Documented Repos × 40) + (CI Repos × 60) + (External Stars × 25) + (Languages ≥1% × 50)`
- **Level curve:** `floor(sqrt(XP / 20)) + 1`
- **Commit synergy:** New contributions detected between syncs deal `delta × 3 DMG` to the active raid boss.

</details>

---

### Contribution Activity

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/25sarvesh2005/25sarvesh2005/output/assets/snake-dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/25sarvesh2005/25sarvesh2005/output/assets/snake-light.svg" />
    <img src="https://raw.githubusercontent.com/25sarvesh2005/25sarvesh2005/output/assets/snake-light.svg" width="100%" alt="Contribution grid snake animation for @25sarvesh2005" />
  </picture>
</div>
