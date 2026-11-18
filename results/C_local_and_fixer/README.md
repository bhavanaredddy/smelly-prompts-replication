# Step C + smell fixer: all local models

One folder per local model holds the details. GPT-4o and Llama-3.1-70B rows are the authors' saved runs, for reference. Scores on the 72 smell-able requirements, against the original intent.

| model             | condition     |   acc_smellable_intent |   f1_smellable_intent |   said_yes |
|:------------------|:--------------|-----------------------:|----------------------:|-----------:|
| gpt-4o-2024-08-06 | clean         |                  0.958 |                 0.699 |      0.745 |
| gpt-4o-2024-08-06 | smelly        |                  0.903 |                 0.585 |      0.702 |
| llama3.1:70b      | clean         |                  0.944 |                 0.611 |      0.713 |
| llama3.1:70b      | smelly        |                  0.875 |                 0.539 |      0.681 |
| llama3.1:8b       | clean         |                  0.764 |                 0.540 |      0.904 |
| llama3.1:8b       | smelly        |                  0.736 |                 0.508 |      0.872 |
| llama3.1:8b       | fixed_rewrite |                  0.778 |                 0.507 |      0.894 |
| llama3.1:8b       | fixed_oracle  |                  0.764 |                 0.504 |      0.904 |
| llama3.2:3b       | clean         |                  0.681 |                 0.205 |      0.979 |
| llama3.2:3b       | smelly        |                  0.681 |                 0.113 |      0.979 |
| llama3.2:3b       | fixed_rewrite |                  0.708 |                 0.149 |      0.968 |
| llama3.2:3b       | fixed_oracle  |                  0.681 |                 0.168 |      0.979 |


## Line F1 recovered by the fixer

| model       | fixer         |   clean |   smelly |   fixed |   fixed_minus_smelly |   ci_low |   ci_high |   share_of_gap_recovered |
|:------------|:--------------|--------:|---------:|--------:|---------------------:|---------:|----------:|-------------------------:|
| llama3.1_8b | fixed_rewrite |   0.540 |    0.508 |   0.507 |               -0.001 |   -0.052 |     0.057 |                   -0.042 |
| llama3.1_8b | fixed_oracle  |   0.540 |    0.508 |   0.504 |               -0.004 |   -0.075 |     0.066 |                   -0.118 |
| llama3.2_3b | fixed_rewrite |   0.205 |    0.113 |   0.149 |                0.036 |   -0.044 |     0.115 |                    0.387 |
| llama3.2_3b | fixed_oracle  |   0.205 |    0.113 |   0.168 |                0.055 |    0.014 |     0.101 |                    0.591 |


## Fixer text quality

| model       | mode    |   changed |   drifted |   rule_flags_before |   rule_flags_after |
|:------------|:--------|----------:|----------:|--------------------:|-------------------:|
| llama3.1_8b | blind   |     0.681 |     0.028 |               1.222 |              0.889 |
| llama3.1_8b | oracle  |     0.694 |     0.028 |               1.222 |              1.000 |
| llama3.1_8b | rewrite |     0.972 |     0.028 |               1.222 |              0.750 |
| llama3.2_3b | blind   |     0.056 |     0.028 |               1.222 |              1.222 |
| llama3.2_3b | oracle  |     0.250 |     0.028 |               1.222 |              1.111 |
| llama3.2_3b | rewrite |     0.972 |     0.097 |               1.222 |              0.639 |
