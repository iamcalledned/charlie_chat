import asyncio
import json
import logging
import ssl
from uuid import uuid4
import traceback

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, APIRouter, Request, Depends, status, Body
from starlette.websockets import WebSocket

from openai_utils_generate_answer import generate_answer
from config import Config
from chat_bot_database import (
    create_db_pool, 
    get_user_info_by_session_id, 
    save_recipe_to_db, 
    clear_user_session_id, 
    get_user_id, 
    favorite_recipe, 
    get_recipe_for_printing, 
    get_saved_recipes_for_user, 
    un_favorite_recipe, 
    get_recent_messages, 
    get_messages_before
)
from process_recipe import process_recipe
from get_recipe_card import get_recipe_card

import redis
from redis.exceptions import RedisError

import spacy
import re
from datetime import datetime
import httpx

# Initialize Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Initialize FastAPI app
app = FastAPI()
router = APIRouter()

OPENAI_API_KEY = Config.OPENAI_API_KEY
connections = {}
tasks = {}  # Dictionary to track scheduled tasks for session cleanup

log_file_path = Config.LOG_PATH
LOG_FORMAT = 'WEBSOCKET - %(asctime)s - %(processName)s - %(name)s - %(levelname)s - %(message)s'

logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format=LOG_FORMAT
)

# Async function to create a connection pool
async def create_pool():
    return await create_db_pool()

@router.post("/logout")
async def logout(request: Request):
    session_id = request.json().get('session_id', '')
    if session_id:
        # Remove session data from Redis
        redis_client.delete(session_id)

        # Additional cleanup if necessary
        username = connections.pop(session_id, None)
        if username:
            print(f"User {username} logged out and disconnected.")

    return {"message": "Logged out successfully"}

@app.on_event("startup")
async def startup_event():
    app.state.pool = await create_pool()
    print("Database pool created")
    print("connections at startup:", connections)

# Function to schedule session data cleanup
async def clear_session_data_after_timeout(session_id, username):
    try:
        await asyncio.sleep(3600)  # wait an hour before cleaning
        # Check if the session still exists before clearing
        if redis_client.exists(session_id):
            redis_client.delete(session_id)
            await clear_user_session_id(app.state.pool, session_id)
            print(f"Session data cleared for user {username}")

            # Send a WebSocket message to the client to log out
            if username in connections:
                websocket = connections[username]
                await websocket.send_text(json.dumps({'action': 'force_logout'}))
    except Exception as e:
        print(f"Error in session cleanup task for {username}: {e}")

# Verify session ID function
async def verify_session_id(session_id: str):
    if not session_id or not redis_client.exists(session_id):
        return False
    return True

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    cookies = websocket.cookies
    session_id_from_cookies = cookies.get('session_id')
    print('sessionID from cookies:', session_id_from_cookies)

    # Verify session ID before accepting the WebSocket connection
    if not await verify_session_id(session_id_from_cookies):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    client_host, client_port = websocket.client
    client_ip = client_host
    print(f"Client IP: {client_ip}")
    print("connections at websocket_endpoint:", connections)

    username = None
    session_id = session_id_from_cookies

    async def ping_client():
        while True:
            try:
                await websocket.send_text(json.dumps({'action': 'ping'}))
                await asyncio.sleep(30)  # Send a ping every 30 seconds
            except Exception as e:
                print(f"Error sending ping: {e}")
                break

    ping_task = asyncio.create_task(ping_client())

    try:
        initial_data = await websocket.receive_text()
        initial_data = json.loads(initial_data)
        print('sessionID from cookies:', session_id)

        if session_id:
            session_data = redis_client.get(session_id)
            if session_data:
                session_data = json.loads(session_data)
                username = session_data['username']
                # Renew the session expiry time upon successful connection
                redis_client.expire(session_id, 3600)  # Reset expiry to another hour

                # First, ask the user to select a persona
                await websocket.send_text(json.dumps({
                    'action': 'select_persona'
                }))
                print('sent persona request')

            else:
                await websocket.send_text(json.dumps({'action': 'redirect_login', 'error': 'Session ID required'}))
                await websocket.close(code=1008)
                return

        while True:
            data = await websocket.receive_text()
            data_dict = json.loads(data)
            print('data: ', data_dict)
            message = data_dict.get('message', '')

            # Validate session_id
            if not session_id or not redis_client.exists(session_id):
                await websocket.send_text(json.dumps({'action': 'redirect_login', 'error': 'Invalid or expired session'}))
                await websocket.close(code=1008)
                return

            # Renew the session expiry time
            redis_client.expire(session_id, 3600)

            # Wait for persona selection from the user
            if data_dict.get('action') == 'persona_selected':
                # Now that the persona is selected, you can fetch and send the recent messages
                persona = data_dict.get('persona')
                userID = await get_user_id(app.state.pool, username)
                print('getting recent messages')
                recent_messages = await get_recent_messages(app.state.pool, userID, persona)
                await websocket.send_text(json.dumps({
                    'action': 'recent_messages',
                    'messages': recent_messages
                }))
                continue

            if data_dict.get('action') == 'pong':
                redis_client.expire(session_id, 3600)  # Reset expiry to another hour
                continue

            if 'action' in data_dict and data_dict['action'] == 'save_recipe':
                # Handle the save recipe action
                userID = await get_user_id(app.state.pool, username)
                recipe_id = data_dict.get('content')
                save_result = await favorite_recipe(app.state.pool, userID, recipe_id)

                await websocket.send_text(json.dumps({'action': 'recipe_saved', 'status': save_result}))
                continue

            if 'action' in data_dict and data_dict['action'] == 'get_user_recipes':
                user_id = await get_user_id(app.state.pool, username)
                if user_id:
                    saved_recipes = await get_saved_recipes_for_user(app.state.pool, user_id)
                    await websocket.send_text(json.dumps({
                        'action': 'user_recipes_list',
                        'recipes': saved_recipes
                    }))
                continue

            if 'action' in data_dict and data_dict['action'] == 'load_more_messages':
                userID = await get_user_id(app.state.pool, username)
                last_loaded_timestamp = data_dict.get('last_loaded_timestamp')
                older_messages = await get_messages_before(app.state.pool, userID, last_loaded_timestamp)
                await websocket.send_text(json.dumps({
                    'action': 'older_messages',
                    'messages': older_messages
                }))
                continue

            if 'action' in data_dict and data_dict['action'] == 'print_recipe':
                recipe_id = data_dict.get('content')
                print_result = await get_recipe_for_printing(app.state.pool, recipe_id)
                await websocket.send_text(json.dumps({'action': 'recipe_printed', 'data': print_result}))
                continue

            if 'action' in data_dict and data_dict['action'] == 'remove_recipe':
                recipe_id = data_dict.get('content')
                userID = await get_user_id(app.state.pool, username)
                remove_result = await un_favorite_recipe(app.state.pool, userID, recipe_id)
                continue

            if 'action' in data_dict and data_dict['action'] == 'chat_message':
                message = data_dict.get('message', '')
                uuid = str(uuid4())
                user_ip = client_ip
                print(f"User IP: {user_ip}")
                response_text, content_type, recipe_id = await generate_answer(app.state.pool, username, message, user_ip, uuid, persona)
                response = {
                    'response': response_text,
                    'type': content_type,
                    'recipe_id': recipe_id
                }
                await websocket.send_text(json.dumps(response))
                continue
            else:
                print("Invalid action:", data_dict)

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for user {username}")
        print(f"Connections: {connections}")
        print(f"sessionid:", session_id)

        if session_id:
            task = asyncio.create_task(clear_session_data_after_timeout(session_id, username))
            tasks[session_id] = task

        connections.pop(username, None)

    except Exception as e:
        print(f"Unhandled exception for user {username}: {e}")
        print("Exception Traceback: " + traceback.format_exc())
    finally:
        ping_task.cancel()

async def on_user_reconnect(username, session_id):
    if session_id in tasks:
        tasks[session_id].cancel()
        del tasks[session_id]
        print(f"Clear data task canceled for user {username}")

@router.post("/validate_session")
async def validate_session(request: Request):
    session_id = request.json().get('session_id', '')
    if session_id and redis_client.exists(session_id):
        return {"status": "valid"}
    else:
        return {"status": "invalid"}

# Run with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
