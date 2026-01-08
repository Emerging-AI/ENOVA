import re
from string import ascii_uppercase
import numpy as np
from lighteval.metrics.metrics import SampleLevelMetric, SamplingMethod
from lighteval.tasks.lighteval_task import LightevalTaskConfig
from lighteval.tasks.requests import Doc
from lighteval.metrics.metrics_sample import SampleLevelComputation


def mmlu_prompt(line, task_name: str = None):
    subject = line["subject"]
    query = f"The following are multiple choice questions (with answers) about {subject.replace('_', ' ')}.\n\nQuestion: {line['question']}"
    query += "".join([f"\n{key}. {choice}" for key, choice in zip(ascii_uppercase, line["choices"])])
    query += "\nAnswer:"

    gold_ix = ascii_uppercase.index(line["answer"]) if isinstance(line["answer"], str) else line["answer"]

    return Doc(
        task_name=task_name,
        query=query,
        choices=["A", "B", "C", "D"],
        gold_index=gold_ix,
        fewshot_sorting_class=line["choices"][gold_ix],
        instruction=f"The following are multiple choice questions (with answers) about {subject.replace('_', ' ')}.\n\n",
    )


def parse_mmlu_answer(output: str) -> str:
    """
    针对不同 LLM 输出风格的 MMLU 解析器
    1. 移除 <think> 标签内容
    2. 寻找常见的 "The answer is X" 模式
    3. 如果没有，则寻找最后一个出现的 A/B/C/D
    """
    # 步骤 1: 移除思考过程 (针对 Qwen-3/R1)
    # 使用非贪婪匹配移除 <think>...</think>
    clean_output = re.sub(r"<think>.*?</think>", "", output, flags=re.DOTALL).strip()

    # 步骤 2: 提取可能的选项候选词
    # 常见的模式如: "Final Answer: A", "The correct choice is (B)", "Ans: C"
    patterns = [
        r"(?:[Tt]he answer is|结论是|答案是|选项是|答案为)[:\s]*([A-D])",
        r"(?:[Ff]inal [Aa]nswer)[:\s]*([A-D])",
        r"\(([A-D])\)",
        r"([A-D])\s*$",  # 结尾处的单个字母
    ]

    for pattern in patterns:
        match = re.search(pattern, clean_output)
        if match:
            return match.group(1).upper()

    # 步骤 3: 兜底逻辑 —— 寻找全文最后一个出现的 A, B, C, 或 D
    # 过滤掉常见的干扰词，只寻找独立的字母
    all_matches = re.findall(r"\b([A-D])\b", clean_output)
    if all_matches:
        return all_matches[-1].upper()

    return ""  # 未解析成功


def mmlu_parsing_metric(doc: Doc, model_response: "ModelResponse") -> bool:
    """ """
    parsed_pred = parse_mmlu_answer(model_response.final_text[0])
    return parsed_pred == doc.choices[doc.gold_index]


class MMLUComputation(SampleLevelComputation):
    """ """

    def compute(self, doc: Doc, model_response: "ModelResponse") -> bool:
        return mmlu_parsing_metric(doc, model_response)


MMLU_CUSTOM_METRIC = SampleLevelMetric(
    metric_name="mmlu_robust_accuracy",
    higher_is_better=True,
    sample_level_fn=MMLUComputation(),
    category=SamplingMethod.GENERATIVE,
    corpus_level_fn=np.mean,
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
    # generation_size=5,
    num_fewshots=5,
    metrics=[MMLU_CUSTOM_METRIC],
    stop_sequence=["\n"],
    version=0,
)

TASKS_TABLE = [mmlu_all]
