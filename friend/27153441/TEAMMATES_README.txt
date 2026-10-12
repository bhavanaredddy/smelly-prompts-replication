Replication review package

Evaluation.ipynb includes saved outputs from our GPT-4o partial replication.
data/results/results_all.json contains our 550 new runs.
data/experiments.json records our configurations.
data/results/*.jsonl contains the downloaded batch responses.
The results_all.json at the project root is the AUTHORS' original supplied data, not our new runs.
The GPT PDF plots were generated from our replication.

Scope: five games, no-smells and all-smells baselines, 20 random smell configurations per game, five repeats per configuration; GPT-4o only. Total: 550 runs.
GLMM regression cells were skipped; no statistical significance claims are established by those cells.

To run the notebook, use Python with ipykernel, pandas, numpy, matplotlib, seaborn, requests, scipy, and statsmodels. Run with the project folder as the working directory. Skip the original LaTeX/GLMM cells and leave Llama plot calls commented out.

Excluded: local Python environments, caches, secrets, and empty Llama plots.
