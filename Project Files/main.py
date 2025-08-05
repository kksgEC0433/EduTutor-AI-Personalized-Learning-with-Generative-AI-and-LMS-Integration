from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid

app = FastAPI()

# --- Models ---
class QuizRequest(BaseModel):
    topic: str
    difficulty: Optional[str] = "medium"

class QuizResponse(BaseModel):
    quiz_id: str
    questions: List[str]

class DiagnosticRequest(BaseModel):
    student_level: Optional[str] = "beginner"

class DiagnosticResponse(BaseModel):
    diagnostic_id: str
    questions: List[str]

# --- Watsonx/Granite AI Integration Stubs ---
def generate_quiz_with_watsonx(topic: str, difficulty: str) -> List[str]:
    # TODO: Replace this stub with real IBM Watsonx/Granite LLM API call
    if difficulty == "hard":
        return [
            f"Explain the advanced concepts of {topic}.",
            f"Provide an in-depth example related to {topic}."
        ]
    else:
        return [
            f"What is {topic}?",
            f"Give a simple example of {topic}."
        ]

def generate_diagnostic_with_granite(level: str) -> List[str]:
    # TODO: Replace this stub with real IBM Watsonx/Granite LLM API call
    if level == "beginner":
        return ["What is 2+2?", "Name a primary color."]
    else:
        return ["Solve x in 2x+5=15.", "Describe the process of photosynthesis."]

# --- Endpoints ---
@app.post("/generate_quiz", response_model=QuizResponse)
def generate_quiz(req: QuizRequest):
    questions = generate_quiz_with_watsonx(req.topic, req.difficulty)
    quiz_id = str(uuid.uuid4())
    return QuizResponse(quiz_id=quiz_id, questions=questions)

@app.post("/generate_diagnostic", response_model=DiagnosticResponse)
def generate_diagnostic(req: DiagnosticRequest):
    questions = generate_diagnostic_with_granite(req.student_level)
    diagnostic_id = str(uuid.uuid4())
    return DiagnosticResponse(diagnostic_id=diagnostic_id, questions=questions)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)