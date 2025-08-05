from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import uuid
import requests
import os

# For Granite local inference
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
import torch

app = FastAPI()

# --------- CONFIG ---------
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "9dw4LziolvR-2msfDoJN8FXZAk0pKBpyXIGUmh32OnNe")
WATSONX_API_URL = "https://eu-de.ml.cloud.ibm.com/ml/v1/text/generate"
WATSONX_MODEL_ID = "granite-13b-chat-v1"  # Or your preferred model

GRANITE_MODEL_PATH = "ibm-granite/granite-3.3-8b-instruct"
GRANITE_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --------- GRANITE MODEL LOAD ON STARTUP (slow, but efficient for repeated calls) ---------
print("Loading Granite model...")
granite_model = AutoModelForCausalLM.from_pretrained(
    GRANITE_MODEL_PATH, device_map=GRANITE_DEVICE, torch_dtype=torch.bfloat16 if GRANITE_DEVICE=="cuda" else torch.float32
)
granite_tokenizer = AutoTokenizer.from_pretrained(GRANITE_MODEL_PATH)
print("Granite model loaded.")

# --------- DATA MODELS ---------
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

# --------- WATSONX API CALL ---------
def call_watsonx_generate_quiz(topic: str, difficulty: str) -> List[str]:
    prompt = f"Generate a {difficulty} quiz with 2 questions about the topic: {topic}. Return ONLY the questions as a numbered list."
    headers = {
        "Authorization": f"Bearer {WATSONX_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model_id": WATSONX_MODEL_ID,
        "input": prompt
    }
    resp = requests.post(WATSONX_API_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        print("Watsonx error:", resp.text)
        return [f"Error from Watsonx: {resp.text}"]
    data = resp.json()
    # Watsonx returns: {"results": [{"generated_text": "..."}]}
    questions_raw = data["results"][0]["generated_text"].strip()
    # Parse numbered list into separate questions
    questions = [q.strip(" .") for q in questions_raw.split("\n") if q.strip()]
    # Remove leading numbers if present
    questions = [q[q.find('.')+1:].strip() if q[:2].isdigit() and '.' in q else q for q in questions]
    return questions

# --------- GRANITE (LOCAL) CALL ---------
def call_granite_generate_diagnostic(level: str) -> List[str]:
    if level == "beginner":
        prompt = "Generate a simple diagnostic test with 2 basic questions for a beginner student. Return ONLY the questions as a numbered list."
    else:
        prompt = "Generate a diagnostic test with 2 advanced questions for an advanced student. Return ONLY the questions as a numbered list."
    conv = [{"role": "user", "content": prompt}]
    input_ids = granite_tokenizer.apply_chat_template(conv, return_tensors="pt", add_generation_prompt=True).to(GRANITE_DEVICE)
    set_seed(42)
    output = granite_model.generate(
        **input_ids,
        max_new_tokens=512,
    )
    prediction = granite_tokenizer.decode(output[0, input_ids["input_ids"].shape[1]:], skip_special_tokens=True)
    # Parse as numbered list
    questions = [q.strip(" .") for q in prediction.split("\n") if q.strip()]
    questions = [q[q.find('.')+1:].strip() if q[:2].isdigit() and '.' in q else q for q in questions]
    return questions if questions else [prediction]

# --------- ENDPOINTS ---------
@app.post("/generate_quiz", response_model=QuizResponse)
def generate_quiz(req: QuizRequest):
    questions = call_watsonx_generate_quiz(req.topic, req.difficulty)
    quiz_id = str(uuid.uuid4())
    return QuizResponse(quiz_id=quiz_id, questions=questions)

@app.post("/generate_diagnostic", response_model=DiagnosticResponse)
def generate_diagnostic(req: DiagnosticRequest):
    questions = call_granite_generate_diagnostic(req.student_level)
    diagnostic_id = str(uuid.uuid4())
    return DiagnosticResponse(diagnostic_id=diagnostic_id, questions=questions)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)