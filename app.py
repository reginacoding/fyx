import streamlit as st
import time
from openai import OpenAI

# Set page config
st.set_page_config(page_title="Fyx Content Assistant", page_icon=":memo:")

# Set your OpenAI API key and assistant ID here
api_key = st.secrets["openai_apikey"]
assistant_id = st.secrets["assistant_id"]

# Set openAi client, assistant ai and assistant ai thread
@st.cache_resource
def load_openai_client_and_assistant():
    client = OpenAI(api_key=api_key)
    my_assistant = client.beta.assistants.retrieve(assistant_id)
    thread = client.beta.threads.create()

    return client, my_assistant, thread

client, my_assistant, assistant_thread = load_openai_client_and_assistant()

# check in loop if assistant ai parses our request
def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

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

def main():
    st.title("Welcome to Fyx")
    st.markdown("A team of digital humans at your service")

    col1, col2, col3 = st.columns(3)

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

    user_input = st.text_area("Fyx yourself a Linkedin post, a blog or whatever you like", key='query')

    if st.button("Send"):
        if user_input:
            result = get_assistant_response(user_input)
            st.header('Assistant:')
            st.write(result)

if __name__ == "__main__":
    main()