from string import ascii_uppercase

from lighteval.metrics.metrics import Metrics
from lighteval.tasks.lighteval_task import LightevalTaskConfig
from lighteval.tasks.requests import Doc


def mmlu_prompt(line, task_name: str = None):
    subject = line["subject"]
    query = f"The following are multiple choice questions (with answers) about {subject.replace('_', ' ')}.\n\nQuestion: {line['question']}"
    query += "".join([f"\n{key}. {choice}" for key, choice in zip(ascii_uppercase, line["choices"])])
    query += "\nAnswer:"

    gold_ix = ascii_uppercase.index(line["answer"]) if isinstance(line["answer"], str) else line["answer"]

    return Doc(
        task_name=task_name,
        query=query,
        choices=[" A", " B", " C", " D"],
        gold_index=gold_ix,
        fewshot_sorting_class=line["choices"][gold_ix],
        instruction=f"The following are multiple choice questions (with answers) about {subject.replace('_', ' ')}.\n\n",
    )


mmlu_all = LightevalTaskConfig(
    name="mmlu-all",
    prompt_function=mmlu_prompt,
    hf_repo="lighteval/mmlu",
    hf_subset="all",
    hf_avail_splits=["auxiliary_train", "test", "validation", "dev"],
    evaluation_splits=["test"],
    few_shots_split="dev",
    few_shots_select=None,
    generation_size=5,
    metrics=[Metrics.exact_match],
    stop_sequence=["\n"],
    version=0,
)

TASKS_TABLE = [mmlu_all]
