# Step C + smell fixer: fresh tracing runs with llama3.2:3b (free, local)

20 tracing runs on CPU (50 min total, temperature 0, so one run per condition is deterministic). Runs with parse problems or missing requirements: 0. The prompt is byte-for-byte the authors' prompt. Rows for GPT-4o and Llama-3.1-70B come from the authors' saved no-smell / all-smell runs, for reference.

*smellable* = the 72 requirements that have a smelly variant. `acc_smellable_intent` and `f1_smellable_intent` score against the clean requirement's ground truth, i.e. whether the original intent was still traced correctly.

| model             | condition     |   acc_all |   acc_smellable_label |   acc_smellable_intent |   f1_smellable_intent |   said_yes |   n_smellable |
|:------------------|:--------------|----------:|----------------------:|-----------------------:|----------------------:|-----------:|--------------:|
| gpt-4o-2024-08-06 | clean         |     0.957 |                 0.958 |                  0.958 |                 0.699 |      0.745 |            72 |
| gpt-4o-2024-08-06 | smelly        |     0.851 |                 0.819 |                  0.903 |                 0.585 |      0.702 |            72 |
| llama3.1:70b      | clean         |     0.947 |                 0.944 |                  0.944 |                 0.611 |      0.713 |            72 |
| llama3.1:70b      | smelly        |     0.830 |                 0.792 |                  0.875 |                 0.539 |      0.681 |            72 |
| llama3.2:3b       | clean         |     0.745 |                 0.681 |                  0.681 |                 0.205 |      0.979 |            72 |
| llama3.2:3b       | smelly        |     0.638 |                 0.542 |                  0.681 |                 0.113 |      0.979 |            72 |
| llama3.2:3b       | fixed_rewrite |     0.670 |                 0.569 |                  0.708 |                 0.149 |      0.968 |            72 |
| llama3.2:3b       | fixed_oracle  |     0.638 |                 0.542 |                  0.681 |                 0.168 |      0.979 |            72 |


## Did the fixer recover the loss? (local model, smellable requirements)

95% CIs from a bootstrap over requirements. `share_of_gap_recovered` = (fixed - smelly) / (clean - smelly); it is unstable when the clean-smelly gap is tiny.

| metric         | fixer         |   clean |   smelly |   fixed |   fixed_minus_smelly |   ci_low |   ci_high |   share_of_gap_recovered |
|:---------------|:--------------|--------:|---------:|--------:|---------------------:|---------:|----------:|-------------------------:|
| correct_intent | fixed_rewrite |   0.681 |    0.681 |   0.708 |                0.028 |    0.000 |     0.069 |                  nan     |
| correct_intent | fixed_oracle  |   0.681 |    0.681 |   0.681 |                0.000 |    0.000 |     0.000 |                  nan     |
| f1_intent      | fixed_rewrite |   0.205 |    0.113 |   0.149 |                0.036 |   -0.044 |     0.115 |                    0.387 |
| f1_intent      | fixed_oracle  |   0.205 |    0.113 |   0.168 |                0.055 |    0.014 |     0.101 |                    0.591 |
| correct        | fixed_rewrite |   0.681 |    0.542 |   0.569 |                0.028 |    0.000 |     0.069 |                    0.200 |
| correct        | fixed_oracle  |   0.681 |    0.542 |   0.542 |                0.000 |    0.000 |     0.000 |                    0.000 |


## Fixer text quality (smelly requirements only)

`sim_*` = content-word overlap (Jaccard, stop words removed) with the authors' clean version. `drifted` = the rewrite overlaps clearly more with a *different* requirement's clean text (the fixer mixed requirements up). Rule flags come from the rule-based detector.

| mode    |   n |   changed |   sim_input_to_clean |   sim_fixed_to_clean |   drifted |   rule_flags_before |   rule_flags_after |   own_smell_flag_removed |
|:--------|----:|----------:|---------------------:|---------------------:|----------:|--------------------:|-------------------:|-------------------------:|
| blind   |  72 |     0.056 |                0.660 |                0.660 |     0.028 |               1.222 |              1.222 |                    0.000 |
| oracle  |  72 |     0.250 |                0.660 |                0.660 |     0.028 |               1.222 |              1.111 |                    0.111 |
| rewrite |  72 |     0.972 |                0.660 |                0.472 |     0.097 |               1.222 |              0.639 |                    0.333 |

| mode    | smell_category   |   changed |   sim_gain |
|:--------|:-----------------|----------:|-----------:|
| blind   | lexical          |     0.083 |      0.649 |
| blind   | semantic         |     0.000 |      0.667 |
| blind   | syntactic        |     0.100 |      0.662 |
| oracle  | lexical          |     0.375 |      0.653 |
| oracle  | semantic         |     0.143 |      0.656 |
| oracle  | syntactic        |     0.250 |      0.675 |
| rewrite | lexical          |     1.000 |      0.478 |
| rewrite | semantic         |     0.964 |      0.463 |
| rewrite | syntactic        |     0.950 |      0.477 |


## Per smell category (local model, smellable requirements)

| smell_category   | condition     |   acc_intent |   f1_intent |   n |
|:-----------------|:--------------|-------------:|------------:|----:|
| lexical          | clean         |        0.625 |       0.195 |  24 |
| lexical          | fixed_oracle  |        0.625 |       0.249 |  24 |
| lexical          | fixed_rewrite |        0.708 |       0.118 |  24 |
| lexical          | smelly        |        0.625 |       0.204 |  24 |
| semantic         | clean         |        0.607 |       0.162 |  28 |
| semantic         | fixed_oracle  |        0.607 |       0.064 |  28 |
| semantic         | fixed_rewrite |        0.607 |       0.106 |  28 |
| semantic         | smelly        |        0.607 |       0.018 |  28 |
| syntactic        | clean         |        0.850 |       0.257 |  20 |
| syntactic        | fixed_oracle  |        0.850 |       0.203 |  20 |
| syntactic        | fixed_rewrite |        0.850 |       0.217 |  20 |
| syntactic        | smelly        |        0.850 |       0.133 |  20 |

![conditions](conditions.png)
