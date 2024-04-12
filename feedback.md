# Creating and Managing Feedback with Log10 client

log10 is a service, and a Python module, designed to collect and analyze feedback for LLM (Language Model) generated outputs. It provides a structured approach to managing feedback tasks, collecting feedback, and automating feedback generation using In-Context Learning (ICL), and custom models (coming soon).

In this document, we will cover details about the Python client. We also recommend, going over the [CLI documentation](https://github.com/log10-io/log10/blob/main/cli_docs.md) and 
[user documentation](https://log10.io/docs/feedback/feedback).
## Components

The feedback system currently consists of three main components:

1. `FeedbackTask`: Manages the creation and listing of feedback tasks.
2. `Feedback`: Manages the actual feedback entries related to specific tasks.
3. `AutoFeedbackICL`: Automates the generation of feedback using In-Context Learning (aka Prompting) based on existing feedback entries.

### FeedbackTask

The `FeedbackTask` component is responsible for defining the schema or structure for collecting feedback. It provides the following methods:

- `create`: Allows defining a new feedback task with a specific schema and optional name and instructions.
- `list`: Fetches existing feedback tasks, supporting pagination through `offset` and `limit` parameters.

### Feedback

The `Feedback` component manages the actual feedback entries related to specific tasks. It provides the following methods:

- `create`: Allows adding feedback entries for a specific task, requiring a task ID, values (structured according to the task's schema), completion tags, and an optional comment.
- `list` and `retrieve`: Allows listing and retrieving feedback entries by their ID.

### AutoFeedbackICL

The `AutoFeedbackICL` component automates the generation of feedback using In-Context Learning (ICL) based on existing feedback entries. It selects a sample of existing feedback entries for a given task and uses them as examples to generate new feedback for similar tasks or completions.

## Workflow

The feedback system follows a structured workflow:

1. Define a Feedback Task: A schema for feedback is defined using `FeedbackTask.create`.
2. Add Feedback: Users or systems add feedback for specific tasks using `Feedback.create`, adhering to the schema defined in step 1.
3. Automate Feedback Generation: `AutoFeedbackICL` can be used to automatically generate feedback for new tasks or completions by learning from existing feedback entries associated with a feedback task.

## Schemas

The feedback system uses JSON schemas to define the structure and rules for feedback tasks and feedback entries.

### Feedback Task Schema

The schema for a feedback task defines the structure and requirements for feedback related to that task. It typically includes:

- `title`: A descriptive name for the feedback task.
- `description`: An explanation of what the feedback task is about.
- `type`: Usually set to "object" to indicate that the feedback data should be a JSON object.
- `properties`: An object that defines the individual fields of the feedback, including their types (e.g., integer, string), possible values, and descriptions.
- `required`: An array listing the names of required properties.

Example:

```python
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
            }
        }
    }
)
```

### Feedback Schema

The schema for submitting feedback is implicitly determined by the schema of the feedback task to which it relates. When submitting feedback, you provide:

- `task_id`: The ID of the feedback task this feedback is for.
- `values`: A dictionary where keys correspond to the properties defined in the feedback task's schema, and values are the feedback given for those properties.
- `completion_tags_selector`: A list of tags associated with the feedback.
- `comment` (optional): A textual comment providing additional context or information about the feedback.

**Example:**

```python
fb_task = FeedbackTask()
       .create(name="summarization_v1", task_schema=fb_item.model_json_schema())
task_id = fb_task.json()["id"]
Feedback().create(task_id=task_id, values=fb_item.model_dump(), 
    completion_tags_selector=["summarization_v1", "summarization",
                            "hf:facebook/bart-large-cnn"])
```

## Feedback Task Name vs. Tags
Log10 provides a highly flexible way to define and organize your tasks. However, great flexibility, if not used carefully, can bring in great complexity. This is especially true with [naming things](https://martinfowler.com/bliki/TwoHardThings.html). Since log10 tasks have names and tags, you will need to decide on a naming semantics that is meaningful to you and your team.

While there are many good options, here's a simple organization. Let's say you are working on a summarization product. The name for the summarization task can be something as simple as `summarization` or `faceted_summarization` or `summarization_v1`. We recommend this name have some relevance to your product. 

You will want to periodically evaluate the quality of the summaries generated by your product. This will depend on the model version currently under deployment, the dataset it is evaluated with, the commit hash of the main branch of your product, and other factors. All of these are good candidates for tag names. Such an organization will allow you to naturally slice and dice your feedback data in a way that's useful to your product needs, and get the most out of Log10. 

By defining feedback tasks with specific schemas, collecting and curating feedback entries, and automating feedback generation, Log10 enables effective analysis and improvement of LLM outputs.