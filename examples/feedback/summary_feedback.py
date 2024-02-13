import uuid
from log10.feedback.feedback_task import FeedbackTask
from log10.feedback.feedback import Feedback

from log10.load import OpenAI

task = FeedbackTask().create(
    name="Summary grading task",
    task_schema={
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Summary Evaluation",
        "description": "Evaluates the quality of a summary based on four key aspects: Relevance, Coherence, Consistency, and Fluency.",
        "type": "object",
        "properties": {
            "Relevance": {
                "type": "integer",
                "minimum": 1,
                "maximum": 7,
                "description": "Evaluates if the summary includes only important information and excludes redundancies. A score of 1 indicates low relevance, with many redundancies or missing important information, while a score of 7 indicates high relevance, with all information being important and no redundancies.",
            },
            "Coherence": {
                "type": "integer",
                "minimum": 1,
                "maximum": 7,
                "description": "Assesses the logical flow and organization of the summary. A score of 1 indicates poor coherence with a disjointed or illogical flow, while a score of 7 indicates excellent coherence with a logical, well-organized flow.",
            },
            "Consistency": {
                "type": "integer",
                "minimum": 1,
                "maximum": 7,
                "description": "Checks if the summary aligns with the facts in the source document. A score of 1 indicates poor consistency with many discrepancies, while a score of 7 indicates high consistency with complete alignment to the source.",
            },
            "Fluency": {
                "type": "integer",
                "minimum": 1,
                "maximum": 7,
                "description": "Rates the grammar and readability of the summary. A score of 1 indicates poor fluency with numerous grammatical errors and poor readability, while a score of 7 indicates excellent fluency with grammatically correct sentences and high readability.",
            },
        },
        "required": ["Relevance", "Coherence", "Consistency", "Fluency"],
    },
)

print(task.json())

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

# add feedback to the completion
Feedback().create(
    task_id=task.json()["id"],
    values={
        "Relevance": 7,
        "Coherence": 6,
        "Consistency": 7,
        "Fluency": 7,
    },
    completion_tags_selector=[unique_id],
)
