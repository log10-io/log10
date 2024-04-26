import uuid

from log10.feedback.feedback import Feedback
from log10.feedback.feedback_task import FeedbackTask
from log10.load import OpenAI


task = FeedbackTask().create(
    name="Summary grading task",
    completion_tags_selector=["summarization"],
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
            "content": "You help users summarize reddit posts. The message from the user will be the post to summarize?",
        },
        {
            "role": "user",
            "content": "Yesterday, I accidentally dropped my Motorola Atrix 2 and the screen cracked really badly. My phone is still fully functional, but it's a bit difficult to see what I'm doing when I'm texting or web browsing, etc. \n\nAnyway, I stupidly didn't buy insurance for my phone and I'm not eligible for an upgrade until next May! AT&T offers some options as far as getting a no-commitment phone at a slight discount, but spending $300-$600 for a new phone isn't really in the budget right now. I know when you start a new contract, AT&T offers their phones at a fraction of the price (i.e., $100 for a $500 phone) so would I be able to take advantage of that? It seems like I wouldn't, but I'm a little confused with how their policy works that way! I was thinking of visiting my local store.\n\nSo I was looking at [Motorola's repair center] and they said they won't repair phones that have been physically abused - so that means dropped, submerged in water, ran over, exposed to heat, etc. \n\nI found a couple websites that will repair your phone if you send it in. [Doctor Quick Fix] will do it for $110 and I'm still waiting on a quote from [CPR](\n\nSo my question is, have any of you used this company, or know anyone who has used it? Should I trust these companies? Do you have any recommendations? What should I do to get my phone fixed?",
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
