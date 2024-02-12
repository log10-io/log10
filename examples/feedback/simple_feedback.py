from pprint import pprint
from typing import Literal

from pydantic import BaseModel, Field

from log10.feedback.feedback import Feedback
from log10.feedback.feedback_task import FeedbackTask
from log10.load import OpenAI


class EmojiFeedback(BaseModel):
    feedback: Literal["😀", "🙁"] = Field(..., description="User feedback with emojis")


client = OpenAI()
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
completion_id = completion.choices[0].id

task = FeedbackTask()
res = task.create(name="emoji_feedback_task", task_schema=EmojiFeedback.model_json_schema())
task_id = res["id"]
pprint(task)
# Example usage
fb = Feedback()
res = fb.create(task_id=task_id, data=EmojiFeedback(feedback="😀").model_dump_json(), completion_tags_selector=[str(completion_id)])
pprint(res)
