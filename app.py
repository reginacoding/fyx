import streamlit as st
import time
from openai import OpenAI
from groq import Groq
from pymongo.server_api import ServerApi
from pymongo import MongoClient, IndexModel, ASCENDING
from datetime import datetime, timedelta

def setup_mongodb():
    uri = st.secrets["mongoURI"]
    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))
    # Send a ping to confirm a successful connection
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)

    db = client.fyx
    collection = db.message_history

    # Create a TTL index for automatic deletion of documents after 30 days (2592000 seconds)
    ttl_index = IndexModel([("created_at", ASCENDING)], expireAfterSeconds=2592000)
    collection.create_indexes([ttl_index])

    return collection

def save_chat_thread(id, messages):
    # Update the document with the given ID to replace its messages
    update_result = collection.update_one(
        {"_id": id},  # Filter to find the document by ID
        {"$set": {"messages": messages}}  # Update operation to set new messages
    )
    if update_result.matched_count == 0:
        print("No document found with the given ID.")
    else:
        print("Document updated successfully.")

# Set page config
st.set_page_config(page_title="Fyx Content Assistant", page_icon=":memo:", layout="wide")

# Set your OpenAI API key and assistant ID here
api_key = st.secrets["openai_apikey"]
assistant_id = st.secrets["assistant_id"]
groq_key = st.secrets["groq_apikey"]

# Set openAi client, assistant ai and assistant ai thread
@st.cache_resource
def load_openai_client_and_assistant():
    client = OpenAI(api_key=api_key)
    my_assistant = client.beta.assistants.retrieve(assistant_id)
    thread = client.beta.threads.create()


    return client, my_assistant, thread

def load_groq_client():
    client = Groq(
    api_key=groq_key,
    )

    client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are Fyx",
            }
        ],
        model="mixtral-8x7b-32768",
    )

    return client

client, my_assistant, assistant_thread = load_openai_client_and_assistant()
groq_client = load_groq_client()
collection = setup_mongodb()

# check in loop if assistant ai parses our request
def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

def get_groq_response(messages):
    history = history_to_assistant_messages(messages)
    chat_completion = groq_client.chat.completions.create(
        messages=history,
        model="mixtral-8x7b-32768",
    )

    return chat_completion.choices[0].message.content

# initiate assistant ai response
def get_assistant_response(user_input=""):
    message = client.beta.threads.messages.create(
        thread_id=assistant_thread.id,
        role="user",
        content=user_input,
    )

    run = client.beta.threads.runs.create(
        thread_id=assistant_thread.id,
        assistant_id=assistant_id,
    )

    run = wait_on_run(run, assistant_thread)

    # Retrieve all the messages added after our last user message
    messages = client.beta.threads.messages.list(
        thread_id=assistant_thread.id, order="asc", after=message.id
    )

    return messages.data[0].content[0].text.value

def get_openai_response(messages):
    history = history_to_assistant_messages(messages)
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=history
    )

    return response.choices[0].message.content

def history_to_assistant_messages(history):
    messages = []
    for message in history:
        if message.startswith("You: "):
            messages.append({"role": "user", "content": message[5:]})
        elif message.startswith("Assistant: "):
            messages.append({"role": "assistant", "content": message[10:]})
    return messages

def display_thread(thread, chat_display):
    # Clear previous messages
    chat_display.empty()
    # Display each message in the thread
    for message in thread['messages']:
        chat_display.markdown(f"<div style='background-color: #262730; padding: 10px; border-radius: 10px; margin: 10px 0;'>{message}</div>", unsafe_allow_html=True)
    

def main():
    _, title = st.columns([1,4])
    with title:
        st.title("Welcome to Fyx")
        st.markdown("A team of digital humans at your service")

    _, col1, col2, col3, _ = st.columns(5)

    with col1:
        st.image("public/jamie.png", width=150)
        st.markdown("**Jamie, the Content Creator**")
        st.markdown("Need a rough draft to get started? I'll cover the main points and translate your ideas into words.")

    with col2:
        st.image("public/michael.png", width=150)
        st.markdown("**Michael, the Editor**")
        st.markdown("Let me polish your draft. I'll ensure it's clear, engaging, and perfectly matches our brand voice.")

    with col3:
        st.image("public/emma.png", width=150)
        st.markdown("**Emma, the Design Consultant**")
        st.markdown("Ready to add a visual? I'll write a prompt that complements your draft and includes all the right brand colors and style.")

    st.markdown("---") 

    history_display, chat_display = st.columns([1,6])
    with chat_display:
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []

        st.header('Chat')
        chat_display = st.container()
        # for message in st.session_state.chat_history:
        #         chat_display.markdown(f"<div style='background-color: #262730; padding: 10px; border-radius: 10px; margin: 10px 0;'>{message}</div>", unsafe_allow_html=True)

        if 'reset_input' not in st.session_state:
            st.session_state['reset_input'] = False
        
        if st.session_state.reset_input == True:
            st.session_state['query'] = ""
            st.session_state.reset_input = False

        st.text_area("Fyx yourself a Linkedin post, a blog or whatever you like", value="", key='query')

        # Initialize or reset the button click state
        if 'run_button' in st.session_state and st.session_state.run_button == True:
            st.session_state.running = True
        else:
            st.session_state.running = False

        if 'output' not in st.session_state:
            st.session_state.output = ""

        col_1, col_2, col_3 = st.columns([5,1,1])

        with col_1:

            # Button to submit input
            if st.button("Send", disabled=st.session_state.running, key='run_button'):
                if st.session_state.query:
                    st.session_state.chat_history.append(f"You: {st.session_state.query}")
                    #result = get_assistant_response(st.session_state.query)
                    if st.session_state.model_selector == "ChatGPT":
                        result = get_openai_response(st.session_state.chat_history)
                    else:
                        result = get_groq_response(st.session_state.chat_history)
                    # Display the response
                    st.session_state.chat_history.append(f"Assistant: {result}")
                    st.session_state.reset_input = True

                    #save to db
                    if st.session_state.chat_history:
                        save_chat_thread(st.session_state.selected_thread_id, st.session_state.chat_history)


                    st.rerun()
        with col_2:
            st.button("Delete Chat")

        with col_3:
            if 'model_selector' not in st.session_state:
                st.session_state.model_selector = "ChatGPT"

            if 'selectbox_option' not in st.session_state:
                st.session_state.selectbox_option = 0

            # Dropdown for selecting the model
            model_choice = st.selectbox("select assistant",
                        ["ChatGPT", "Groq"], 
                        key='model_selector', 
                        index=st.session_state.selectbox_option,
                        label_visibility="collapsed")
            
            st.session_state.selectbox_option = ["ChatGPT", "Groq"].index(model_choice)
    
    with history_display:
        st.text('History')
        st.button("+ New Chat")
        all_threads = collection.find({})
        # Create a list of descriptions for the selectbox
        for thread in all_threads:
            thread_description = f"Thread from {thread['created_at'].strftime('%Y-%m-%d %H:%M:%S')}" 
            if st.button(thread_description):
                display_thread(thread, chat_display)
                st.session_state.chat_history = thread['messages']
                # Store selected thread in session state
                if 'selected_thread_id' not in st.session_state or st.session_state.selected_thread_id != thread['_id']:
                    st.session_state.selected_thread_id = thread['_id']
                    
                
                

        


if __name__ == "__main__":
    main()