import csv
import json
import os
import subprocess
import tempfile

from log10.llm import Messages
from log10.utils import fuzzy_match, parse_field


def run_metric(metric, ideal, model_output):
    ideal = parse_field(ideal)
    for ideal_candidate in ideal:
        # Ref: https://github.com/openai/evals/blob/a24f20a357ecb3cc5eec8323097aeade9585796c/evals/elsuite/utils.py
        if metric == "match":
            if model_output.startswith(ideal_candidate):
                return True
        elif metric == "includes":  # case-insensitive
            # Ref: https://github.com/openai/evals/blob/a24f20a357ecb3cc5eec8323097aeade9585796c/evals/elsuite/basic/includes.py
            if ideal_candidate.lower() in model_output.lower():
                return True
        elif metric == "fuzzy_match":
            if fuzzy_match(ideal_candidate, model_output):
                return True
    return False


def write_to_csv(file_name, row_data):
    with open(file_name, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(row_data)


def eval(llm, dataset, metric, out_file_path):
    csv_file_name, mapping = dataset
    with open(csv_file_name, "r") as csv_file:
        reader = csv.DictReader(csv_file)
        examples = []
        for example in reader:
            mapped_example = {}
            for key, value in mapping.items():
                mapped_example[key] = example[value]
            examples.append(mapped_example)

        # todo: each example could be launched as separate threads or separate api calls to job runners
        write_to_csv(out_file_path, ["input", "ideal", "model_completion", "metric"])
        for example in examples:
            messages = Messages.from_dict(json.loads(example["input"]))
            model_completion = llm.chat(messages)

            example_metric = run_metric(metric, example["ideal"], model_completion.content)
            write_to_csv(
                out_file_path,
                [example["input"], example["ideal"], model_completion, example_metric],
            )
            print(f"\n\nIdeal:{example['ideal']}\nModel output:{model_completion.content}")
            print(f"Correct:{example_metric}")
    return


def compile(code):
    with tempfile.NamedTemporaryFile(suffix=".c", delete=False) as temp:
        temp.write(code.encode())
        temp.close()
        process = subprocess.run(["gcc", temp.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.remove(temp.name)  # remove the temp file
        if process.returncode == 0:
            return True
        else:
            return False, process.stderr.decode()
