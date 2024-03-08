#openai_utils_send_message.py
from openai import OpenAI
import time
import sys
import os
# Get the directory of the current script
current_script_path = os.path.dirname(os.path.abspath(__file__))
# Set the path to the parent directory (one folder up)
parent_directory = os.path.dirname(current_script_path)
# Add the config directory to sys.path
sys.path.append(os.path.join(parent_directory, 'database'))
sys.path.append(os.path.join(parent_directory, 'config'))
from config import Config

OPENAI_API_KEY = Config.OPENAI_API_KEY

# Initialize OpenAI client
openai_client = OpenAI()
openai_client.api_key = Config.OPENAI_API_KEY

#send the message    
async def send_message(thread_id_n, message):
    try:
        response = openai_client.beta.threads.messages.create(
            thread_id_n,
            role="user",
            content=message
        )
        # Extracting the response text from the nested structure
        response_text = response.content[0].text.value
        
       
        return response_text
    except Exception as e:
        print(f"Error in sending message: {e}")
        return "Error in sending message."
