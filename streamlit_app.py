import streamlit as st
import requests
import json

# Show title and description
st.title("💬 DeepSeek Chatbot")
st.write(
    "This is a simple chatbot that uses DeepSeek's language model to generate responses. "
    "The conversation is limited to 20 messages (10 exchanges)."
)

# Get API key from Streamlit secrets
# Make sure to add your DeepSeek API key to the .streamlit/secrets.toml file:
# deepseek_api_key = "your-api-key-here"
api_key = st.secrets["deepseek_api_key"]
api_url = "https://api.deepseek.com/v1/chat/completions"

# Set up headers for API request
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

# Create a session state variable to store the chat messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display message count and limit warning if approaching limit
message_count = len(st.session_state.messages)
exchanges_left = (20 - message_count) // 2
if exchanges_left <= 3 and exchanges_left > 0:
    st.warning(f"You have {exchanges_left} exchanges left in this conversation.")
elif message_count >= 20:
    st.error("You've reached the maximum of 20 messages in this conversation.")
    # Add a reset button
    if st.button("Reset Conversation"):
        st.session_state.messages = []
        st.experimental_rerun()

# Display the existing chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Create a chat input field - only if under the message limit
if message_count < 20:
    if prompt := st.chat_input("What is up?"):
        # Store and display the current prompt
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Prepare messages for the API request
        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ]
        
        # For streaming response
        with st.chat_message("assistant"):
            # Create a placeholder for the streamed response
            message_placeholder = st.empty()
            full_response = ""
            
            # Set up the API request data
            data = {
                "model": "deepseek-chat",  # Replace with the appropriate DeepSeek model
                "messages": api_messages,
                "stream": True
            }
            
            # Make the API request with streaming
            try:
                with requests.post(api_url, headers=headers, json=data, stream=True) as r:
                    if r.status_code != 200:
                        st.error(f"Error: {r.status_code} - {r.text}")
                    else:
                        # Process the streaming response
                        for line in r.iter_lines():
                            if line:
                                line_text = line.decode('utf-8')
