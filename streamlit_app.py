import streamlit as st
import requests
import json
import re

# Show title and description
st.title("💬 DeepSeek Chatbot")
st.write(
    "This is a simple chatbot that uses DeepSeek's language model to generate responses. "
    "The conversation is limited to 20 messages (10 exchanges), with each response limited to 300 words."
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

# Helper function to count words
def count_words(text):
    return len(re.findall(r'\b\w+\b', text))

# Helper function to truncate to 300 words
def truncate_to_word_limit(text, limit=300):
    words = re.findall(r'\b\w+\b|\S', text)
    if len(words) <= limit:
        return text
    
    # Truncate to word limit
    truncated_text = " ".join(words[:limit])
    # Add ellipsis to indicate truncation
    return truncated_text + "..."

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
        # Truncate user input if over 300 words
        truncated_prompt = truncate_to_word_limit(prompt)
        if truncated_prompt != prompt:
            st.info("Your message was truncated to 300 words.")
            
        # Store and display the truncated prompt
        st.session_state.messages.append({"role": "user", "content": truncated_prompt})
        with st.chat_message("user"):
            st.markdown(truncated_prompt)
        
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
            
            # Set up the API request data with max tokens limit to help ensure response is not too long
            data = {
                "model": "deepseek-chat",  # Replace with the appropriate DeepSeek model
                "messages": api_messages,
                "max_tokens": 500,  # Approximate limit to help stay under 300 words
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
                                # Skip the "data: " prefix and empty lines
                                if line_text.startswith("data: ") and line_text != "data: [DONE]":
                                    json_str = line_text[6:]  # Remove "data: " prefix
                                    try:
                                        chunk = json.loads(json_str)
                                        if "choices" in chunk and len(chunk["choices"]) > 0:
                                            content = chunk["choices"][0].get("delta", {}).get("content", "")
                                            if content:
                                                full_response += content
                                                # Display maximum 300 words as we go
                                                display_response = truncate_to_word_limit(full_response)
                                                message_placeholder.markdown(display_response + "▌")
                                    except json.JSONDecodeError:
                                        continue
                        
                        # Truncate the final response if it's over the limit
                        final_response = truncate_to_word_limit(full_response)
                        if final_response != full_response:
                            st.info("The assistant's response was truncated to 300 words.")
                        
                        # Update the placeholder with the final response
                        message_placeholder.markdown(final_response)
                        
                        # Store the truncated response
                        st.session_state.messages.append({"role": "assistant", "content": final_response})
            except Exception as e:
                st.error(f"Error connecting to DeepSeek API: {str(e)}")
                error_message = "Sorry, I encountered an error trying to generate a response."
                message_placeholder.markdown(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
else:
    # Show a message when the chat is full
    st.info("This conversation has reached its message limit. Please reset to continue chatting.")
    if st.button("Reset Conversation"):
        st.session_state.messages = []
        st.experimental_rerun()
