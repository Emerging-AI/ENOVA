from typing import List
from enova.api.data_api import get_datasets
from enova.database.relation.transaction.session import db_router, PostgresqlEngine, get_session


def process_qa_data(row):
    """
    question, answers, selected_answer
    """
    return {
        "text": row["question"],
    }


DATASET_TYPE_ROW_PROCESS_MAP = {
    "qa": process_qa_data,
}


def download_dataset(dataset_id_list: List[str]):
    """ """
    dataset_info = {}
    dataset_filename = "quant_data.jsonl"
    datasets = get_datasets(dataset_id_list)
    with open(f"data/{dataset_filename}", "w", encoding="utf-8") as f:
        for dataset in datasets:
            data_list = []
            dataset_id = dataset["dataset_id"]
            if dataset["dataset_storage"][0]["storage_type"] == "pgsql":
                pg_engine = PostgresqlEngine(dataset["dataset_storage"][0]["storage_detail_config"])
                db_router.set_custom_db_engine(dataset_id, pg_engine)
                table_name = dataset["dataset_storage"][0]["storage_detail_config"]["table_name"]
                with get_session(dataset_id) as session:
                    for row in session.execute(text(f'select * from "{table_name}"')):
                        row_dct = row._mapping
                        f.write(json.dumps(DATASET_TYPE_ROW_PROCESS_MAP[dataset["dataset_type"]](row_dct)))

    with open("data/dataset_info.json", "w", encoding="utf-8") as f:
        json.dump(dataset_info, f, indent=4, ensure_ascii=False)
