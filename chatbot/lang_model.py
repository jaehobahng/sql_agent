# import getpass
# import os
# from langchain_community.utilities import SQLDatabase
# from dotenv import load_dotenv


# load_dotenv('.env')
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


# # Database connection details
# DB_HOST = os.getenv("DB_HOST", "localhost")
# DB_PORT = os.getenv("DB_PORT", "5432")
# DB_NAME = os.getenv("DB_NAME", "your_database_name")
# DB_USER = os.getenv("DB_USER", "your_username")
# DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")

# engine = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# db = SQLDatabase.from_uri(engine)


# from langchain_community.agent_toolkits import SQLDatabaseToolkit
# from langchain_openai import ChatOpenAI

# toolkit = SQLDatabaseToolkit(db=db, llm=ChatOpenAI(model="gpt-4o"))
# tools = toolkit.get_tools()

# list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
# get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")

# from typing import Any

# from langchain_core.messages import ToolMessage
# from langchain_core.runnables import RunnableLambda, RunnableWithFallbacks
# from langgraph.prebuilt import ToolNode


# def create_tool_node_with_fallback(tools: list) -> RunnableWithFallbacks[Any, dict]:
#     """
#     Create a ToolNode with a fallback to handle errors and surface them to the agent.
#     """
#     return ToolNode(tools).with_fallbacks(
#         [RunnableLambda(handle_tool_error)], exception_key="error"
#     )


# def handle_tool_error(state) -> dict:
#     print(state)
#     error = state.get("error")  # Get the error message of current state
#     tool_calls = state["messages"][-1].tool_calls # Get the tool calls of the last message
#     return {
#         "messages": [
#             ToolMessage(
#                 content=f"Error: {repr(error)}\n please fix your mistakes.",
#                 tool_call_id=tc["id"],
#             )
#             for tc in tool_calls
#         ]
#     }


# from typing import Annotated, Literal

# from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
# from langchain_openai import ChatOpenAI

# from pydantic import BaseModel, Field
# from typing_extensions import TypedDict

# from langgraph.graph import END, StateGraph, START
# from langgraph.graph.message import AnyMessage, add_messages


# # Define the state for the agent
# class State(TypedDict):
#     messages: Annotated[list[AnyMessage], add_messages]


# # Define a new graph



# # Add a node for the first tool call
# def first_tool_call(state: State) -> dict[str, list[AIMessage]]:
#     return {
#         "messages": [
#             AIMessage(
#                 content="",
#                 tool_calls=[
#                     {
#                         "name": "sql_db_list_tables",
#                         "args": {},
#                         "id": "tool_abcd123",
#                     }
#                 ],
#             )
#         ]
#     }


# # Add a node for a model to choose the relevant tables based on the question and available tables
# model_get_schema = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
#     [get_schema_tool]
# )


# from langchain_core.tools import tool

# # Describe a tool to represent the end state
# # class SubmitFinalAnswer(BaseModel):
# #     """Submit the final answer to the user based on the query results."""

# #     final_answer: str = Field(..., description="The final answer to the user")


# @tool
# def SubmitFinalAnswer(final_answer: str) -> str:
#     """Submit the final answer to the user based on the query results."""
#     # final_answer: str = Field(..., description="The final answer to the user")
#     if not final_answer:
#         raise ValueError("final_answer cannot be empty")
#     return final_answer








# # Query check function
# from langchain_core.prompts import ChatPromptTemplate

# query_check_system = """You are a SQL expert with a strong attention to detail.
# Double check the postgres query for common mistakes, including:
# - Using NOT IN with NULL values
# - Using UNION when UNION ALL should have been used
# - Using BETWEEN for exclusive ranges
# - Data type mismatch in predicates
# - Properly quoting identifiers
# - Using the correct number of arguments for functions
# - Casting to the correct data type
# - Using the proper columns for joins

# If there are any of the above mistakes, rewrite the query. If there are no mistakes, just reproduce the original query.

# You will call the appropriate tool to execute the query after running this check."""

# query_check_prompt = ChatPromptTemplate.from_messages(
#     [("system", query_check_system), ("placeholder", "{messages}")]
# )


# from langchain_core.tools import tool


# @tool
# def db_query_tool(query: str) -> str:
#     """
#     Execute a SQL query against the database and get back the result.
#     If the query is not correct, an error message will be returned.
#     If an error is returned, rewrite the query, check the query, and try again.
#     """
#     result = db.run_no_throw(query)
#     if not result:
#         return "Error: Query failed. Please rewrite your query and try again."
#     return result


# # print(db_query_tool.invoke("SELECT * FROM purchase_data LIMIT 10;"))


# query_check = query_check_prompt | ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
#     [db_query_tool], tool_choice="required"
# )

# # invoke_check = query_check.invoke({"messages": [("user", "SELECT * FROM purchase_data LIMIT 10;")]})


# def model_check_query(state: State) -> dict[str, list[AIMessage]]:
#     """
#     Use this tool to double-check if your query is correct before executing it.
#     """
#     return {"messages": [query_check.invoke({"messages": [state["messages"][-1]]})]}








# # Add a node for a model to generate a query based on the question and schema
# query_gen_system = """You are a SQL expert with a strong attention to detail.

# Given an input question, output a syntactically correct postgres query to run, then look at the results of the query and return the answer.

# DO NOT call any tool besides SubmitFinalAnswer to submit the final answer.

# When generating the query:

# Output the SQL query that answers the input question without a tool call.

# Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results.
# You can order the results by a relevant column to return the most interesting examples in the database.
# Never query for all the columns from a specific table, only ask for the relevant columns given the question.

# If you get an error while executing a query, rewrite the query and try again.

# If you get an empty result set, you should try to rewrite the query to get a non-empty result set. 
# NEVER make stuff up if you don't have enough information to answer the query... just say you don't have enough information.

# If you have enough information to answer the input question, simply invoke the appropriate tool to submit the final answer to the user.

# DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database."""


# query_gen_system = """
# You are a SQL expert with a strong attention to detail.

# Given the HumanMessage content, output a syntactically correct postgres query to run, then look at the results of the query and return the answer.

# You must generate a query for each Human Input.

# When generating the query:
# Output the SQL query that answers the input question without a tool call.

# DO NOT call any tool besides SubmitFinalAnswer or create sequel output to submit the final answer.

# Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results.
# You can order the results by a relevant column to return the most interesting examples in the database.
# Never query for all the columns from a specific table, only ask for the relevant columns given the question.

# If you get an error while executing a query, rewrite the query and try again.

# NEVER make stuff up if you don't have enough information to answer the query... just say you don't have enough information.

# If you have enough information to answer the input question, simply invoke the appropriate tool to submit the final answer to the user.

# DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
# """

# query_gen_prompt = ChatPromptTemplate.from_messages(
#     [("system", query_gen_system), ("placeholder", "{messages}")]
# )

# # query_gen = query_gen_prompt | ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
# #     [SubmitFinalAnswer, model_check_query]
# # )

# query_gen = query_gen_prompt | ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
#     [SubmitFinalAnswer, model_check_query]
# )

# def query_gen_node(state: State):
#     """
#     1. Invoke whatever state the workflow is in now.
#     2. If tool_calls is not empty, and the tool is not submit final answer, return an error message.
#     3. If tool_calls is empty return a blank tool message
#     4. return invoked state + tool message

#     This LLM generates a SQL query due to system prompt and then either check/runs the query or submits the final answer.
#     """
#     message = query_gen.invoke(state)

#     # Sometimes, the LLM will hallucinate and call the wrong tool. We need to catch this and return an error message.
#     tool_messages = []
#     if message.tool_calls:
#         for tc in message.tool_calls:
#             if tc["name"] != "SubmitFinalAnswer":
#                 tool_messages.append(
#                     ToolMessage(
#                         content=f"Error: The wrong tool was called: {tc['name']}. Please fix your mistakes. Remember to only call SubmitFinalAnswer to submit the final answer. Generated queries should be outputted WITHOUT a tool call.",
#                         tool_call_id=tc["id"],
#                     )
#                 )
#     else:
#         tool_messages = []
#     return {"messages": [message] + tool_messages}


# # Define a conditional edge to decide whether to continue or end the workflow
# def should_continue(state: State) -> Literal["SubmitFinalAnswer", "correct_query", "query_gen"]:
#     messages = state["messages"]
#     last_message = messages[-1]
#     # If there is a tool call, then we finish
#     if getattr(last_message, "tool_calls", None):
#         return "SubmitFinalAnswer"
#     if last_message.content.startswith("Error:"):
#         return "query_gen"
#     else:
#         return "correct_query"









# # Add a node for a model to generate a query based on the question and schema
# oracle_system = """
# You are the oracle, the great AI decision maker.
# If the user prompt is asking for data, use list_tables_tool.
# if the user is not asking for data, greet accordingly and ask how you can help get the data.
# use only one tool

# """
# oracle_prompt = ChatPromptTemplate.from_messages([
#     ("system", query_gen_system), 
#     ("placeholder", "{messages}"),
# ])


# # Describe a tool to represent the end state
# @tool
# def final_answer(final_answer: str) -> str:
#     """Submit the final answer to the user based on the query results."""
#     # final_answer: str = Field(..., description="The final answer to the user")
#     if not final_answer:
#         raise ValueError("final_answer cannot be empty")
#     return final_answer

# oracle_bind = oracle_prompt | ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
#     [list_tables_tool, final_answer], tool_choice="required"
# )

# def run_oracle(state: State):
#     print(state)
#     message = oracle_bind.invoke(state)
#     return {"messages": [message]}


# # Define a conditional edge to decide whether to continue or end the workflow
# def query_or_conv(state: State) -> Literal['final_answer', "list_tables_tool"]:
#     messages = state["messages"]
#     tool = messages[-1].additional_kwargs['tool_calls'][0]['function']['name']
#     # If there is a tool call, then we finish
#     if tool == 'final_answer':
#         return 'final_answer'
#     elif tool == 'sql_db_list_tables':
#         return "list_tables_tool"
#     else:
#         return "run_oracle"
    
# from langgraph.checkpoint.memory import MemorySaver

# memory = MemorySaver()

# def chatbot():

#     workflow = StateGraph(State)
#     workflow.add_node("oracle", run_oracle)
#     workflow.add_node("final_answer", create_tool_node_with_fallback([final_answer]))
#     # workflow.add_node("first_tool_call", first_tool_call)
#     workflow.add_node("list_tables_tool", create_tool_node_with_fallback([list_tables_tool]))
#     workflow.add_node("model_get_schema", lambda state: {"messages": [model_get_schema.invoke(state["messages"])],},)
#     workflow.add_node("get_schema_tool", create_tool_node_with_fallback([get_schema_tool]))
#     workflow.add_node("query_gen", query_gen_node)
#     workflow.add_node("correct_query", model_check_query)
#     workflow.add_node("SubmitFinalAnswer",  create_tool_node_with_fallback([SubmitFinalAnswer]))
#     workflow.add_node("execute_query", create_tool_node_with_fallback([db_query_tool]))




#     # Specify the edges between the nodes
#     workflow.set_entry_point("oracle")
#     workflow.add_conditional_edges("oracle",query_or_conv)
#     workflow.add_edge("final_answer", END)

#     workflow.add_edge("list_tables_tool", "model_get_schema")
#     workflow.add_edge("model_get_schema", "get_schema_tool")
#     workflow.add_edge("get_schema_tool", "query_gen")

#     workflow.add_conditional_edges(
#         "query_gen",
#         should_continue, # query_gen, correct_querry, END
#     )
#     workflow.add_edge("correct_query", "execute_query")
#     workflow.add_edge("execute_query", "query_gen")
#     # workflow.add_edge("execute_query", "SubmitFinalAnswer")
#     workflow.add_edge("SubmitFinalAnswer", END)
#     # Compile the workflow into a runnable
#     app = workflow.compile(checkpointer=memory)


#     return app

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


from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI

toolkit = SQLDatabaseToolkit(db=db, llm=ChatOpenAI(model="gpt-4o"))
tools = toolkit.get_tools()

list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")

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
    print(state)
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


from typing import Annotated, Literal
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import AnyMessage, add_messages
from langchain_core.tools import tool


# Define the state for the agent
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


# Define a new graph



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
# class SubmitFinalAnswer(BaseModel):
#     """Submit the final answer to the user based on the query results."""

#     final_answer: str = Field(..., description="The final answer to the user")






# Query check function
from langchain_core.prompts import ChatPromptTemplate

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




@tool
def FinalAnswer(final_answer: str) -> str:
    """
    Use this tool when the user asks for an answer to the question and does not ask for a file.
    
    final_answer: The final answer to the user which explains the results of the query
    """
    # final_answer: str = Field(..., description="The final answer to the user")
    if not final_answer:
        raise ValueError("final_answer cannot be empty")
    return final_answer

@tool
def FileOutput(column_names: list, query_output: list, description: str) -> dict:
    """
    Use this tool when the user asks an excel or csv file output.
    You are outputting data with a brief description of the data.

    'description' : A brief summary of the output with a rephrasing of the question that was asked
    'column_names' : List the column names of query that was run to get the results
    'query_output' : The output of the query that was run
    """
    return {'description': description, 'column_names': column_names, 'query_output': query_output}



# Add a node for a model to generate a query based on the question and schema
query_gen_system = """
    You are a SQL expert with a strong attention to detail.
    Given the HumanMessage content, output a syntactically correct postgres query to run, then look at the results of the query and return the answer.

    You must generate a SQL query at least once before using FileOutput or FinalAnswer that answers the input question.
    When outputting a query, do not call any tool. The query should be outputted as a message.

    When generating the query:
    Output the SQL query that answers the input question without a tool call.

    DO NOT call any tool besides SubmitFinalAnswer or create sequel output to submit the final answer.

    Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results.
    You can order the results by a relevant column to return the most interesting examples in the database.
    Never query for all the columns from a specific table, only ask for the relevant columns given the question.

    If you get an error while executing a query, rewrite the query and try again.

    NEVER make stuff up if you don't have enough information to answer the query... just say you don't have enough information.

    If you have enough information to answer the input question, simply invoke the appropriate tool to submit the final answer to the user.

    DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
    """
query_gen_prompt = ChatPromptTemplate.from_messages(
    [("system", query_gen_system), ("placeholder", "{messages}")]
)

# query_gen = query_gen_prompt | ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
#     [SubmitFinalAnswer, model_check_query]
# )

query_gen = query_gen_prompt | ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
    [FileOutput, FinalAnswer, model_check_query]
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

    # # Sometimes, the LLM will hallucinate and call the wrong tool. We need to catch this and return an error message.
    # tool_messages = []
    # if message.tool_calls:
    #     for tc in message.tool_calls:
    #         if tc["name"] != "SubmitFinalAnswer":
    #             tool_messages.append(
    #                 ToolMessage(
    #                     content=f"Error: The wrong tool was called: {tc['name']}. Please fix your mistakes. Remember to only call SubmitFinalAnswer to submit the final answer. Generated queries should be outputted WITHOUT a tool call.",
    #                     tool_call_id=tc["id"],
    #                 )
    #             )
    # else:
    #     tool_messages = []
    return {"messages": [message]}


# Define a conditional edge to decide whether to continue or end the workflow
def should_continue(state: State) -> Literal["FileOutput", "FinalAnswer", "correct_query", "query_gen"]:
    print(state)
    messages = state["messages"]
    last_message = messages[-1]
    # If there is a tool call, then we finish
    # if getattr(last_message, "tool_calls", None):
    #     return "FileOutput"
    if getattr(last_message, "tool_calls") == []:
        return "correct_query"
    if getattr(last_message, "tool_calls"):
        if last_message.tool_calls[0]['name'] == "FinalAnswer":
            return "FinalAnswer"
        elif last_message.tool_calls[0]['name'] == "FileOutput":
            return "FileOutput"
    if last_message.content.startswith("Error:"):
        return "query_gen"



def chatbot():

    workflow = StateGraph(State)
    workflow.add_node("first_tool_call", first_tool_call)
    workflow.add_node("list_tables_tool", create_tool_node_with_fallback([list_tables_tool]))
    workflow.add_node("model_get_schema", lambda state: {"messages": [model_get_schema.invoke(state["messages"])],},)
    workflow.add_node("get_schema_tool", create_tool_node_with_fallback([get_schema_tool]))
    workflow.add_node("query_gen", query_gen_node)
    workflow.add_node("correct_query", model_check_query)
    workflow.add_node("FileOutput",  create_tool_node_with_fallback([FileOutput]))
    workflow.add_node("FinalAnswer",  create_tool_node_with_fallback([FinalAnswer]))
    workflow.add_node("execute_query", create_tool_node_with_fallback([db_query_tool]))

    # Specify the edges between the nodes
    workflow.add_edge(START, "first_tool_call")
    workflow.add_edge("first_tool_call", "list_tables_tool")
    workflow.add_edge("list_tables_tool", "model_get_schema")
    workflow.add_edge("model_get_schema", "get_schema_tool")
    workflow.add_edge("get_schema_tool", "query_gen")
    workflow.add_conditional_edges(
        "query_gen",
        should_continue, # query_gen, correct_querry, END
    )
    workflow.add_edge("correct_query", "execute_query")
    workflow.add_edge("execute_query", "query_gen")
    workflow.add_edge("FileOutput", END)
    workflow.add_edge("FinalAnswer", END)
    app = workflow.compile()

    return app