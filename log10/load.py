from pprint import pprint
import requests
import openai
import os
import json

url = os.environ.get("LOG10_URL")
token = os.environ.get("LOG10_TOKEN")

orig_completion = openai.Completion.create


def intercepted_completion(**params):
    session_url = url + "/api/completions"
    output = None

    try:
        res = requests.request("PUT",
                               session_url, headers={"x-log10-token": token, "Content-Type": "application/json"})

        completionID = res.json()['completionID']

        res = requests.request("POST",
                               session_url + "/" + completionID, headers={"x-log10-token": token, "Content-Type": "application/json"}, json={
                                   "request": json.dumps(params)
                               })

        output = orig_completion(**params)

        res = requests.request("POST",
                               session_url + "/" + completionID, headers={"x-log10-token": token, "Content-Type": "application/json"}, json={
                                   "response": json.dumps(output)
                               })

    except Exception as e:
        print(e)

    return output


openai.Completion.create = intercepted_completion


orig_embedding = openai.Embedding.create


def intercepted_embedding(**params):
    output = orig_embedding(**params)
    return output


openai.Embedding.create = intercepted_embedding
