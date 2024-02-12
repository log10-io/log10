import logging
from pydantic import BaseModel, Field
from typing import Literal
from log10.feedback.feedback_task import FeedbackTask
from log10.feedback.feedback import Feedback

httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.DEBUG)

feedback_task = FeedbackTask()
t_s = {
  "type": "object",
  "properties": {
    "feedback": {
      "type": "string",
      "enum": ["😀", "😬", "😐", "🙁", "😫"]
    }
  }
}
class EmojiFeedback(BaseModel):
    feedback: Literal["😀", "🙁"] = Field(..., description="User feedback with emojis")

eft = EmojiFeedback(feedback="😀")

# convert t_s to json
task = feedback_task.create(name="emo", task_schema=eft.model_json_schema())
task_dump = task.json()
print(task_dump["id"])

fb = Feedback()
print(eft.model_dump_json())
fb.create(task_id=task_dump["id"], rate=eft.model_dump(), completion_tags_selector=["give_me_feedback"])