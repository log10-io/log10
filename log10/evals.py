import csv
import json
import logging


def write_to_csv(file_name, row_data):
    with open(file_name, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(row_data)


def eval(test_name, completion_func, completion_params, completion_type, dataset, metric, out_file_path):
    csv_file_name, mapping = dataset
    with open(csv_file_name, 'r') as csv_file:
        reader = csv.DictReader(csv_file)
        examples = []
        for example in reader:
            mapped_example = {}
            for key, value in mapping.items():
                mapped_example[key] = example[value]
            examples.append(mapped_example)

        # todo: each example could be launched as separate threads or separate api calls to job runners
        write_to_csv(out_file_path, [
                     'input', 'ideal', 'model_completion', 'metric'])
        for example in examples:
            if metric == "match":
                try:
                    response = completion_func(
                        **completion_params, messages=json.loads(example['input']))
                except Exception as e:
                    logging.error("LOG10 eval: failed", e)
                if completion_type == 'chat':
                    model_completion = response['choices'][0]['message']['content']
                elif completion_type == 'completion':
                    model_completion = response['choices'][0]['text']
                write_to_csv(out_file_path, [example['input'], example['ideal'],
                             model_completion, model_completion.startswith(example['ideal'])])

                print(
                    f"\n\nIdeal:{example['ideal']}\nModel output:{model_completion}")
                print(
                    f"Correct:{model_completion.startswith(example['ideal'])}")
    return
