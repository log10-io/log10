import openai
from langchain.chains import LLMChain, SimpleSequentialChain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate

from log10.load import log10, log10_session


log10(openai)


llm = OpenAI(temperature=0.9, model_name="gpt-3.5-turbo-instruct")

with log10_session():
    prompt = PromptTemplate(
        input_variables=["product"],
        template="What is a good name for a company that makes {product}?",
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    second_prompt = PromptTemplate(
        input_variables=["company_name"],
        template="Write a catchphrase for the following company: {company_name}",
    )
    chain_two = LLMChain(llm=llm, prompt=second_prompt)
    overall_chain = SimpleSequentialChain(chains=[chain, chain_two], verbose=True)
    # Run the chain specifying only the input variable for the first chain.
    catchphrase = overall_chain.run("colorful socks")
    print(catchphrase)

with log10_session():
    third_prompt = PromptTemplate(
        input_variables=["month"],
        template="What is a good country to travel during {month}?",
    )

    chain_three = LLMChain(llm=llm, prompt=third_prompt)

    fourth_prompt = PromptTemplate(
        input_variables=["country_name"],
        template="Write a 1 day itinerary to {country_name}",
    )
    chain_four = LLMChain(llm=llm, prompt=fourth_prompt)

    overall_chain_two = SimpleSequentialChain(chains=[chain_three, chain_four], verbose=True)

    # Run the chain specifying only the input variable for the first chain.
    catchphrase_two = overall_chain_two.run("April")
    print(catchphrase_two)
