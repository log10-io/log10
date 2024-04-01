import random
from dotenv import load_dotenv
from random_word import RandomWords
from echo import ground_truth, noisy_predictor, EchoFeedback
from log10.llm import MockLLM, Message, Log10Config
from log10.feedback.feedback import Feedback
from log10.feedback.feedback_task import FeedbackTask


load_dotenv()

def mk_tag(prefix):
    rw = RandomWords()
    return f"{prefix}-{rw.get_random_word()}-{rw.get_random_word()}"


if __name__ == "__main__":
    # each time you run you have the same task name, but a different session name
    task_name = "echo"
    session_tag = mk_tag(task_name)
    input_offset = random.randint(0, 100)
    random_seed = 42
    # set a random seed for the noisy predictor.
    # This seed will be logged as a tag for reproducibility.
    random.seed(random_seed)
    config = Log10Config(tags=[session_tag, task_name, f"random_seed:{random_seed}"])
    # we will mock the llm with a function
    client = MockLLM(mock_function=noisy_predictor, log10_config=config)
    task = FeedbackTask().create(name=task_name, 
                                 task_schema=EchoFeedback.model_json_schema())
    task_id = task.json()["id"]
    for i in range(10):
        x = i + input_offset
        y = ground_truth(x)
        response = client.chat([Message(role="user", content=str(x))])
        y_hat = response.content
        l10fb = EchoFeedback.create(y, y_hat)        
        response = Feedback().create(task_id=task_id, values=l10fb.model_dump(), completion_tags_selector=config.tags)
        print(f"{response.json()['id']}: {l10fb}")
