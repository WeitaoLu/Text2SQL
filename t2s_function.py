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

from langchain.agents import create_sql_agent
from langchain.agents.agent_types import AgentType
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.llms.openai import OpenAI

def read_api_key(file_path):
    '''read the api key from the file
    :param file_path: the path of the file
    '''
    with open(file_path, 'r') as file:
        return file.read().strip()

def model_select(model_name):
    if model_name == "llama2_chat":
        return ChatOllama(model="llama2:13b-chat")
    elif model_name == "llama2_code":
        return ChatOllama(model="codellama:7b-instruct")
    elif model_name == "gpt4":
        return ChatOpenAI(model='gpt-4-0613')
    elif model_name == "gpt3":
        return ChatOpenAI(model='gpt-3.5-turbo-1106')
    else:
        return ChatOpenAI(model='gpt-3.5-turbo-1106')

def init(model_name,db_name):
    model = model_select(model_name)
    REPLICATE_API_TOKE = read_api_key('../API_Key/REPLICATE_API_TOKEN.txt')
    OPENAI_API_KEY = read_api_key('../API_Key/OPENAI_API_KEY.txt')

    #set the environment variable
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKE
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    # Replicate API
    replicate_id = "meta/llama-2-13b-chat:f4e2de70d66816a838a89eeeb621910adffb0dd0baba3976c96980970978018d"
    llama2_chat_replicate = Replicate(
    model=replicate_id, model_kwargs={"temperature": 0.01, "max_length": 500, "top_p": 1}
    )
    # Database

    db = SQLDatabase.from_uri(f"sqlite:///./{db_name}.db", sample_rows_in_table_info=0)
    return model,db
def text2sql_end2end(model_name,db_name,question):
    model,db = init(model_name,db_name)
    # Prompts
    # 
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
    return full_chain.invoke({"question": question})

def sql_agent(question):
    db = SQLDatabase.from_uri("sqlite:///./Chinook.db")
    toolkit = SQLDatabaseToolkit(db=db, llm=ChatOpenAI(model='gpt-3.5-turbo-1106',temperature=0))
    agent_executor = create_sql_agent(
    llm=ChatOpenAI(model='gpt-3.5-turbo-1106',temperature=0),
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
)
    agent_executor.run(
    question
)
# sample to execute the model 
question = "What are the top 3 best-selling artists from the database?"
# print(sql_agent(question))
print(text2sql("gpt3","Chinook",question))