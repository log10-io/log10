import openai

from log10.load import log10


log10(openai)

# Example from: https://python.langchain.com/en/latest/use_cases/question_answering.html
# Download the state_of_the_union.txt here: https://raw.githubusercontent.com/hwchase17/langchain/master/docs/modules/state_of_the_union.txt
# This example requires: pip install chromadb

# Load Your Documents
from langchain.document_loaders import TextLoader


loader = TextLoader("./examples/logging/state_of_the_union.txt")

# Create Your Index
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.indexes import VectorstoreIndexCreator
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma


index = VectorstoreIndexCreator(
    vectorstore_cls=Chroma,
    embedding=OpenAIEmbeddings(),
    text_splitter=CharacterTextSplitter(chunk_size=1000, chunk_overlap=0),
).from_loaders([loader])

# Query Your Index
query = "What did the president say about Ketanji Brown Jackson"
print(index.query_with_sources(query, llm=ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")))
