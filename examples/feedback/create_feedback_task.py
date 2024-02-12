import logging
from log10.feedback.feedback_task import FeedbackTask

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
# convert t_s to json
import json
t_s = json.dumps(t_s)
task = feedback_task.create(name="emo", task_schema=t_s)
