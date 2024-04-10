import litellm

from log10.litellm import Log10LitellmLogger


log10_handler = Log10LitellmLogger(tags=["litellm_completion", "stream"])
litellm.callbacks = [log10_handler]
response = litellm.completion(
    model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Count to 10."}], stream=True
)
for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
