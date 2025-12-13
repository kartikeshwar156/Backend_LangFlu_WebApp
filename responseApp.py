import os
from pathlib import Path
from urllib.parse import urlencode
import logging

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
import uvicorn
from google import genai
from classTypes import LLM_Response, ConversationRequest
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Load .env variables from the repo-local file so development works out of the box.
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY", "AIzaSyABCwnvWjXNN8uOtEH5zSWesc5b1a4u6Xs")
GEMINI_API_MODEL = os.getenv("GEMINI_API_MODEL", "models/gemini-flash-latest")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI]):
    raise RuntimeError("Environment variables not detected")

# Google ENDpoints to use

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def healthcheck():
    return {"status": "ok"}


@app.get("/auth/google/start")
def login():
    query_params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(query_params)}"
    return RedirectResponse(url)

# call back url called by google to redirect to required frontend


@app.get("/auth/callback")
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(
            status_code=400, detail="Authorization code not found")

    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(GOOGLE_TOKEN_ENDPOINT, data=data)
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=400, detail="Failed to retrieve access token")

        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_response = await client.get(GOOGLE_USERINFO_ENDPOINT, headers=headers)
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()

    # Redirect back to the SPA with the minimal profile in the query string.
    return RedirectResponse(
        f"{FRONTEND_ORIGIN}/?name={userinfo.get('name')}&email={userinfo.get('email')}&picture={userinfo.get('picture')}"
    )


@app.post("/api/conversation", response_model=LLM_Response)
async def ask_response(user_request: ConversationRequest):
    try:
        # Format the conversation history for the prompt
        conversation_text = ""
        for qa in user_request.question_answers:
            conversation_text += f"Question: {qa.quest}\n"
            if qa.user_answer:
                conversation_text += f"User Answer: {qa.user_answer}\n"
            if qa.expected_answer:
                conversation_text += f"Suggested Answer: {qa.expected_answer}\n"
            conversation_text += "\n"

        final_query = f"""
        We are having a conversation like this:
        
        {conversation_text}
        
        I want this discussion to continue. According to this discussion, analyze the last answer the user gave and suggest a more appropriate answer the user could have given and which is more fluent and clear to speak according to data provided about user. Also suggest the next question we can ask to the user.
        
        You should give your response ONLY in JSON format like this:
        {{
            "next_question": "your suggested question here",
            "suggested_answer": "your suggested answer here"
        }}
        
        Only return the JSON, nothing else.
        """

        client = genai.Client(api_key="AIzaSyABCwnvWjXNN8uOtEH5zSWesc5b1a4u6Xs")
        final_response = client.models.generate_content(
            model=GEMINI_API_MODEL,
            contents=final_query
        )

        logger.info(f"LLM Response: {final_response.text}")

        # Parse the JSON response
        import json
        import re

        # Extract JSON from the response (in case there's extra text)
        response_text = final_response.text.strip()
        # Try to find JSON object in the response
        json_match = re.search(
            r'\{[^{}]*"next_question"[^{}]*"suggested_answer"[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)

        # Parse JSON
        try:
            response_data = json.loads(response_text)
            llm_response = LLM_Response(
                next_question=response_data.get(
                    "next_question", "How are you feeling about your English practice?"),
                suggested_answer=response_data.get(
                    "suggested_answer", "That's a good start!")
            )
            return llm_response
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            # Fallback response
            return LLM_Response(
                next_question="How are you feeling about your English practice?",
                suggested_answer="That's a good start! Keep practicing."
            )

    except Exception as e:
        logger.error(f"Error in conversation endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error processing query: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "responseApp:app",
        host="0.0.0.0",
        port=8080,
        reload=False,  # Disable reload in production
    )
