import json
import os
import requests
import streamlit as st
from openai import OpenAI, InternalServerError

st.title('🤖ENOVA AI WebUI')

MAX_TURNS = 20
MAX_BOXES = MAX_TURNS * 2

vllm_mode = os.getenv("VLLM_MODE", "openai")
serving_url = os.getenv("SERVING_URL", "http://127.0.0.1:9199")
openai_api_base = serving_url + "/v1"
openai_api_key = "xxx"

client = None
model = None
if vllm_mode == "openai":
    try:
        client = OpenAI(
            api_key=openai_api_key,
            base_url=openai_api_base,
        )
        models = client.models.list()
        model = models.data[0].id

    except InternalServerError as e:
        print("Server not ready. Please wait a moment and refresh the page.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print("Please check the server status and try again.")

system_prompt = st.sidebar.text_area(
    label="System Prompt",
    value="You are a helpful AI assistant who answers questions in short sentences."
)

max_tokens = st.sidebar.slider('max_tokens', 0, 4096, 2048, step=1)
temperature = st.sidebar.slider('temperature', 0.0, 1.0, 0.1, step=0.01)
top_p = st.sidebar.slider('top_p', 0.0, 1.0, 0.5, step=0.01) if vllm_mode == "normal" else None


if 'messages' not in st.session_state:
    st.session_state.messages = []

messages = st.session_state.messages

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

if user_input := st.chat_input(''):

    with st.chat_message('user'):
        st.markdown(user_input)
        messages.append({'role': 'user', 'content': user_input})

    with st.chat_message('assistant') as assistant_message:

        if vllm_mode == "normal":
            placeholder = st.empty()

            response = requests.post(
                url=f"{serving_url}/generate",
                headers={'Content-type': 'application/json; charset=utf-8'},
                data=json.dumps({
                    "prompt": user_input,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                    "temperature": temperature,
                    "stream": True
                }),
                stream=True
            )

            full_content = ''
            for line in response.iter_lines(delimiter=b'\00'):
                line = line.decode(encoding='utf-8')
                if line.strip() == '':
                    continue
                response_json = json.loads(line)
                full_content = response_json['text'][0]
                placeholder.markdown(full_content)

            st.session_state.messages.append({'role': 'assistant', 'content': full_content})

        elif vllm_mode == "openai" and model:
            placeholder = st.empty()
            openai_messages = [
                {"role": message["role"], "content": message["content"]}
                for message in st.session_state.messages[-5:]
            ]

            chat_completion = client.chat.completions.create(
                messages=openai_messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            full_content = ''
            for chunk in chat_completion:
                if chunk.choices[0].delta.content is not None:
                    full_content += str(chunk.choices[0].delta.content)
                    placeholder.markdown(full_content)

            st.session_state.messages.append({'role': 'assistant', 'content': full_content})
