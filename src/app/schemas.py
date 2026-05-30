from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Role = Literal["admin", "teacher", "student"]


class UserPublic(BaseModel):
    id: int
    username: str
    full_name: str
    role: Role
    is_active: bool


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    full_name: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    role: Role
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=120)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role: Role | None = None
    is_active: bool | None = None


class OptionInput(BaseModel):
    text: str = Field(min_length=1, max_length=200)
    is_correct: bool


class OptionView(BaseModel):
    id: int
    text: str
    position: int
    is_correct: bool | None = None


class QuestionInput(BaseModel):
    prompt: str = Field(min_length=5, max_length=500)
    explanation: str = Field(default="", max_length=500)
    options: list[OptionInput] = Field(min_length=2, max_length=6)

    @model_validator(mode="after")
    def ensure_single_correct_answer(self) -> "QuestionInput":
        correct_answers = [item for item in self.options if item.is_correct]
        if len(correct_answers) != 1:
            raise ValueError("Each question must contain exactly one correct answer.")
        return self


class QuestionView(BaseModel):
    id: int
    prompt: str
    explanation: str
    position: int
    options: list[OptionView]


class TestInput(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=1000)
    questions: list[QuestionInput] = Field(min_length=1, max_length=20)
    is_published: bool = False


class TestSummary(BaseModel):
    id: int
    title: str
    description: str
    is_published: bool
    owner_id: int
    owner_name: str
    question_count: int
    attempt_count: int
    updated_at: datetime


class TestView(BaseModel):
    id: int
    title: str
    description: str
    is_published: bool
    owner_id: int
    owner_name: str
    created_at: datetime
    updated_at: datetime
    questions: list[QuestionView]


class PublishRequest(BaseModel):
    is_published: bool


class SubmitAnswer(BaseModel):
    question_id: int
    option_id: int


class AttemptSubmitRequest(BaseModel):
    answers: list[SubmitAnswer] = Field(min_length=1)


class AttemptAnswerView(BaseModel):
    question_id: int
    option_id: int
    is_correct: bool


class AttemptView(BaseModel):
    id: int
    test_id: int
    test_title: str
    student_id: int | None = None
    student_name: str | None = None
    score: int
    total_questions: int
    submitted_at: datetime
    answers: list[AttemptAnswerView]
