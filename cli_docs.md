# CLI

Use the `log10` CLI to list and download the completions, feedback, and feedback task data at [log10.io](https://log10.io).
Here's a [demo video](https://www.loom.com/share/4f5da34df6e94b7083b1e33c707deb53?sid=6b48acc4-72f1-49f2-b9ec-99905552781f).

## Get Started

Install the `log10-io` python package (version >= 0.6.7) and [setup Log10](README.md#⚙️-setup)

```bash
$ pip install log10-io
```

### Completions

You can list all your completions using [`log10 completions list`](#log10-completions-list). In addition, you can filter the completions by tag names (`--tags`) and created date `--from` and `--to`. For instance, here is the command to filter the completions with two tag names `foo` and `bar` and created between 2024-02-01 and 2024-02-29

```bash
$ log10 completions list --tags foo,bar --from 2024-2-1 --to 2024-2-29
```

#### Output:

```bash
Filter with tags: foo,bar
Filter with created date: 2024-02-01 to 2024-02-29
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ ID                                   ┃ Status  ┃ Created At  ┃ Prompt                       ┃ Completion                                ┃     Tags ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 497974e8-c1ed-4de7-90ab-8f104eb870te │ success │ 18 days ago │ You are a ping pong machine. │                                           │ bar, foo │
│                                      │         │             │ Ping?                        │ Pong!                                     │          │
│                                      │         │             │                              │                                           │          │
│ e8e4eaf5-871b-4e1d-8688-1234071aca1c │ success │ 18 days ago │ Where is the Eiffel Tower?   │ The Eiffel Tower is located in Paris, ... │ bar, foo │
│                                      │         │             │                              │                                           │          │
│ eb5ee140-6d93-4908-837f-9872345f1677 │ success │ 19 days ago │ You are a ping pong machine. │ Pong!                                     │ bar, foo │
│                                      │         │             │ Ping?                        │                                           │          │
│                                      │         │             │                              │                                           │          │
│ 98250940-bd7c-4b1d-9834-12b8a2fdec73 │ success │ 19 days ago │ Where is the Eiffel Tower?   │ The Eiffel Tower is located in Paris, ... │ bar, foo │
│                                      │         │             │                              │                                           │          │
│ b922d686-4aae-42ef-815e-60987sdfge16 │ success │ 19 days ago │ Where is the Eiffel Tower?   │ The Eiffel Tower is located in Paris, ... │ bar, foo │
│                                      │         │             │                              │                                           │          │
└──────────────────────────────────────┴─────────┴─────────────┴──────────────────────────────┴───────────────────────────────────────────┴──────────┘
total_completions=5
```

You can download these completions into a JSONL file by using [`log10 completions download`](#log10-completions-download) with the same options and specify the output file `--file`:

```bash
$ log10 completions download --tags foo,bar --from 2024-2-1 --to 2024-2-29 --file foo_bar.jsonl
Filter with tags: foo,bar
Filter with created date: 2024-02-01 to 2024-02-29
Download total completions: 5/5
Do you want to continue? [y/N]: y
100%|███████████████████████████████████████████████████████████████████████████| 5/5 [00:03<00:00,  1.31it/s]
```

To retrieve details for a specific completion, use [`log10 completions get`](#log10-completions-get).
For instance,

```bash
$ log10 completions get --id 497974e8-c1ed-4de7-90ab-8f104eb870te
```

output (only showing part of the full raw output):

```
{
  "id": "497974e8-c1ed-4de7-90ab-8f104eb870te",
  "created_at": "2024-02-23T19:37:17.709536+00:00",
  "status": "finished",
  "duration": 384,
  "kind": "completion",
  "request": {
    "prompt": [
      "You are a ping pong machine.\nPing?\n"
    ],
    "model": "gpt-3.5-turbo-instruct",
    "temperature": 0.5,
  },
  "response": {
    "choices": [
      {
        "finish_reason": "stop",
        "index": 0,
        "text": "\nPong!"
      }
    ],
  }
}
```

You can load completions' prompt messages and compare with other LLM models by using [`log10 completions benchmark_models`](#log10-completions-benchmark_models).
For instance,

```bash
log10 completions benchmark_models --ids 25572f3c-c2f1-45b0-9de8-d96be4c4e544 --models=gpt-3.5-turbo,mistral-small-latest,claude-3-haiku-20240307
```

output

```
Running gpt-3.5-turbo
Running mistral-small-latest
Running claude-3-haiku-20240307
completion_id: 25572f3c-c2f1-45b0-9de8-d96be4c4e544
original_request:
{
  "model": "gpt-4-0125-preview",
  "messages": [
    {
      "role": "system",
      "content": "Summarize the article in 30 words."
    },
    {
      "role": "user",
      "content": "\"Story of Your Life\" is a science fiction novella by American writer Ted Chiang, first published in Starlight 2 in 1998, and in 2002 in Chiang's collection of short stories, Stories of Your Life and Others. Its major themes are language and determinism. \"Story of Your Life\" won the 2000 Nebula Award for Best Novella, as well as the 1999 Theodore Sturgeon Award. It was nominated for the 1999 Hugo Award for Best Novella. The novella has been translated into Italian, Japanese, French and German.[1] A film adaptation of the story, Arrival, was conceived and adapted by Eric Heisserer. Titled and directed by Denis Villeneuve, it was released in 2016. It stars Amy Adams, Jeremy Renner, and Forest Whitaker and was nominated for eight Academy Awards, including Best Picture and Best Adapted Screenplay; it won the award for Best Sound Editing.[2][3][4] The film also won the 2017 Ray Bradbury Award for Outstanding Dramatic Presentation and the Hugo Award for Best Dramatic Presentation."
    }
  ],
  "temperature": 0.2
}
╭─────────────────────────┬───────────────────────────────────────────────────────┬──────────────────────────────────┬───────────────╮
│ Model                   │ Content                                               │ Total Token Usage (Input/Output) │ Duration (ms) │
├─────────────────────────┼───────────────────────────────────────────────────────┼──────────────────────────────────┼───────────────┤
│ gpt-4-0125-preview      │ "Story of Your Life" by Ted Chiang explores language  │ 323 (255/68)                     │ 2527          │
│                         │ and determinism, winning the 2000 Nebula and 1999     │                                  │               │
│                         │ Theodore Sturgeon Awards. Adapted into the film       │                                  │               │
│                         │ "Arrival" by Denis Villeneuve in 2016, it received    │                                  │               │
│                         │ critical acclaim and multiple awards, including an    │                                  │               │
│                         │ Academy Award for Best Sound Editing.                 │                                  │               │
├─────────────────────────┼───────────────────────────────────────────────────────┼──────────────────────────────────┼───────────────┤
│ gpt-3.5-turbo           │ "Story of Your Life" is a science fiction novella by  │ 295 (255/40)                     │ 2345          │
│                         │ Ted Chiang, exploring themes of language and          │                                  │               │
│                         │ determinism. It won awards and was adapted into the   │                                  │               │
│                         │ film Arrival in 2016.                                 │                                  │               │
├─────────────────────────┼───────────────────────────────────────────────────────┼──────────────────────────────────┼───────────────┤
│ mistral-small-latest    │ "Story of Your Life" is a Ted Chiang novella          │ 342 (282/60)                     │ 2087          │
│                         │ exploring language and determinism, winning Nebula    │                                  │               │
│                         │ and Sturgeon Awards. It was adapted into the 2016     │                                  │               │
│                         │ film "Arrival," which received multiple Academy Award │                                  │               │
│                         │ nominations and won for Best Sound Editing.           │                                  │               │
├─────────────────────────┼───────────────────────────────────────────────────────┼──────────────────────────────────┼───────────────┤
│ claude-3-haiku-20240307 │ "Story of Your Life" is a science fiction novella by  │ 320 (274/46)                     │ 1944          │
│                         │ Ted Chiang, exploring themes of language and          │                                  │               │
│                         │ determinism, winning multiple awards and inspiring a  │                                  │               │
│                         │ film adaptation, Arrival, which was critically        │                                  │               │
│                         │ acclaimed.                                            │                                  │               │
╰─────────────────────────┴───────────────────────────────────────────────────────┴──────────────────────────────────┴───────────────╯
```

You can also filter the completions by tags and generate a report in markdown file using `--file` or `-f`. And run our prompt analyzer (auto-prompt) using `--analyze_prompt`.

### Feedback Tasks and Feedback

To start adding feedback, first you need to define a feedback task with [`log10 feedback-task create`](#log10-feedback-task-create). Then you can add feedback to a logged completions with [`log10 feedback create`](#log10-feedback-create). For more details, you can read more in [log10's user documentation](https://log10.io/docs/feedback/feedback#add-feedback).

To list all feedback tasks, use [`log10 feedback-task list`](#log10-feedback-task-list)

```bash
$ log10 feedback-task list
                                                                                                        Feedback Tasks
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID                      ┃ Created At  ┃ Name                                       ┃ Required                                   ┃ Instruction                                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 04405cbc-3420-4901-97b6 │ 5 days ago  │ Demo TLDR Dataset Summary grading w/ note  │ coherence, accuracy, coverage, overall     │                                                   │
│ 15a5e099-a56a-49d0-b488 │ 29 days ago │ emoji_feedback_task                        │ feedback                                   │ Provide feedback using emojis                     │
└─────────────────────────┴─────────────┴────────────────────────────────────────────┴────────────────────────────────────────────┴───────────────────────────────────────────────────┘
```

and retrieve details about a specific task with [`log10 feedback-task get --id`](#log10-feedback-task-get)

To list and download your current feedback, use [`log10 feedback list`](#log10-feedback-list) and [`log10 feedback download`](#log10-feedback-download).
For instance you can list all feedback filtered by a feedback task `--task_id`:

```bash
$ log10 feedback list --task_id 04405cbc-3420-4901-97b6
                                                                                                           Feedback
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID                      ┃ Task Name                                 ┃ Feedback                                                                                         ┃ Completion ID            ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 4f5fefd1-06a4-415e-b56f │ Demo TLDR Dataset Summary grading w/ note │ {"note": "sounds like the girl is really into OP and OP is wary about committing too easily      │ 0b5bc07c-a976-49cc-bd160 │
│                         │                                           │ -which is absolutely not the right interpretation.", "overall": 2, "accuracy": 3, "coverage": 2, │                          │
│                         │                                           │ "coherence": 7}                                                                                  │                          │
│ 5525bf49-a870-465a-b6b7 │ Demo TLDR Dataset Summary grading w/ note │ {"note": "The summary conveys the main idea of the post.", "overall": 7, "accuracy": 7,          │ 431ee175-3a37-436a-bd627 │
│                         │                                           │ "coverage": 7, "coherence": 7}                                                                   │                          │
│ 9874ca7b-1c01-4785-8331 │ Demo TLDR Dataset Summary grading w/ note │ {"note": "•explicit purpose statement will make summary perfect. ", "overall": 6, "accuracy": 7, │ 447c3b69-6aea-4f4d-95846 │
│                         │                                           │ "coverage": 6, "coherence": 7}                                                                   │                          │
│ ad7dd317-3a19-4633-bf80 │ Demo TLDR Dataset Summary grading w/ note │ {"note": "Missing details of why.", "overall": 4, "accuracy": 7, "coverage": 4, "coherence": 7}  │ 1d2396bf-df44-4eaf-a9f03 │
│ 4b5edcb1-ca79-42a8-a0f5 │ Demo TLDR Dataset Summary grading w/ note │ {"note": "Should mention they're male.", "overall": 6, "accuracy": 7, "coverage": 6,             │ 264a3ca1-7bcc-4679-b80eb │
│                         │                                           │ "coherence": 7}                                                                                  │                          │
└─────────────────────────┴───────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────┴──────────────────────────┘
```

And to download to a JSONL file, use `log10 feedback download --task_id 04405cbc-3420-4901-97b6 --file feedback.jsonl`

To leverage your feedback and use AI to generate more feedback automatically, use [`log10 feedback predict`](#log10-feedback-predict). Please refer to this [doc](https://log10.io/docs/feedback/auto_feedback) for more details.

## CLI References

### Completions

```bash
$ log10 completions --help
Usage: log10 completions [OPTIONS] COMMAND [ARGS]...

  Manage logs from completions i.e. logs from users

Options:
  --help  Show this message and exit.

Commands:
  benchmark_models  Compare completions using different models and...
  download          Download completions to a jsonl file
  get               Get a completion by id
  list              List completions
```

#### log10 completions benchmark_models

```bash
log10 completions benchmark_models --help
Usage: log10 completions benchmark_models [OPTIONS]

  Compare completions using different models and generate report

Options:
  --ids TEXT            Completion IDs. Separate multiple ids with commas.
  --tags TEXT           Filter completions by specific tags. Separate multiple
                        tags with commas.
  --limit TEXT          Specify the maximum number of completions to retrieve
                        filtered by tags.
  --offset TEXT         Set the starting point (offset) from where to begin
                        fetching completions filtered by tags.
  --models TEXT         Comma separated list of models to compare
  --temperature FLOAT   Temperature
  --max_tokens INTEGER  Max tokens
  --top_p FLOAT         Top p
  --analyze_prompt      Run prompt analyzer on the messages.
  -f, --file TEXT       Specify the filename for the report in markdown
                        format.
  --help                Show this message and exit.
```

#### log10 completions download

```bash
$ log10 completions download --help
Usage: log10 completions download [OPTIONS]

  Download completions to a jsonl file

Options:
  --limit TEXT                    Specify the maximum number of completions to
                                  retrieve.
  --offset TEXT                   Set the starting point (offset) from where
                                  to begin fetching completions.
  --timeout INTEGER               Set the maximum time (in seconds) allowed
                                  for the HTTP request to complete.
  --tags TEXT                     Filter completions by specific tags.
                                  Separate multiple tags with commas.
  --from [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%d %H:%M:%S]
                                  Define the start date for fetching
                                  completions (inclusive). Use the format:
                                  YYYY-MM-DD.
  --to [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%d %H:%M:%S]
                                  Set the end date for fetching completions
                                  (inclusive). Use the format: YYYY-MM-DD.
  --compact                       Enable to download only the compact version
                                  of the output.
  -f, --file TEXT                 Specify the filename and path for the output
                                  file.
```

#### log10 completions get

```bash
$ log10 completions get --help
Usage: log10 completions get [OPTIONS]

  Get a completion by id

Options:
  --id TEXT  Completion ID
```

#### log10 completions list

```bash
$ log10 completions list --help
Usage: log10 completions list [OPTIONS]

  List completions

Options:
  --limit INTEGER                 Specify the maximum number of completions to
                                  retrieve.
  --offset INTEGER                Set the starting point (offset) from where
                                  to begin fetching completions.
  --timeout INTEGER               Set the maximum time (in seconds) allowed
                                  for the HTTP request to complete.
  --tags TEXT                     Filter completions by specific tags.
                                  Separate multiple tags with commas.
  --from [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%d %H:%M:%S]
                                  Define the start date for fetching
                                  completions (inclusive). Use the format:
                                  YYYY-MM-DD.
  --to [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%d %H:%M:%S]
                                  Set the end date for fetching completions
                                  (inclusive). Use the format: YYYY-MM-DD.
```

### Feedback

```bash
$ log10 feedback --help
Usage: log10 feedback [OPTIONS] COMMAND [ARGS]...

  Manage feedback for completions i.e. capturing feedback from users

Commands:
  create    Add feedback to a group of completions associated with a task
  download  Download feedback based on the provided criteria.
  get       Get feedback based on provided ID.
  list      List feedback based on the provided criteria.
  predict
```

#### log10 feedback create

```bash
$ log10 feedback create --help
Usage: log10 feedback create [OPTIONS]

  Add feedback to a group of completions associated with a task

Options:
  --task_id TEXT                  Task ID
  --values TEXT                   Feedback in JSON format
  --completion_tags_selector TEXT
                                  Completion tags selector
  --comment TEXT                  Comment
```

#### log10 feedback download

```bash
$ log10 feedback download --help
Usage: log10 feedback download [OPTIONS]

  Download feedback based on the provided criteria. This command allows
  fetching feedback for a specific task or across all tasks, with control over
  the starting point and the number of items to retrieve.

Options:
  --offset INTEGER  The starting index from which to begin the feedback fetch.
                    Leave empty to start from the beginning.
  --limit TEXT      The maximum number of feedback items to retrieve. Leave
                    empty to retrieve all.
  --task_id TEXT    The specific Task ID to filter feedback. If not provided,
                    feedback for all tasks will be fetched.
  -f, --file TEXT   Path to the file where the feedback will be saved. The
                    feedback data is saved in JSON Lines (jsonl) format. If
                    not specified, feedback will be printed to stdout.
```

#### log10 feedback get

```bash
$ log10 feedback get --help
Usage: log10 feedback get [OPTIONS]

  Get feedback based on provided ID.

Options:
  --id TEXT  Get feedback by ID
```

#### log10 feedback list

```bash
$ log10 feedback list --help
Usage: log10 feedback list [OPTIONS]

  List feedback based on the provided criteria. This command allows fetching
  feedback for a specific task or across all tasks, with control over the
  starting point and the number of items to retrieve.

Options:
  --offset INTEGER  The starting index from which to begin the feedback fetch.
                    Defaults to 0.
  --limit INTEGER   The maximum number of feedback items to retrieve. Defaults
                    to 25.
  --task_id TEXT    The specific Task ID to filter feedback. If not provided,
                    feedback for all tasks will be fetched.
```

#### log10 feedback predict

```bash
$ log10 feedback predict --help
Usage: log10 feedback predict [OPTIONS]

Options:
  --task_id TEXT         Feedback task ID
  --content TEXT         Completion content
  -f, --file TEXT        File containing completion content
  --completion_id TEXT   Completion ID
  --num_samples INTEGER  Number of samples to use for few-shot learning
```

### Feedback Task

```bash
$ log10 feedback-task --help
Usage: log10 feedback-task [OPTIONS] COMMAND [ARGS]...

  Manage tasks for feedback i.e. instructions and schema for feedback

Commands:
  create
  get
  list
```

#### log10 feedback-task create

```bash
$ log10 feedback-task create --help
Usage: log10 feedback-task create [OPTIONS]

Options:
  --name TEXT         Name of the task
  --task_schema TEXT  Task schema
  --instruction TEXT  Task instruction
  --completion_tags_selector TEXT  Completion tags selector
```

#### log10 feedback-task get

```bash
$ log10 feedback-task get --help
Usage: log10 feedback-task get [OPTIONS]

Options:
  --id TEXT  Get feedback task by ID
  --help     Show this message and exit.
```

#### log10 feedback-task list

```bash
$ log10 feedback-task list --help
Usage: log10 feedback-task list [OPTIONS]

Options:
  --limit INTEGER   Number of feedback tasks to fetch
  --offset INTEGER  Offset for the feedback tasks
```
