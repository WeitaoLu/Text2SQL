#an API to call the text2sql model
import os
from langchain.chat_models import ChatOllama
from langchain.utilities import SQLDatabase
from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.llms import Replicate
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

def read_api_key(file_path):
    '''read the api key from the file
    :param file_path: the path of the file
    '''
    with open(file_path, 'r') as file:
        return file.read().strip()

REPLICATE_API_TOKE = read_api_key('../API_Key/REPLICATE_API_TOKEN.txt')
OPENAI_API_KEY = read_api_key('../API_Key/OPENAI_API_KEY.txt')

#set the environment variable
os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKE
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Model
llama2_chat = ChatOllama(model="llama2:13b-chat")
llama2_code = ChatOllama(model="codellama:7b-instruct")
gpt4= ChatOpenAI(model='gpt-4-0613')
gpt3 = ChatOpenAI(model='gpt-3.5-turbo-1106')

model=llama2_chat
model=gpt3
# Replicate API

replicate_id = "meta/llama-2-13b-chat:f4e2de70d66816a838a89eeeb621910adffb0dd0baba3976c96980970978018d"
llama2_chat_replicate = Replicate(
    model=replicate_id, model_kwargs={"temperature": 0.01, "max_length": 500, "top_p": 1}
)

# Database

class SQLite_DB:
    def __init__(self, db_path: str):
        self.db = SQLDatabase.from_uri(db_path, sample_rows_in_table_info=0)
    
    def get_schema(self,la):
        return self.db.get_table_info()
    
    def run_query(self,query):
        print("running query", query)
        return self.db.run(query)

# 
db = SQLite_DB("sqlite:///./Chinook.db")
db = SQLDatabase.from_uri("sqlite:///./Chinook.db", sample_rows_in_table_info=0)
def get_schema(_):
    return db.get_table_info()

def run_query(query):
    print("running query\n", query)
    try:
        result = db.run(query)
        if result:
            print("successfully run query")
            return result
        else:
            return "No results found."
    except Exception as e:
        error_message = str(e)
        print("An error occurred!!" + error_message)
        print("1 to exit, 2 to try auto fix using another model,THIS IS NOT FINISHED NOW, I WILL FIX LATER!")#change to input later 
        exit()
        if input == 1:
            return "An error occurred: " + error_message
        else:
            return "An error occurred: " + error_message

# Prompts

## To SQL   
template = """Based on the table schema below, write a SQLite query that would answer the user's question:
{schema}

Question: {question}
SQL Query:"""
prompt = ChatPromptTemplate.from_template(template)

sql_response = (
    RunnablePassthrough.assign(schema=get_schema)
    | prompt
    | model.bind(stop=["\nSQLResult:"])
    | StrOutputParser()
)

## To natural language
template = """Based on the table schema below, question, sql query, and sql response, write a natural language response:
{schema}

Question: {question}
SQL Query: {query}
SQL Response: {response}"""


prompt_response = ChatPromptTemplate.from_template(template)


full_chain = (
    RunnablePassthrough.assign(query=sql_response).assign(
        schema=get_schema,
        response=lambda x: run_query(x["query"]),
    )
    | prompt_response
    | model
)

# execute the model 
print(full_chain.invoke({"question": "What are the top 3 best-selling artists from the database?"}))