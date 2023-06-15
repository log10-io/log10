import os
from log10.load import log10
from log10.evals import eval

# Choose provider
provider = "openai" # "anthropic"

if provider == "openai":
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
elif provider == "anthropic":
    import anthropic
    log10(anthropic)
    anthropicClient = anthropic.Client(os.environ["ANTHROPIC_API_KEY"])
    completion_func = anthropicClient.completion
    completion_params = {
        'model': 'claude-1',
        'temperature': 0,
        'max_tokens_to_sample': 1024,
        }
else:
    print(f"Unsupported provider option: {provider}. Supported providers are 'openai' or 'anthropic'.")

# Ground truth dataset to use for evaluation
eval_dataset = ('match_data.csv', {
                'input': 'my_input_column', 'ideal': 'my_output_column'})

# Specify which metrics to use. Options are:
# 'match': model_output.startswith(ideal)
# 'includes': ideal.lower() in model_output.lower()
# 'fuzzy_match': similar to includes but remove punctuation, articles and extra whitespace and compare both ways
eval_metric = 'includes'

# Path to output file to store the metrics
# Example from: https://github.com/openai/evals/blob/a24f20a357ecb3cc5eec8323097aeade9585796c/evals/elsuite/test/match.py
out_file_path = "match_output.csv"

# Get back and id and url for the summary of results and status
# todo: get back path to logfile; eval_id, eval_url =
eval(completion_func, completion_params, eval_dataset, eval_metric, out_file_path)
