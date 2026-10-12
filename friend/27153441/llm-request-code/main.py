import logging
import os

from experiments import workflow_defs
from req_smell_tracing.workflow import Workflow

logger = logging.getLogger(__name__)


def main():
    config = {
        "DATA_PATH": os.environ.get("DATA_PATH"),
        "GAMES_PATH": os.environ.get("GAMES_PATH"),
        "PROMPTS_PATH": os.environ.get("PROMPTS_PATH"),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "OLLAMA_URL": os.environ.get("OLLAMA_URL"),
        "COMMAND": os.environ.get("COMMAND"),
    }

    logging.basicConfig(level=logging.DEBUG)

    workflow = Workflow.load_workflow(
        config, workflow_defs=[workflow_defs.def_workflow]
    )
    workflow.run()


if __name__ == "__main__":
    main()
