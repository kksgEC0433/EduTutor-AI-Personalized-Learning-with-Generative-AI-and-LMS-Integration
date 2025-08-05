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