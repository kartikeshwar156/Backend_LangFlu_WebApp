from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class QuestionAnswer(BaseModel):
    """Represents a single question-answer pair"""
    quest: str
    user_answer: str
    expected_answer: str


class UserProfile(BaseModel):
    """Represents user profile information from Google OAuth"""
    name: Optional[str] = None
    email: Optional[str] = None
    picture: Optional[str] = None


class ConversationRequest(BaseModel):
    """Request body for the conversation API endpoint"""
    question_answers: List[QuestionAnswer]
    # Flexible dict for onboarding responses
    onboarding_answers: Dict[str, Any]


class LLM_Response(BaseModel):
    """Response from LLM containing next question and suggested answer"""
    next_question: str
    suggested_answer: str
