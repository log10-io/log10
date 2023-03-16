from pprint import pprint

import openai
orig_completion = openai.Completion.create
def intercepted_completion(**params):
    print("request")
    pprint(params)
    output = orig_completion(**params)
    print("response")
    pprint(output)
    return output

openai.Completion.create = intercepted_completion


orig_embedding = openai.Embedding.create
def intercepted_embedding(**params):
    print("request")
    pprint(params)
    output = orig_embedding(**params)
    print("response")
    # print(output)
    return output

openai.Embedding.create = intercepted_embedding