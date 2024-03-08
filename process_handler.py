#process_handler.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

import os
import base64
import hashlib
import httpx
import jwt
import datetime
import json
import time
import pymysql

from config import Config
from process_handler_database import create_db_pool, save_code_verifier, get_code_verifier, generate_code_verifier_and_challenge, get_data_from_db, save_user_info_to_userdata, delete_code_verifier, delete_old_verifiers
import jwt
from jwt.algorithms import RSAAlgorithm
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import logging
import asyncio

import redis

log_file_path = Config.LOG_PATH
LOG_FORMAT = 'generate-answer - %(asctime)s - %(processName)s - %(name)s - %(levelname)s - %(message)s'

logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,  # Adjust the log level as needed (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format=LOG_FORMAT
)
import redis

# Initialize Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)  # Adjust host and port as needed


app = FastAPI()




# Define session middleware
app.add_middleware(SessionMiddleware, secret_key=Config.SESSION_SECRET_KEY)

#####!!!!  Startup   !!!!!!################
@app.on_event("startup")
async def startup():
    app.state.pool = await create_db_pool()  # No argument is passed here
    print(f"Database pool created: {app.state.pool}")
    asyncio.create_task(schedule_verifier_cleanup(app.state.pool, redis_client))


#####!!!!  Startup   !!!!!!################

async def schedule_verifier_cleanup(pool, redis_client):
    while True:
        # Attempt to acquire the lock
        if redis_client.set("verifier_cleanup_lock", "true", nx=True, ex=60):
            print("Lock acquired. Running cleanup task.")
            await delete_old_verifiers(pool)
            redis_client.delete("verifier_cleanup_lock")
        else:
            print("Lock not acquired. Skipping cleanup task.")
        
        # Wait for 60 seconds before the next attempt
        await asyncio.sleep(60)


################################################################## 
######!!!!       Routes                !!!!!######################
##################################################################

################################################################## 
######!!!!     Start login endpoint    !!!!!######################
##################################################################

@app.get("/login")
async def login(request: Request):
    #set login timestemp
    login_timestamp  = datetime.datetime.now()


    # Getting the client's IP address
    client_ip = request.client.host
        
    #get code_verifier and code_challenge
    code_verifier, code_challenge = await generate_code_verifier_and_challenge()
    
    # generate a state code to link things later
    state = os.urandom(24).hex()  # Generate a random state value
    
    
    await save_code_verifier(app.state.pool, state, code_verifier, client_ip, login_timestamp)  # Corrected function name
    
    cognito_login_url = (
        f"{Config.COGNITO_DOMAIN}/login?response_type=code&client_id={Config.COGNITO_APP_CLIENT_ID}"
        f"&redirect_uri={Config.REDIRECT_URI}&state={state}&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )
    
    return RedirectResponse(cognito_login_url)

################################################################## 
######!!!!     End login endpoint      !!!!!######################
##################################################################

################################################################## 
######!!!!     Start callback  endpoint!!!!!######################
##################################################################

@app.get("/callback")

async def callback(request: Request, code: str, state: str):
    
     # Extract query parameters
    query_params = request.query_params
    code = query_params.get('code')
    state = query_params.get('state')
    client_ip = request.client.host
    
    if not code:
        raise HTTPException(status_code=400, detail="Code parameter is missing")

    # Retrieve the code_verifier using the state
    code_verifier = await get_code_verifier(app.state.pool,state)
    if not code_verifier:
        raise HTTPException(status_code=400, detail="Invalid state or code_verifier missing")

    #delete the code verifier since we don't really need it anymore and it's risky
    await delete_code_verifier(app.state.pool, state)
    
    tokens = await exchange_code_for_token(code, code_verifier)
    if tokens:
        id_token = tokens['id_token']
        decoded_token = await validate_token(id_token)

        # Retrieve session data
        session = request.session

        # Store user information in session
        session['email'] = decoded_token.get('email', 'unknown')
        session['username'] = decoded_token.get('cognito:username', 'unknown')
        session['name'] = decoded_token.get('name', 'unknown')
        session['session_id'] = os.urandom(24).hex()  # Generate a random state value

        #await save_user_info_to_mysql(app.state.pool, session, client_ip, state)
        await save_user_info_to_userdata(app.state.pool, session)
        session_id = session['session_id']
        session_data = {
        'email': decoded_token.get('email', 'unknown'),
        'username': decoded_token.get('cognito:username', 'unknown'),
        'name': decoded_token.get('name', 'unknown'),
        'session_id': session['session_id']
        }
        print("setting redis in login")
        redis_client.set(session_id, json.dumps(session_data), ex=3600)  # ex is expiry time in seconds

        
        
        
        # Prepare the URL with query parameters
        chat_html_url = '/chat.html'  # Replace with the actual URL of your chat.html
        redirect_url = f"{chat_html_url}?sessionId={session['session_id']}"

        # Redirect the user to the chatbot interface with query parameters
        return RedirectResponse(url=redirect_url, status_code=302)
    else:
        return 'Error during token exchange.', 400
    

##################################################################
######!!!!     End callback endpoint   !!!!!######################
##################################################################


##################################################################
######!!!!     start get ssession endpoint!!######################
##################################################################

@app.get("/get_session_data")
async def get_session_data(request: Request):
    print("at /get_session_data")
    # Retrieve session data
    session_id = request.session.get('session_id')
    
    # If session_id is not available, return an error
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID not found in session data")

    
    # Retrieve additional data from the database using the session_id
    db_data = await get_data_from_db(session_id, app.state.pool)
    state = db_data['state']
    username = db_data.get('username')
    


    # You can merge the user_info with db_data if needed
    # user_info.update(db_data)  # Uncomment this line if you want to merge

    
    return JSONResponse(content={
        "sessionId": session_id,
        "nonce": state,
        "userInfo": username  # or db_data if you have merged them
    })


##################################################################
######!!!!     end get ssession endpoint  !!######################
##################################################################

##################################################################
######!!!!     Start Functions           !!!!!####################
##################################################################

# exhange code for token
async def exchange_code_for_token(code, code_verifier):
    token_url = f"{Config.COGNITO_DOMAIN}/oauth2/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'authorization_code',
        'client_id': Config.COGNITO_APP_CLIENT_ID,
        'code': code,
        'redirect_uri': Config.REDIRECT_URI,
        'code_verifier': code_verifier
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()
        
    else:
        return None

# validate token
async def validate_token(id_token):
    COGNITO_USER_POOL_ID = Config.COGNITO_USER_POOL_ID
    COGNITO_APP_CLIENT_ID = Config.COGNITO_APP_CLIENT_ID
    jwks_url = f"https://cognito-idp.us-east-1.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    #jwks_response = requests.get(jwks_url)
    with httpx.Client() as client:
        jwks_response = client.get(jwks_url)
    jwks = jwks_response.json()

    headers = jwt.get_unverified_header(id_token)
    kid = headers['kid']
    key = [k for k in jwks['keys'] if k['kid'] == kid][0]
    pem = RSAAlgorithm.from_jwk(json.dumps(key))

    decoded_token = jwt.decode(
        id_token,
        pem,
        algorithms=['RS256'],
        audience=COGNITO_APP_CLIENT_ID
    )
    return decoded_token

######   Sessions

async def get_session(request: Request):
    return request.session





##################################################################


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
