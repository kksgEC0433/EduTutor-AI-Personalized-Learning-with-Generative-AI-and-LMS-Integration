# EduTutor AI – Documentation (IBM Watsonx & Granite Integration)

This project is a template for an AI-powered personalized education platform using IBM Watsonx (cloud API) and Granite (local inference).  
You get:
- **Quiz generation** via Watsonx foundation models (cloud API call)
- **Diagnostic test generation** via Granite (local inference using HuggingFace Transformers)
- A FastAPI backend and a sample frontend

---

## Table of Contents

1. [Backend: main.py (explained)](#1-backend-mainpy-explained)
2. [Backend: requirements.txt](#2-backend-requirementstxt)
3. [Frontend: index.html, styles.css, app.js](#3-frontend-indexhtml-stylescss-appjs)
4. [How the system works](#4-how-the-system-works)
5. [How to use the IBM APIs](#5-how-to-use-the-ibm-apis)
6. [Security & Deployment Notes](#6-security--deployment-notes)
7. [Project Structure](#7-project-structure)

---

## 1. Backend: main.py (explained)

```python name=backend/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import uuid
import requests
import os

# Granite (local inference)
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
import torch

app = FastAPI()

# -------- CONFIGURATION --------
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "YOUR_WATSONX_API_KEY")  # Replace with your API key or set as env var
WATSONX_API_URL = "https://eu-de.ml.cloud.ibm.com/ml/v1/text/generate"
WATSONX_MODEL_ID = "granite-13b-chat-v1"  # See IBM docs for other models

GRANITE_MODEL_PATH = "ibm-granite/granite-3.3-8b-instruct"
GRANITE_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# -------- LOAD GRANITE ON STARTUP --------
print("Loading Granite model locally. This may take some time...")
granite_model = AutoModelForCausalLM.from_pretrained(
    GRANITE_MODEL_PATH, device_map=GRANITE_DEVICE, torch_dtype=torch.bfloat16 if GRANITE_DEVICE=="cuda" else torch.float32
)
granite_tokenizer = AutoTokenizer.from_pretrained(GRANITE_MODEL_PATH)
print("Granite model loaded.")

# -------- PYDANTIC DATA MODELS --------
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

# -------- WATSONX QUIZ GENERATION --------
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
    questions_raw = data["results"][0]["generated_text"].strip()
    questions = [q.strip(" .") for q in questions_raw.split("\n") if q.strip()]
    questions = [q[q.find('.')+1:].strip() if q[:2].isdigit() and '.' in q else q for q in questions]
    return questions

# -------- GRANITE (LOCAL) DIAGNOSTIC GENERATION --------
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
    questions = [q.strip(" .") for q in prediction.split("\n") if q.strip()]
    questions = [q[q.find('.')+1:].strip() if q[:2].isdigit() and '.' in q else q for q in questions]
    return questions if questions else [prediction]

# -------- FASTAPI ENDPOINTS --------
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
```

### **Backend Explanation**
- **Watsonx API**: Used for quiz generation (cloud, with your API key and region).
- **Granite Model**: Loaded locally using HuggingFace transformers for diagnostic generation.
- **Quiz and Diagnostic Endpoints**: `/generate_quiz` and `/generate_diagnostic` accept POST requests.
- **Configuration**: API key and model paths can be set in environment variables or directly in code (for demo).

---

## 2. Backend: requirements.txt

```txt name=backend/requirements.txt
fastapi
uvicorn
pydantic
requests
torch
torchvision
torchaudio
accelerate
transformers
```

- **All libraries needed for FastAPI, Watsonx (requests), and local Granite inference.**

---

## 3. Frontend: index.html, styles.css, app.js

### `frontend/index.html`
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>EduTutor AI</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <h1>EduTutor AI - Powered by Watsonx & Granite</h1>
    </header>
    <main>
        <section>
            <h2>Generate Quiz</h2>
            <form id="quiz-form">
                <input type="text" id="quiz-topic" placeholder="Enter topic (e.g., Algebra)" required>
                <select id="quiz-difficulty">
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                </select>
                <button type="submit">Generate Quiz</button>
            </form>
            <div id="quiz-result"></div>
        </section>
        <section>
            <h2>Diagnostic Test</h2>
            <form id="diagnostic-form">
                <select id="diagnostic-level">
                    <option value="beginner">Beginner</option>
                    <option value="advanced">Advanced</option>
                </select>
                <button type="submit">Generate Diagnostic</button>
            </form>
            <div id="diagnostic-result"></div>
        </section>
    </main>
    <script src="app.js"></script>
</body>
</html>
```

**Purpose:**  
A simple UI for generating quizzes (Watsonx) and diagnostics (Granite).

---

### `frontend/styles.css`
```css
body {
    font-family: Arial, sans-serif;
    background: #f5f8fa;
    margin: 0;
    padding: 0;
}
header {
    background: #0062ff;
    color: #fff;
    padding: 20px;
    text-align: center;
}
main {
    max-width: 600px;
    background: #fff;
    margin: 40px auto;
    padding: 30px 40px;
    border-radius: 8px;
    box-shadow: 0 4px 18px rgba(0,0,0,0.09);
}
section {
    margin-bottom: 30px;
}
form input, form select {
    padding: 8px;
    margin-right: 12px;
    border-radius: 4px;
    border: 1px solid #ccc;
}
form button {
    padding: 8px 14px;
    background: #0062ff;
    color: #fff;
    border: none;
    border-radius: 4px;
}
#quiz-result, #diagnostic-result {
    margin-top: 16px;
    font-weight: 500;
    color: #222;
}
```

**Purpose:**  
To provide a clean, modern, and readable style for the frontend.

---

### `frontend/app.js`
```javascript
const backendBase = "http://localhost:8000";

document.getElementById("quiz-form").onsubmit = async (e) => {
    e.preventDefault();
    const topic = document.getElementById("quiz-topic").value;
    const difficulty = document.getElementById("quiz-difficulty").value;
    const res = await fetch(`${backendBase}/generate_quiz`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({topic, difficulty}),
    });
    const data = await res.json();
    document.getElementById("quiz-result").innerHTML =
        "<b>Quiz Questions:</b><ol>" +
        data.questions.map(q => `<li>${q}</li>`).join("") +
        "</ol>";
};

document.getElementById("diagnostic-form").onsubmit = async (e) => {
    e.preventDefault();
    const student_level = document.getElementById("diagnostic-level").value;
    const res = await fetch(`${backendBase}/generate_diagnostic`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({student_level}),
    });
    const data = await res.json();
    document.getElementById("diagnostic-result").innerHTML =
        "<b>Diagnostic Questions:</b><ol>" +
        data.questions.map(q => `<li>${q}</li>`).join("") +
        "</ol>";
};
```

**Purpose:**  
Handles frontend form submission, calls the backend, and displays the results.

---

## 4. How the system works

- **User**: Uses the browser to request a quiz or diagnostic.
- **Frontend**: Sends a POST to backend endpoint.
- **Backend**:  
  - For quizzes: Calls Watsonx API (cloud) using your key and prompt.
  - For diagnostics: Runs Granite model locally using Transformers.
- **Frontend**: Renders the questions as a list.

---

## 5. How to use the IBM APIs

### **Watsonx Foundation Model (Cloud)**
- Endpoint:  
  `POST https://eu-de.ml.cloud.ibm.com/ml/v1/text/generate`
- Auth:  
  Bearer token (your API key)
- Payload:
    ```json
    {
      "model_id": "granite-13b-chat-v1",
      "input": "Generate a medium quiz with 2 questions about Algebra. Return ONLY the questions as a numbered list."
    }
    ```
- See more: [IBM watsonx.ai Foundation Model API](https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/fm-api.html)

### **Granite Instruct (Local)**
- Loaded via HuggingFace Transformers.
- Example:
    ```python
    from transformers import AutoModelForCausalLM, AutoTokenizer
    # See code above for how to use
    ```

---

## 6. Security & Deployment Notes

- Never hardcode API keys for production! Use env vars or a secure config.
- For Granite, ensure you have sufficient GPU RAM (8B models are large).
- For public deployment, use HTTPS and proper CORS config.

---

## 7. Project Structure

```
edututor-ai/
│
├── backend/
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
└── PROJECT_DOCUMENTATION.md
```

---

**You can now use both IBM Watsonx (cloud) and Granite (local) models for your EduTutor AI platform!**