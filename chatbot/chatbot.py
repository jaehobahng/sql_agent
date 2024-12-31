import streamlit as st
from collections import Counter
from langchain_core.messages import AIMessage, HumanMessage
import json
import uuid

# Config for icons
USER_ICON = "./images/traveller.png"  # Replace with the path to your user icon
ASSISTANT_ICON = "./images/guide.png"

from lang_model import chatbot
model = chatbot()
thread_id = uuid.uuid4()
config = {"configurable": {"thread_id": thread_id}}

# Page Config
st.set_page_config(layout="wide", page_title="Sequel Agent")

# Sidebar
st.sidebar.title("Natural Language to Sequel Agent")
st.sidebar.write(
    """
    This chatbot provides a user-friendly interface that transforms natural language inputs into SQL queries, seamlessly interacting with three data tables: **purchase data**, **product data**, and **click data**. \n\n
    On the left side of the interface, you can view the generated SQL query, while the right side displays the natural language input alongside the chatbot's response. This ensures a clear and intuitive experience for crafting and understanding database queries.
    
    """)

st.title("Sequel Agent")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state["messages"] = [AIMessage(content="How can I help you?")]

if "analysis" not in st.session_state:
    st.session_state["analysis"] = []

# Layout
col1, col2 = st.columns([1, 1])

# Right Side: Chat Interface
with col2:
    st.header("Chat")
    # Display previous messages

    for msg in st.session_state["messages"]:
        if isinstance(msg, AIMessage):
            # Render assistant messages with custom icon
            with st.chat_message("assistant", avatar=ASSISTANT_ICON):
                st.write(msg.content)
        elif isinstance(msg, HumanMessage):
            # Render user messages with custom icon
            with st.chat_message("user", avatar = USER_ICON):
                st.write(msg.content)

if prompt := st.chat_input():

    st.session_state.messages.append(HumanMessage(content=prompt))

    with st.chat_message("user", avatar=USER_ICON):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=ASSISTANT_ICON):
        # assistant_message = st.chat_message('assistant')
        message_placeholder = st.markdown("Loading your analysis...!")
        current_response = ""
        
        messages = model.invoke({"messages": [("user", prompt)], "chat_history": []}, config=config)
        print(messages)
        

        try:
            response = messages["messages"][-1].tool_calls[0]["args"]["final_answer"]
            query = []

            for i, item in enumerate(messages["messages"]):
                try:
                    tool_name = item.additional_kwargs["tool_calls"][0]["function"]["name"]
                    if tool_name == "db_query_tool":
                        a = item.additional_kwargs['tool_calls'][0]['function']['arguments']
                        actual_dict = json.loads(a)
                        query.append(actual_dict['query'])
                        output_query = query[-1].replace("\n", " \n")
                        # final = response + "\n\n" + output_query
                        st.session_state["analysis"].append(
                            {"query" : output_query,
                             "input" : prompt,
                             "output": response
                             })
                        print(output_query)
                        # print(query[-1])
            
                except:
                    pass
        
        except:
            response = "I'm sorry, I couldn't understand that. Please try again."
            query = ''


        message_placeholder.markdown(response)
        assistant_message = AIMessage(content=response)
        st.session_state["messages"].append(assistant_message)

# Left Side: Analysis Output
# with col1:
#     st.header("Output")
#     st.subheader("Sequel Query")
#     if st.session_state["analysis"]:
#         st.markdown(f"```sql\n{st.session_state['analysis'][-1]}\n```")
        
#         # # Combine all messages into one text for analysis
#         # all_text = " ".join([msg["content"] for msg in st.session_state["messages"]])
#         # word_counts = Counter(all_text.split())
#         # st.session_state["analysis"] = dict(word_counts.most_common(10))
#     else:
#         st.markdown("No data to analyze yet.")
    
    
with col1:
    st.header("Output")
    st.subheader("Matching Prompts and Queries")

    # Display past prompts and queries
    if st.session_state["analysis"]:
        st.write("Past Matching Prompts and Queries:")
        for analysis in st.session_state["analysis"]:
            st.markdown(f"**Prompt:** {analysis['input']}")
            st.markdown(f"```sql\n{analysis['query']}\n```")
            st.markdown(f"**Output:** {analysis['output']}")
    else:
        st.markdown("No data to analyze yet.")