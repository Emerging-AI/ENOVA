import json
import os

import requests
import streamlit as st

st.title("🤖ENOVA AI WebUI")

MAX_TURNS = 20
MAX_BOXES = MAX_TURNS * 2
url = os.environ.get("SERVING_URL", "http://127.0.0.1:8000/generate")

system_prompt = st.sidebar.text_area(
    label="System Prompt", value="You are a helpful AI assistant who answers questions in short sentences."
)

max_tokens = st.sidebar.slider("max_tokens", 0, 4096, 2048, step=1)
top_p = st.sidebar.slider("top_p", 0.0, 1.0, 0.5, step=0.01)
temperature = st.sidebar.slider("temperature", 0.0, 1.0, 0.1, step=0.01)

# save history dialogue in session
if "messages" not in st.session_state:
    st.session_state.messages = []
messages = st.session_state.messages

# render history dialogue
for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input(""):
    with st.chat_message("user"):
        st.markdown(user_input)
        messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant") as assistant_message:
        placeholder = st.empty()
        full_content = ""

        prompt = user_input

        req = {
            "prompt": prompt,
            # "history": history,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "temperature": temperature,
            "stream": True,
        }
        headers = {"Content-type": "application/json; charset=utf-8"}
        res = requests.post(url=url, headers=headers, data=json.dumps(req), stream=True)
        for line in res.iter_lines(delimiter=b"\00"):
            line = line.decode(encoding="utf-8")
            if line.strip() == "":
                continue
            response_json = json.loads(line)
            full_content = response_json["text"][0]
            placeholder.markdown(full_content)

        messages.append({"role": "assistant", "content": full_content})
