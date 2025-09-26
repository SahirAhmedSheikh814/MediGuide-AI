document.addEventListener("DOMContentLoaded", function () {
  if (document.getElementById("welcome-notification")) return;

  const notification = document.createElement("div");
  notification.id = "welcome-notification";
  notification.innerHTML = `
    <h3>👋 Welcome to the ABIM MCQ Generator!</h3>
    <p>I am designed to create high-quality, exam-ready multiple-choice questions (MCQs) tailored to your needs, complete with answers and detailed explanations.</p>
    <strong>How to Use:</strong>
    <p>• Request a specific number of MCQs on a topic (e.g., "Generate 5 MCQs on diabetes").</p>
    <p>• Request a full-length exam (e.g., "Generate a full exam with 240 MCQs").</p>
    <p>Get started now to enhance your preparation with professional, ABIM-style questions!</p>
    <div class="btn-container">
      <button id="thanks-btn">Thanks</button>
    </div>
  `;

  document.body.appendChild(notification);

  document.getElementById("thanks-btn").addEventListener("click", function () {
    notification.style.display = "none";
  });
});
