import os

from google.api_core.exceptions import NotFound
from google.cloud import bigquery


# todo: add requirements.txt file
# todo: add instructions for bigquery integration


def initialize_bigquery(debug=False):
    # Configure the BigQuery client
    project_id = os.environ.get("LOG10_BQ_PROJECT_ID")
    dataset_id = os.environ.get("LOG10_BQ_DATASET_ID")
    completions_table_id = os.environ.get("LOG10_BQ_COMPLETIONS_TABLE_ID")

    client = bigquery.Client(project=project_id)

    def dataset_exists(dataset_id):
        try:
            client.get_dataset(dataset_id)  # API request
            return True
        except NotFound:
            return False

    def table_exists(dataset_id, completions_table_id):
        try:
            table_ref = client.dataset(dataset_id).table(completions_table_id)
            client.get_table(table_ref)  # API request
            return True
        except NotFound:
            return False

    # Check if dataset exists
    if dataset_exists(dataset_id):
        if debug:
            print(f"Dataset {dataset_id} exists.")
    else:
        if debug:
            print(f"Dataset {dataset_id} does not exist. Creating...")
        # Create the dataset
        dataset_ref = client.dataset(dataset_id)
        dataset = bigquery.Dataset(dataset_ref)
        # Set the location, e.g., "US", "EU", "asia-northeast1", etc.
        dataset.location = "US"
        created_dataset = client.create_dataset(dataset)  # API request

        if debug:
            print(f"Dataset {created_dataset.dataset_id} created.")

    client_dataset = client.dataset(dataset_id)

    # Check if table exists
    if table_exists(dataset_id, completions_table_id):
        if debug:
            print(f"Table {completions_table_id} exists in dataset {dataset_id}.")
    else:
        if debug:
            print(f"Table {completions_table_id} does not exist in dataset {dataset_id}. Creating...")
        # Create the table
        table_ref = client_dataset.table(completions_table_id)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(script_dir, "schemas", "bigquery.json")
        schema = client.schema_from_json(schema_path)
        table = bigquery.Table(table_ref, schema=schema)
        created_table = client.create_table(table)  # API request

        if debug:
            print(f"Table {created_table.table_id} created.")

    # load dataset and table
    table_ref = client_dataset.table(completions_table_id)
    table = client.get_table(table_ref)

    return client, table
