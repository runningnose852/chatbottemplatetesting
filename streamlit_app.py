
import streamlit as st
import requests
import json
import re

# Show title and description
st.title("💬 Paraphrasing Feedback Assistant")
st.write(
    "This chatbot helps with paraphrasing tasks and provides constructive feedback to improve your writing. "
    "The conversation is limited to 20 messages (10 exchanges), with each response limited to 300 words."
)

# Get API key from Streamlit secrets
api_key = st.secrets["deepseek_api_key"]
api_url = "https://api.deepseek.com/v1/chat/completions"

# Set up headers for API request
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

# Helper function to count words
def count_words(text):
    return len(re.findall(r'\b\w+\b', text))

# Helper function to truncate to 300 words
def truncate_to_word_limit(text, limit=300):
    words = re.findall(r'\b\w+\b|\S', text)
    if len(words) <= limit:
        return text
    truncated_text = " ".join(words[:limit])
    return truncated_text + "..."

# Helper function to clean bold/heading markdown
def clean_response(text):
    return re.sub(r"[#*_`]", "", text)

# System message to instruct the model to provide feedback
feedback_system_message = """You are a helpful writing assistant that specializes in providing constructive feedback on paraphrasing tasks.
When reviewing a student's paraphrased text:
1. Assess how well they've maintained the original meaning
2. Evaluate their use of different sentence structures and vocabulary
3. Provide constructive suggestions for improvement but not suggested version
4. Asking one follow-up question that encourages the student to revise their own answer

Be encouraging but honest. Focus on helping the student improve their paraphrasing skills."""

# Initial paraphrasing task message
initial_message = """**Paraphrasing Task:** Please read the paragraph below and rewrite it in your own words. Try to maintain the original meaning, but use different sentence structures and vocabulary.

**Original Paragraph:** In today's fast-paced world, technology plays a crucial role in almost every aspect of our lives. From communication and transportation to healthcare and education, advancements in technology have significantly improved the way we live and work. However, while these innovations offer many benefits, they also raise concerns about privacy, job displacement, and the overreliance on digital tools. It is important for individuals and societies to find a balance between embracing techn...

Submit your paraphrased version below, and I'll provide constructive feedback to help you improve."""

# Create a session state variable to store the chat messages
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": initial_message})
elif len(st.session_state.messages) == 0:
    st.session_state.messages.append({"role": "assistant", "content": initial_message})

# Display message count and limit warning if approaching limit
message_count = len(st.session_state.messages)
exchanges_left = (20 - message_count) // 2
if exchanges_left <= 3 and exchanges_left > 0:
    st.warning(f"You have {exchanges_left} exchanges left in this conversation.")
elif message_count >= 20:
    st.error("You've reached the maximum of 20 messages in this conversation.")
    if st.button("Reset Conversation"):
        st.session_state.messages = []
        st.session_state.messages.append({"role": "assistant", "content": initial_message})
        st.rerun()

# Display the existing chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Create a chat input field - only if under the message limit
if message_count < 20:
    if prompt := st.chat_input("Enter your paraphrased version..."):
        truncated_prompt = truncate_to_word_limit(prompt)
        if truncated_prompt != prompt:
            st.info("Your message was truncated to 300 words.")
        st.session_state.messages.append({"role": "user", "content": truncated_prompt})
        with st.chat_message("user"):
            st.markdown(truncated_prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            api_messages = [{"role": "system", "content": feedback_system_message}] + [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]

            data = {
                "model": "deepseek-chat",
                "messages": api_messages,
                "max_tokens": 1000,
                "temperature": 0.7,
                "stream": True
            }

            try:
                with requests.post(api_url, headers=headers, json=data, stream=True) as r:
                    if r.status_code != 200:
                        st.error(f"Error: {r.status_code} - {r.text}")
                    else:
                        for line in r.iter_lines():
                            if line:
                                line_text = line.decode("utf-8")
                                if line_text.startswith("data: ") and line_text != "data: [DONE]":
                                    json_str = line_text[6:]
                                    try:
                                        chunk = json.loads(json_str)
                                        content = chunk["choices"][0].get("delta", {}).get("content")
                                        if content is not None:
                                            full_response += content
                                            message_placeholder.markdown(clean_response(full_response))
                                    except json.JSONDecodeError:
                                        continue

                message_placeholder.markdown(clean_response(full_response))
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"Error connecting to DeepSeek API: {str(e)}")
                error_message = "Sorry, I encountered an error trying to generate a response."
                message_placeholder.markdown(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

else:
    st.info("This conversation has reached its message limit. Please reset to continue chatting.")
    if st.button("Reset Conversation"):
        st.session_state.messages = []
        st.session_state.messages.append({"role": "assistant", "content": initial_message})
        st.rerun()
