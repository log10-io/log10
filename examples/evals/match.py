import os
from log10.load import log10
from log10.evals import eval
import openai

log10(openai)

openai.api_key = os.getenv("OPENAI_API_KEY")

# Define completion spec
completion_func = openai.ChatCompletion.create
completion_params = {
    'model': "gpt-3.5-turbo",
    'temperature': 0,
    'max_tokens': 1024,
    'top_p': 1,
    'frequency_penalty': 0,
    'presence_penalty': 0,
}

# Ground truth dataset to use for evaluation
eval_dataset = ('my_eval_data.csv', {
                'input': 'my_input_column', 'ideal': 'my_output_column'})

# Specify which metrics to use
eval_metric = 'match'

# Name your test
test_name = "my_test"

# Path to output file to store the metrics
out_file_path = "my_eval_output.csv"

completion_type = 'chat'

# Get back and id and url for the summary of results and status
# todo: get back path to logfile; eval_id, eval_url =
eval(test_name, completion_func, completion_params, completion_type,
     eval_dataset, eval_metric, out_file_path)
