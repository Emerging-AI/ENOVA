# WARNING: machine managed in runtime, only used within eval session, do not import from here
from lighteval.metrics.metrics import Metrics
from lighteval.tasks.lighteval_task import LightevalTaskConfig  # noqa
from lighteval.tasks.requests import Doc

# def prompt_fn(line: dict, task_name: str):
#     """Defines how to go from a dataset line to a doc object.
#     Follow examples in src/lighteval/tasks/default_prompts.py, or get more info
#     about what this function should do in the README.
#     """
#     return Doc(
#         task_name=task_name,
#         query=line["question"],
#         choices=[f" {c}" for c in line["options"]],
#         gold_index=line["answer_index"],
#     )

# exact_match_metric = Metrics.exact_match
metric = Metrics.response_match

# task = LightevalTaskConfig(
#     name="custom_task1",
#     prompt_function=prompt_fn,  # Must be defined in the file or imported
#     hf_repo="{{dataset_path}}",
#     hf_subset="default",
#     hf_avail_splits=["validation", "test"],
#     evaluation_splits=["test"],
#     few_shots_split="validation",
#     few_shots_select="random_sampling_from_train",
#     metrics=[metric],
#     generation_size=256,
#     stop_sequence=["\n", "Question:"],
# )
# TASKS_TABLE = [task]
