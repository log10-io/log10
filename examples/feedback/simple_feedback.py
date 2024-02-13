import uuid
from pprint import pprint
from typing import Literal

from pydantic import BaseModel, Field

from log10.feedback.feedback import Feedback
from log10.feedback.feedback_task import FeedbackTask
from log10.load import OpenAI


#
# use log10 to log an openai completion
#

# create a unique id
unique_id = str(uuid.uuid4())
print(f"Use tag: {unique_id}")
client = OpenAI(tags=[unique_id])
completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {
            "role": "system",
            "content": "You are the most knowledgable Star Wars guru on the planet",
        },
        {
            "role": "user",
            "content": "Write the time period of all the Star Wars movies and spinoffs?",
        },
    ],
)
print(completion.choices[0].message)

#
# add feedback to the completion
#


# define a feedback task
class EmojiFeedback(BaseModel):
    feedback: Literal["😀", "🙁"] = Field(..., description="User feedback with emojis")


# create a feedback
fb = EmojiFeedback(feedback="😀")

task = FeedbackTask().create(name="emoji_task_test", task_schema=fb.model_json_schema())
task_dump = task.json()

print(fb.model_dump_json())
Feedback().create(task_id=task_dump["id"], values=fb.model_dump(), completion_tags_selector=[unique_id])
