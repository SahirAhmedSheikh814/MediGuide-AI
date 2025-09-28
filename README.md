# 🩺 MediGuide AI

MediGuide AI is an **AI-powered medical assistant chatbot** that helps users interact with healthcare knowledge in a conversational way.  
It uses **LangChain, FAISS, and OpenAI embeddings** to provide context-aware answers from ingested PDF medical documents.  
Deployed on **Railway.app** with a clean and responsive UI powered by **Chainlit**.

---

## ✨ Features

- 📂 **PDF Knowledge Base** – Upload & index medical PDFs into FAISS vector store.  
- 🤖 **AI Chatbot** – Ask context-aware questions, get accurate responses.  
- ⚡ **Fast Search** – Uses FAISS for efficient vector similarity search.  
- 🎨 **Custom UI** – Interactive chatbot UI with branding & logo.  
- ☁️ **Deployment Ready** – Fully deployable on [Railway.app](https://railway.app).  
- 🔒 **Environment Variables Support** – Securely manage API keys & configs.  

---

## 🚀 Tech Stack

- [Python 3.10+](https://www.python.org/)  
- [LangChain](https://www.langchain.com/)  
- [FAISS](https://github.com/facebookresearch/faiss)  
- [Chainlit](https://docs.chainlit.io/)  
- [OpenAI API](https://platform.openai.com/)  
- [Railway](https://railway.app/)  

---

## ⚙️ Installation (Local Development)

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/MediGuide-AI.git
   cd MediGuide-AI

2. **Create virtual environment & activate**
    ```bash
    python -m venv venv
    source venv/bin/activate   # Mac/Linux
    venv\Scripts\activate      # Windows


3. **Install dependencies**
    ```bash
    pip install -r requirements.txt


4. **Setup environment variables**
Create a .env file in the root directory:
    ```bash
    OPENAI_API_KEY=your_openai_api_key

5. **Ingest PDFs into FAISS**
Place your PDFs in the /docs folder and run:
    ```bash
    python ingest.py

6. **Run locally with Chainlit**
    ```bash
    chainlit run main.py -w

---

## ☁️ Deployment (Railway)

1. Push your project to GitHub.

2. Connect GitHub repo to Railway.

3. Add environment variables in Railway dashboard:
    - OPENAI_API_KEY = your API key

4. Add start command under Settings → Deploy → Start Command:
    ```bash
    chainlit run main.py --host 0.0.0.0 --port $PORT

5. Deploy 🎉 and access your chatbot via generated domain.

---

🧑‍💻 Usage

- Open the deployed app link.

- Start chatting with the AI assistant.

- For new knowledge, re-ingest PDFs and redeploy.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

---

## 📜 License

- Distributed under the MIT License.
- See LICENSE for more information.