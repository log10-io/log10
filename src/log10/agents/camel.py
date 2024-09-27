import logging
from typing import List, Tuple

from dotenv import load_dotenv

from log10.llm import LLM, Message


load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - LOG10 - CAMEL - %(message)s",
)

# Repeat word termination conditions
# https://github.com/lightaime/camel/blob/master/examples/ai_society/role_playing_multiprocess.py#L63
repeat_word_threshold = 4
repeat_word_list = ["goodbye", "good bye", "thank", "bye", "welcome", "language model"]


def camel_agent(
    user_role: str,
    assistant_role: str,
    task_prompt: str,
    max_turns: int,
    user_prompt: str = None,
    assistant_prompt: str = None,
    summary_model: str = None,
    llm: LLM = None,
) -> Tuple[List[Message], List[Message]]:
    generator = camel_agent_generator(
        user_role,
        assistant_role,
        task_prompt,
        max_turns,
        user_prompt,
        assistant_prompt,
        summary_model,
        llm,
    )
    *_, last = generator
    return last


def camel_agent_generator(
    user_role: str,
    assistant_role: str,
    task_prompt: str,
    max_turns: int,
    user_prompt: str,
    assistant_prompt: str,
    summary_model: str,
    llm: LLM,
):
    try:
        assistant_inception_prompt = f"""Never forget you are a {assistant_role} and I am a {user_role}. Never flip roles! Never instruct me!
We share a common interest in collaborating to successfully complete a task.
You must help me to complete the task.
Here is the task: {task_prompt}. Never forget our task!
I must instruct you based on your expertise and my needs to complete the task.

I must give you one instruction at a time.
You must write a specific solution that appropriately completes the requested instruction.
You must decline my instruction honestly if you cannot perform the instruction due to physical, moral, legal reasons or your capability and explain the reasons.
Do not add anything else other than your solution to my instruction.
You are never supposed to ask me any questions you only answer questions.
You are never supposed to reply with a flake solution. Explain your solutions.
Your solution must be declarative sentences and simple present tense.
Unless I say the task is completed, you should always start with:

Solution: <YOUR_SOLUTION>

<YOUR_SOLUTION> should be specific and provide preferable implementations and examples for task-solving.
Always end <YOUR_SOLUTION> with: Next request."""

        if assistant_prompt is not None:
            assistant_inception_prompt = assistant_prompt

        user_inception_prompt = f"""Never forget you are a {user_role} and I am a {assistant_role}. Never flip roles! You will always instruct me.
We share a common interest in collaborating to successfully complete a task.
I must help you to complete the task.
Here is the task: {task_prompt}. Never forget our task!
You must instruct me based on my expertise and your needs to complete the task ONLY in the following two ways:

1. Instruct with a necessary input:
Instruction: <YOUR_INSTRUCTION>
Input: <YOUR_INPUT>

2. Instruct without any input:
Instruction: <YOUR_INSTRUCTION>
Input: None

The "Instruction" describes a task or question. The paired "Input" provides further context or information for the requested "Instruction".

You must give me one instruction at a time.
I must write a response that appropriately completes the requested instruction.
I must decline your instruction honestly if I cannot perform the instruction due to physical, moral, legal reasons or my capability and explain the reasons.
You should instruct me not ask me questions.
Now you must start to instruct me using the two ways described above.
Do not add anything else other than your instruction and the optional corresponding input!
Keep giving me instructions and necessary inputs until you think the task is completed.
When the task is completed, you must only reply with a single word <CAMEL_TASK_DONE>.
Never say <CAMEL_TASK_DONE> unless my responses have solved your task."""

        if user_prompt is not None:
            user_inception_prompt = user_prompt

        assistant_prompt = f"ASSISTANT PROMPT: \n {assistant_inception_prompt}"
        user_prompt = f"USER PROMPT: \n {user_inception_prompt}"

        assistant_messages = [
            Message(role="system", content=assistant_prompt),
            Message(role="user", content=assistant_prompt),
        ]
        user_messages = [
            Message(role="system", content=user_prompt),
            Message(
                role="user",
                content=user_prompt
                + " Now start to give me instructions one by one. Only reply with Instruction and Input.",
            ),
        ]
        repeat_word_counter = 0
        repeat_word_threshold_exceeded = False

        for i in range(max_turns):
            repeated_word_current_turn = False
            #
            # User turn
            #
            user_message = llm.chat(user_messages)
            user_messages.append(user_message)
            assistant_messages.append(Message(role="user", content=user_message.content))
            logging.info(f"User turn {i}: {user_message}")

            #
            # Assistant turn
            #
            assistant_message = llm.chat(assistant_messages)
            assistant_messages.append(assistant_message)
            user_messages.append(Message(role="user", content=assistant_message.content))
            logging.info(f"Assistant turn {i}: {assistant_message}")

            yield (user_messages, assistant_messages)

            #
            # Termination conditions.
            #
            for repeat_word in repeat_word_list:
                if repeat_word in assistant_message.content.lower() or repeat_word in user_message.content.lower():
                    repeat_word_counter += 1
                    repeated_word_current_turn = True
                    logging.info(f"Repeat word counter = {repeat_word_counter}")
                    if repeat_word_counter == repeat_word_threshold:
                        repeat_word_threshold_exceeded = True
                    break

            if not repeated_word_current_turn:
                repeat_word_counter = 0

            if (
                ("CAMEL_TASK_DONE" in user_messages[-2].content)
                or (i == max_turns - 1)
                or repeat_word_threshold_exceeded
            ):
                #
                # Summary turn
                #
                summary_context = "\n".join(
                    [
                        f"{turn.role.capitalize()} ({user_role if turn.role == 'user' else assistant_role}): {turn.content}"
                        for turn in assistant_messages
                        if turn.role in ["assistant", "user"]
                    ]
                )

                logging.info(f"summary context: {summary_context}")
                summary_system_prompt = """You are an experienced solution extracting agent.
Your task is to extract full and complete solutions by looking at the conversation between a user and an assistant with particular specializations.
You should present me with a final and detailed solution purely based on the conversation.
You should present the solution as if its yours.
Use present tense and as if you are the one presenting the solution.
You should not miss any necessary details or examples.
Keep all provided explanations and codes provided throughout the conversation.
Remember your task is not to summarize rather to extract the full solution."""

                summary_closing_prompt = f"""\n\nAs a reminder, the above context is to help you provide a complete and concise solution to the following task: {task_prompt}
Do not attempt to describe the solution, but try to answer in a way such that your answer will directly solve the task - not just describe the steps required to solve the task.
Only use the provided context above and no other sources.
Even if I told you that the task is completed in the context above you should still reply with a complete solution. Never tell me the task is completed or ask for the next request, but instead replay the final solution back to me."""
                summary_prompt = f"Task:{task_prompt}\n" + summary_context + summary_closing_prompt
                summary_messages = [
                    Message(role="system", content=summary_system_prompt),
                    Message(
                        role="user",
                        content="Here is the conversation: " + summary_prompt,
                    ),
                ]

                hparams = {"model": summary_model}
                message = llm.chat(summary_messages, hparams)
                assistant_messages.append(message)
                user_messages.append(Message(role="user", content=message.content))
                logging.info(message.content)

                # End of conversation
                yield (user_messages, assistant_messages)
                break

    except Exception as e:
        logging.error("Error in CAMEL agent: ", e)
