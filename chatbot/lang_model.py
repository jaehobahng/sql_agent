import getpass
import os
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv


load_dotenv('.env')
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "your_database_name")
DB_USER = os.getenv("DB_USER", "your_username")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")

engine = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

db = SQLDatabase.from_uri(engine)




from typing import Any

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda, RunnableWithFallbacks
from langgraph.prebuilt import ToolNode


def create_tool_node_with_fallback(tools: list) -> RunnableWithFallbacks[Any, dict]:
    """
    Create a ToolNode with a fallback to handle errors and surface them to the agent.
    """
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )


def handle_tool_error(state) -> dict:
    error = state.get("error")  # Get the error message of current state
    tool_calls = state["messages"][-1].tool_calls # Get the tool calls of the last message
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }


from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI

toolkit = SQLDatabaseToolkit(db=db, llm=ChatOpenAI(model="gpt-4o"))
tools = toolkit.get_tools()

list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")


# print(list_tables_tool.invoke(""))
# print(get_schema_tool.invoke("purchase_data"))


from langchain_core.tools import tool


@tool
def db_query_tool(query: str) -> str:
    """
    Execute a SQL query against the database and get back the result.
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    """
    result = db.run_no_throw(query)
    if not result:
        return "Error: Query failed. Please rewrite your query and try again."
    return result


# print(db_query_tool.invoke("SELECT * FROM purchase_data LIMIT 10;"))





from typing import Annotated, Literal

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import AnyMessage, add_messages


# Define the state for the agent
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]



# Add a node for the first tool call
def first_tool_call(state: State) -> dict[str, list[AIMessage]]:
    return {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "sql_db_list_tables",
                        "args": {},
                        "id": "tool_abcd123",
                    }
                ],
            )
        ]
    }

# Add a node for a model to choose the relevant tables based on the question and available tables
model_get_schema = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
    [get_schema_tool]
)




# Describe a tool to represent the end state
class SubmitFinalAnswer(BaseModel):
    """Submit the final answer to the user based on the query results."""

    final_answer: str = Field(..., description="The final answer to the user")








# Query check function
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

query_check_system = """You are a SQL expert with a strong attention to detail.
Double check the postgres query for common mistakes, including:
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins

If there are any of the above mistakes, rewrite the query. If there are no mistakes, just reproduce the original query.

You will call the appropriate tool to execute the query after running this check."""

query_check_prompt = ChatPromptTemplate.from_messages(
    [("system", query_check_system), ("placeholder", "{messages}")]
)


from langchain_core.tools import tool


@tool
def db_query_tool(query: str) -> str:
    """
    Execute a SQL query against the database and get back the result.
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    """
    result = db.run_no_throw(query)
    if not result:
        return "Error: Query failed. Please rewrite your query and try again."
    return result


# print(db_query_tool.invoke("SELECT * FROM purchase_data LIMIT 10;"))


query_check = query_check_prompt | ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
    [db_query_tool], tool_choice="required"
)

# invoke_check = query_check.invoke({"messages": [("user", "SELECT * FROM purchase_data LIMIT 10;")]})

def model_check_query(state: State) -> dict[str, list[AIMessage]]:
    """
    Use this tool to double-check if your query is correct before executing it.
    """
    return {"messages": [query_check.invoke({"messages": [state["messages"][-1]]})]}




# Add a node for a model to generate a query based on the question and schema
query_gen_system = """You are a SQL expert with a strong attention to detail.

Given an input question, output a syntactically correct postgres query to run, then look at the results of the query and return the answer.
If the user's input is not asking for data, do not generate a query, SubmitFinalAnswer and ask for clarification.

DO NOT call any tool besides SubmitFinalAnswer to submit the final answer.

When generating the query:

Output the SQL query that answers the input question without a tool call.

Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.

If you get an error while executing a query, rewrite the query and try again.

NEVER make stuff up if you don't have enough information to answer the query... just say you don't have enough information.

If you have enough information to answer the input question, simply invoke the appropriate tool to submit the final answer to the user.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database."""
query_gen_prompt = ChatPromptTemplate.from_messages(
    [("system", query_gen_system), ("placeholder", "{messages}")]
)

query_gen = query_gen_prompt | ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
    [SubmitFinalAnswer, model_check_query]
)


def query_gen_node(state: State):
    """
    1. Invoke whatever state the workflow is in now.
    2. If tool_calls is not empty, and the tool is not submit final answer, return an error message.
    3. If tool_calls is empty return a blank tool message
    4. return invoked state + tool message

    This LLM generates a SQL query due to system prompt and then either check/runs the query or submits the final answer.
    """
    message = query_gen.invoke(state)

    # Sometimes, the LLM will hallucinate and call the wrong tool. We need to catch this and return an error message.
    tool_messages = []
    if message.tool_calls:
        for tc in message.tool_calls:
            if tc["name"] != "SubmitFinalAnswer":
                tool_messages.append(
                    ToolMessage(
                        content=f"Error: The wrong tool was called: {tc['name']}. Please fix your mistakes. Remember to only call SubmitFinalAnswer to submit the final answer. Generated queries should be outputted WITHOUT a tool call.",
                        tool_call_id=tc["id"],
                    )
                )
    else:
        tool_messages = []
    return {"messages": [message] + tool_messages}



# Define a conditional edge to decide whether to continue or end the workflow
def should_continue(state: State) -> Literal[END, "correct_query", "query_gen"]:
    messages = state["messages"]
    last_message = messages[-1]
    # If there is a tool call, then we finish
    if getattr(last_message, "tool_calls", None):
        return END
    if last_message.content.startswith("Error:"):
        return "query_gen"
    else:
        return "correct_query"







# Add a node for a model to generate a query based on the question and schema
oracle_system = """
You are the oracle, the great AI decision maker.
If the user prompt is asking for data, use the list_tables_tool.

DO NOT call any tool besides SubmitFinalAnswer to submit the final answer.
Answer based on chat history as well.
Use only one tool.

"""
oracle_prompt = ChatPromptTemplate.from_messages([
    ("system", query_gen_system), 
    ("placeholder", "{messages}"),
    # MessagesPlaceholder(variable_name="chat_history"),
])

oracle_bind = oracle_prompt | ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
    [list_tables_tool, SubmitFinalAnswer], tool_choice="required"
)

def run_oracle(state: State):
    message = oracle_bind.invoke(state)

    return {"messages": [message]}


# Define a conditional edge to decide whether to continue or end the workflow
def query_or_conv(state: State) -> Literal[END, "list_tables_tool"]:
    
    messages = state["messages"]
    # print(state)
    tool = messages[-1].additional_kwargs['tool_calls'][0]['function']['name']
    # print(tool)
    # If there is a tool call, then we finish
    if tool == 'SubmitFinalAnswer':
        return END
    elif tool == 'sql_db_list_tables':
        return "list_tables_tool"
    else:
        return "run_oracle"
    
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()


def chatbot():

    workflow = StateGraph(State)
    workflow.add_node("oracle", run_oracle)
    # workflow.add_node("final_answer", final_answer)
    # workflow.add_node("first_tool_call", first_tool_call)
    workflow.add_node("list_tables_tool", create_tool_node_with_fallback([list_tables_tool]))
    workflow.add_node("model_get_schema", lambda state: {"messages": [model_get_schema.invoke(state["messages"])],},)
    workflow.add_node("get_schema_tool", create_tool_node_with_fallback([get_schema_tool]))
    workflow.add_node("query_gen", query_gen_node)
    workflow.add_node("correct_query", model_check_query)
    workflow.add_node("execute_query", create_tool_node_with_fallback([db_query_tool]))



    # Specify the edges between the nodes
    # workflow.add_edge(START, "first_tool_call")
    workflow.set_entry_point("oracle")

    workflow.add_conditional_edges("oracle",query_or_conv)

    # workflow.add_edge("oracle", "list_tables_tool")
    workflow.add_edge("list_tables_tool", "model_get_schema")
    workflow.add_edge("model_get_schema", "get_schema_tool")
    workflow.add_edge("get_schema_tool", "query_gen")

    workflow.add_conditional_edges(
        "query_gen",
        should_continue, # query_gen, correct_querry, END
    )
    workflow.add_edge("correct_query", "execute_query")
    workflow.add_edge("execute_query", "query_gen")

    # Compile the workflow into a runnable
    app = workflow.compile(checkpointer=memory)

    return app