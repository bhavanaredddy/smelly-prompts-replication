# On the Impact of Requirements Smells in Prompts: The Case of Automated Traceability

## Artifact Evaluation

This research artifact offers the means to run the framework for reproducing the results presented in our paper. It includes Docker images and detailed instructions for executing them, enabling users to replicate our experiments and achieve results comparable to those reported in the paper. Therefore, we claim the badges for artifacts being available, functional, and reusable.

The paper's preprint is available at [Arxiv](https://arxiv.org/abs/2501.04810). The artifact will be made available on [Figshare](https://doi.org/10.6084/m9.figshare.27153441).

## Requirements

To utilize these artifacts effectively, familiarity with Docker and a basic understanding of generative AI models are recommended. Since our work involves generative AI models, users will need either an API key for the OpenAI API or access to a machine capable of running the Llama 3.1 model with 70 billion parameters (32-64 GB RAM, 2-4 NVIDIA A100 80 GB, 150-200 GB disk space).

## Dataset Overview

The dataset contains the following data:

| Path                                 | Description                                                                  |
| ------------------------------------ | ---------------------------------------------------------------------------- |
| `evaluation.ipynb`                   | The Jupyter notebook containing our evaluation.                              |
| `games/`                             | The code and requirements in CSV format for all games.                       |
| `ground_truth.csv`                   | The ground truth in CSV format.                                              |
| `llm-request-code/`                  | The code used to generate the samples and prompt the LLMs via APIs.          |
| `prompts/`                           | The prompts used with the LLMs.                                              |
| `requirements_and_ground_truth.xlsx` | The requirements and ground truth (for both raters) as an Excel spreadsheet. |
| `results_all.json`                   | The results retrieved from the LLMs in JSON format.                          |
| `smell_types_and_categories.pdf`     | A PDF file listing all considered smell types with their categories.         |

## Instructions on Running the Experiments

### Quick Instructions

1. Create a `data/` directory next to the `llm-request-code/` directory
2. In `compose.yaml`, set `OPENAI_API_KEY` to your OpenAI API key
3. Run `docker compose up llm-request-code`
4. Wait for the script to complete, the results will be stored in `data/results/results_all.json`

Using the OpenAI API, this will cost approximately less than $1 USD as not all experiments are run by default (see below).

### Detailed Instructions

Our experiments are defined in the `llm-request-code/experiments` folder. There you can find the following two files:

- `experiments_def.py`
  - This file defines all experiments that we have run. You will find definitions for running the experiments for all of the five games used, and for different variations of smelly requirements, as described in the paper.
  - Depending on whether you want to use the OpenAI API or a local instance of Llama 3.1 running in Ollama, comment out the GPT or Ollama block in lines 6-18.
- `workflow_defs.py`
  - This file defines our workflows, which list the steps run consecutively to execute the experiments. At the bottom of the file, the two commands `run`, and `batchtoresults` are defined. These will be of use later.
  - Make sure to set `BATCH=False` in line 19 when using Llama, as it does not support batch mode.
  - If using batch mode, make sure to see the notes below.

**Caution:** Running all experiments (in batch mode) using the OpenAI API **will cost approximately $20 USD**. This is only an estimation and may differ depending on the current pricing. Running the requests without batch mode will also be more expensive. We recommend, running only a single experiment for evaluating the functionality of our artifact. Therefore, in `experiments_def.py` we commented out some experiments, reducing the cost to approximately less than $1 USD even without batch mode.

You can run the experiments using Docker by running the services defined in `compose.yaml`:

- `llm-request-code`
  - The service running our experiments. Make sure to set the environment variables to your OpenAI key or Ollama instance URL (if not using the Ollama instance configured in `compose.yaml`). Set the `COMMAND` variable to the desired command (see above).
- `ollama`
  - A service running an Ollama instance with Nvidia GPU acceleration.
  - When using this service instead of another local Ollama instance, make sure that you have GPU support in Docker configured using NVIDIA Container Toolkit. See the [NVIDIA documentation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) or [Ollama docker repository](https://github.com/valiantlynx/ollama-docker) for instructions on how to do that.

### Notes on Using Batch Mode

As stated above, when using the OpenAI API to run *all experiments*, batch mode is recommended as it reduces cost and also heavily reduces the time it takes to run all experiments. Using batch mode is a multi-step process:

1. Using the `run` command with batch mode activated as stated above generates a new batch in the OpenAI API
2. Log in to [OpenAI](https://platform.openai.com/) and navigate to *Batches*
3. After the batch is completed, download the resulting `.jsonl` file, rename it to `batch_results.jsonl` and place it in `data/results`
4. Run the `batchtoresults` command to generate the results as above


### Notes on LLM choice
We used Ollama to allow for an easy change in the used LLM. You can specify the LLM you want to use in function `def_experiments` in file `experiments/experiments_def.py`. Lines 13-18 already contain the commented out code for using Llama3.1:70b. You can replace this by any model you have access to. 
