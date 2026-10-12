# Smell detector baseline

72 smelly and 116 non-smelly requirement texts (clean versions of all requirements plus the smelly list per game). *Type hit rate*: share of smelly requirements whose labelled smell type is among the flagged types. Rule-based word lists are in `src/smellrep/rules.py`.

| detector          |   precision |   recall |    f1 |   accuracy |   TP |   FP |   FN |   TN |   type_hit_rate |   category_hit_rate |   mean_types_flagged |
|:------------------|------------:|---------:|------:|-----------:|-----:|-----:|-----:|-----:|----------------:|--------------------:|---------------------:|
| rule_based        |       0.513 |    0.806 | 0.627 |      0.633 |   58 |   55 |   14 |   61 |           0.556 |               0.653 |                0.862 |
| llm (llama3.2:3b) |       0.605 |    0.361 | 0.452 |      0.665 |   26 |   17 |   46 |   99 |           0.139 |               0.236 |                0.457 |


## Recall and type hit rate per labelled smell type

| gold_type               |   recall | llm (llama3.2:3b) |   recall | rule_based |   type_hit_rate | llm (llama3.2:3b) |   type_hit_rate | rule_based |
|:------------------------|-----------------------------:|----------------------:|------------------------------------:|-----------------------------:|
| ambiguities             |                        0.200 |                 0.800 |                               0.000 |                        0.400 |
| logical_inconsistencies |                        0.380 |                 0.620 |                               0.250 |                        0.000 |
| negative                |                        0.400 |                 1.000 |                               0.000 |                        1.000 |
| numerical_discrepancies |                        0.400 |                 0.600 |                               0.200 |                        0.200 |
| optional_parts          |                        0.400 |                 0.800 |                               0.200 |                        0.600 |
| passive_voice           |                        0.200 |                 1.000 |                               0.000 |                        1.000 |
| subjective_language     |                        0.570 |                 0.640 |                               0.290 |                        0.360 |
| vague_pronouns          |                        0.400 |                 1.000 |                               0.000 |                        1.000 |
| weak_verbs              |                        0.400 |                 1.000 |                               0.400 |                        1.000 |
