# Requirements smells in LLM prompts: replication and extension ($0)

Replication and extension of Vogelsang et al., *On the Impact of Requirements Smells in
Prompts: The Case of Automated Traceability*, ICSE-NIER 2025
([arXiv 2501.04810](https://arxiv.org/abs/2501.04810), artifact
[doi:10.6084/m9.figshare.27153441](https://doi.org/10.6084/m9.figshare.27153441)).

Everything here runs for free: the analyses reuse the authors' 6,100 saved LLM answers and
a teammate's 550 GPT-4o re-runs; new LLM work uses a local model through Ollama.

**Findings so far: see [`REPORT.md`](REPORT.md).** Each step also writes its own
`results/<step>/README.md` with tables and figures.

## Layout

| Path | What |
| --- | --- |
| `artifact/` | The Figshare artifact, downloaded unchanged (flat file layout) |
| `friend/27153441/` | Teammate's replication package (550 new GPT-4o runs in `data/results/results_all.json`) |
| `src/smellrep/` | Shared code: data loading, the authors' metrics, Ollama client, rule-based detector |
| `scripts/` | One script per step (below) |
| `notebooks/Evaluation_local.ipynb` | The authors' notebook, patched to read local files, executed |
| `generated/` | LLM outputs (fixed requirements, local tracing runs, detector answers) and caches |
| `results/` | Tables (CSV), figures (PNG) and a README per step |

## Steps

| Step | Script | Needs LLM? |
| --- | --- | --- |
| A. Reproduce the paper's tables, plots and mixed models | `scripts/a_replicate.py` (also `scripts/patch_notebook.py`) | no |
| B. Check the friend's 550 runs against the originals | `scripts/b_compare_friend.py` | no |
| Improved statistics (within-requirement models) | `scripts/g_stats.py` | no |
| Breakdown by smell type / game / requirement | `scripts/h_breakdown.py` | no |
| Smell detector: rule-based vs. LLM | `scripts/d_detector.py [--run-llm]` | optional |
| Smell fixer (blind / rewrite / oracle) | `scripts/e_fixer.py --mode ...` | yes (local) |
| C. Fresh tracing runs (clean / smelly / fixed) | `scripts/c_trace_local.py` | yes (local) |
| Evaluate C + fixer | `scripts/f_eval_local.py` | no |

## Setup (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\scripts\run_analysis.ps1                 # all non-LLM steps

winget install Ollama.Ollama               # free local LLM runtime
ollama pull llama3.2:3b                    # 2 GB; llama3.1:8b works too but is ~3x slower on CPU
.\scripts\run_local_pipeline.ps1           # fixer, local tracing, LLM detector, evaluation
.\scripts\run_local_pipeline.ps1 -Model llama3.1:8b
```

On a laptop CPU (i5-1235U, 16 GB), one tracing prompt takes about 2-4 minutes with
`llama3.2:3b`; the whole local pipeline takes about 1.5 hours. Scripts resume where they stopped.

## Credits

Data, prompts, code and ground truth: Vogelsang et al. (Figshare artifact above). The 550
GPT-4o re-runs in `friend/` come from a teammate's partial replication. Please cite both.
