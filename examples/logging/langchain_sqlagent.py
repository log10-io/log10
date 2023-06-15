import faker
import sqlalchemy
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import create_sql_agent
from langchain.llms import OpenAI
from faker import Faker
import random
import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, DateTime
import os
from log10.load import log10
import openai

log10(openai)


# Set up a dummy database
fake = Faker()

# Create a SQLite database and connect to it
engine = create_engine('sqlite:///users.db', echo=True)
Base = declarative_base()

# Define the User class with standard fields and the created_at field
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', first_name='{self.first_name}', last_name='{self.last_name}', age={self.age}, created_at={self.created_at})>"

# Helper function to generate a random user using Faker
def generate_random_user():
    username = fake.user_name()
    email = fake.email()
    first_name = fake.first_name()
    last_name = fake.last_name()
    age = random.randint(18, 100)
    return User(username=username, email=email, first_name=first_name, last_name=last_name, age=age)


# Create the 'users' table
Base.metadata.create_all(engine)

# Create a session factory and a session
Session = sessionmaker(bind=engine)
session = Session()

# Add some example users
for n_users in range(10):
    user = generate_random_user()
    session.add(user)

session.commit()

# Query the users and print the results
all_users = session.query(User).all()
print(all_users)

session.close()

# Setup vars for Langchain
openai.api_key = os.getenv("OPENAI_API_KEY")

# Setup Langchain SQL agent
db = SQLDatabase.from_uri("sqlite:///users.db")
toolkit = SQLDatabaseToolkit(db=db)

agent_executor = create_sql_agent(
    llm=OpenAI(temperature=0, model_name="text-davinci-003"),
    toolkit=toolkit,
    verbose=True
)

print(agent_executor.run("Who is the least recent user?"))
