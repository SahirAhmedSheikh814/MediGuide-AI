import os
import re
import math
import asyncio
from dotenv import load_dotenv
import chainlit as cl
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from typing import Optional, Tuple, Dict, List

# ================================
# Load env
# ================================
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_base_url = os.getenv("OPENAI_BASE_URL")

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")
if not openai_base_url:
    raise ValueError("OPENAI_BASE_URL environment variable is not set")

# ================================
# LLM init
# ================================
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
    api_key=openai_api_key,
    base_url=openai_base_url,
    max_retries=3,
)

# ================================
# Vector store / PDF syllabus loader
# ================================
PDF_DIR = "./syllabus_pdfs"
if not os.path.exists(PDF_DIR):
    os.makedirs(PDF_DIR)
    print("Created syllabus_pdfs directory. Place all PDF files there.")

@cl.cache
def load_vectorstore():
    print("Starting to build vector store from PDFs...")
    loader = PyPDFDirectoryLoader(PDF_DIR)
    documents = loader.load()[:50]
    print(f"Loaded {len(documents)} documents.")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)
    print(f"Split into {len(texts)} text chunks.")
    embeddings = OpenAIEmbeddings(api_key=openai_api_key, base_url=openai_base_url, chunk_size=100)
    vectorstore = FAISS.from_documents(texts, embeddings)
    vectorstore.save_local("faiss_index")
    print("✅ Vector store built and saved successfully!")
    return vectorstore

embeddings = OpenAIEmbeddings(api_key=openai_api_key, base_url=openai_base_url)

if os.path.exists("faiss_index"):
    try:
        print("📂 Loading existing vector store from faiss_index...")
        vectorstore = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        print("✅ Existing vector store loaded successfully!")
    except Exception as e:
        print(f"[WARN] Failed to load faiss_index ({e}). Rebuilding...")
        vectorstore = load_vectorstore()
else:
    vectorstore = load_vectorstore()

def search_syllabus(query: str) -> str:
    try:
        print(f"Searching syllabus for query: {query}...")
        results = vectorstore.similarity_search(query, k=5)
        if not results:
            print("No relevant content found in syllabus.")
            return ""
        print(f"Found {len(results)} relevant documents.")
        return "\n\n".join([doc.page_content for doc in results])
    except Exception as e:
        print(f"[WARN] search_syllabus failed: {e}")
        return ""

search_tool = Tool(
    name="Syllabus_Search",
    func=search_syllabus,
    description="Search the ABIM syllabus PDFs for content on a specific topic. Input: topic query."
)

# ================================
# Exam Blueprint mapping
# ================================
BLUEPRINT_PERCENTAGES: Dict[str, float] = {
    "Cardiovascular Disease": 14.0,
    "Endocrinology, Diabetes, and Metabolism": 9.0,
    "Gastroenterology": 9.0,
    "Infectious Disease": 9.0,
    "Pulmonary Disease": 9.0,
    "Rheumatology and Orthopedics": 9.0,
    "Hematology": 6.0,
    "Nephrology and Urology": 6.0,
    "Medical Oncology": 6.0,
    "Neurology": 4.0,
    "Psychiatry": 4.0,
    "Dermatology": 3.0,
    "Obstetrics and Gynecology": 3.0,
    "Geriatric Syndromes": 3.0,
    "Allergy and Immunology": 2.0,
    "Miscellaneous": 2.0,
    "Ophthalmology": 1.0,
    "Otolaryngology and Dental Medicine": 1.0,
}

# ================================
# Input parsing
# ================================
MCQ_TRIGGERS = [r"\bmcq\b", r"\bmcqs\b", r"\bquestions\b", r"\bsawal\b", r"\bmake\b", r"\bcreate\b"]

def parse_user_input(text: str) -> Optional[Tuple[int, str, bool]]:
    t = (text or "").strip().lower()
    if not t:
        return None
    if re.search(r"\b(blueprint|full exam|full set|generate full|complete exam|240 mcqs|240 questions)\b", t):
        num = 240
        return (num, "BLUEPRINT", True)
    if not any(re.search(p, t) for p in MCQ_TRIGGERS):
        return None
    num_match = re.search(r"\b(\d{1,3})\b", t)
    num = int(num_match.group(1)) if num_match else 5
    m = re.search(r"(?:for|on|about|topic|regarding)\s+(.+)$", t)
    if m:
        return (num, m.group(1), False)
    return (num, t, False)

# ================================
# Vignette Control Helper
# ================================
def enforce_vignette_ratio(mcq_text: str, num: int) -> str:
    """Ensure vignette MCQs follow the required ratio (1 per 10)."""
    required_vignette = max(1, math.ceil(num / 10))
    mcqs = re.split(r"\n(?=Q\d+\.)", mcq_text.strip())
    vignette_mcqs = [q for q in mcqs if re.search(r"\b\d{2,3}-year-old\b", q)]
    non_vignette_mcqs = [q for q in mcqs if q not in vignette_mcqs]

    if len(vignette_mcqs) > required_vignette:
        vignette_mcqs = vignette_mcqs[:required_vignette]
        mcqs = vignette_mcqs + non_vignette_mcqs
    elif len(vignette_mcqs) < required_vignette and non_vignette_mcqs:
        needed = required_vignette - len(vignette_mcqs)
        to_convert = non_vignette_mcqs[:needed]
        converted = [
            re.sub(
                r"^Q\d+\.\s*",
                lambda m: m.group(0) + "A 55-year-old man presents with ",
                q,
                1,
            )
            for q in to_convert
        ]
        vignette_mcqs.extend(converted)
        mcqs = vignette_mcqs + non_vignette_mcqs[needed:]

    return "\n".join(mcqs)

# ================================
# Prompt builder
# ================================
def build_mcq_prompt(topic: str, num: int, syllabus: str) -> str:
    syllabus_snippet = (syllabus or "").strip()[:2500]
    num_vignette = max(1, math.ceil(num / 10))
    return f"""
You are an experienced ABIM exam MCQ writer. Produce {num} **unique and professional** MCQs on "{topic}".

Requirements:
- ⚠️ Do not repeat any previously generated questions.
- Exactly {num_vignette} should be full patient vignette style (e.g., "A 50-year-old man..."). generate less mcqs of vignette type
- The rest MUST be diverse and **not repetitive**.
- Ensure a good mix of question types:
  * Some factual recall (definitions, anatomy, physiology).
  * Some diagnostic criteria / risk factor questions.
  * Some management / next-step questions.
  * Some interpretation (labs, imaging, ECG).
  * Some drug mechanism / contraindication questions.
- Each question must have **4 answer options (A–D)** with no gaps between them, one correct answer, and a concise evidence-based explanation (1–3 lines), Don't use bold text for explanation.
- Use syllabus content if provided below, otherwise standard clinical knowledge.
  * Use this line two separate each mcq ---------------------------------------- 
  
Syllabus (if available):
{syllabus_snippet}

Format strictly:
Q1. [stem]

A. option
B. option
C. option
D. option

Correct Answer: [A/B/C/D] \n
Explanation: [detailed explanation]

Now produce {num} questions.
"""

# ================================
# Async MCQ generator (with vignette fix)
# ================================
async def generate_mcqs_for_topic_async(topic: str, num: int):
    syllabus = search_syllabus(topic)
    prompt = build_mcq_prompt(topic, num, syllabus)

    msg = cl.Message(content=f"⏳ Generating {num} MCQs for **{topic}**...\n")
    await msg.send()

    buffer = ""
    async for chunk in llm.astream([HumanMessage(content=prompt)]):
        if not chunk.content:
            continue
        buffer += chunk.content
        if len(buffer) > 1500:
            msg.content += buffer
            await msg.update()
            buffer = ""

    if buffer.strip():
        final_text = buffer.strip()
        final_text = enforce_vignette_ratio(final_text, num)  # 🔥 enforce vignette ratio
        msg.content += final_text
        await msg.update()

# ================================
# Blueprint allocation
# ================================
def allocate_counts_by_blueprint(total: int) -> Dict[str, int]:
    allocation = {}
    remaining = total
    for cat, pct in BLUEPRINT_PERCENTAGES.items():
        cnt = int(math.floor(total * (pct / 100)))
        allocation[cat] = cnt
        remaining -= cnt
    while remaining > 0:
        for cat in sorted(BLUEPRINT_PERCENTAGES, key=BLUEPRINT_PERCENTAGES.get, reverse=True):
            allocation[cat] += 1
            remaining -= 1
            if remaining == 0:
                break
    return allocation

# ================================
# Non-MCQ reply
# ================================
NON_MCQ_REPLY = (
    "Hi, I am an MCQ Generator Chatbot. I am specifically designed to assist exam writers by generating multiple-choice questions quickly and efficiently. My purpose is to save your time and effort by creating MCQs on any medical topic you provide. Simply share the subject or area you need, and I will generate well-structured questions along with accurate answers and explanations. Thank you for using this tool to streamline your exam preparation process. "
    "\nExample: 'Generate 10 MCQs on cardiology' or 'Generate full exam (240 MCQs)'."
)

# ================================
# Chainlit Handlers (with cancel support)
# ================================
@cl.on_chat_start
async def start():
    # await cl.Message(
    #     "👋 Welcome to the ABIM MCQ Generator!\n"
    #     "I am designed to create high-quality, exam-ready multiple-choice questions (MCQs) tailored to your needs, complete with answers and detailed explanations.\n"
    #     "How to Use:\n"
    #     "- Request a specific number of MCQs on a topic (e.g., 'Generate 5 MCQs on diabetes').\n"
    #     "- Request a full-length exam (e.g., 'Generate a full exam with 240 MCQs').\n\n"
    #     "Get started now to enhance your preparation with professional, ABIM-style questions!\n"
    # ).send()
    pass

@cl.on_message
async def main_handler(message: cl.Message):
    parsed = parse_user_input(message.content)
    if not parsed:
        await cl.Message(content=NON_MCQ_REPLY).send()
        return

    num, topic, is_blueprint = parsed

    async def run_task():
        if is_blueprint:
            await cl.Message(content=f"📘 Generating full blueprint exam ({num} MCQs)...").send()
            allocation = allocate_counts_by_blueprint(num)
            alloc_text = "\n".join([f"{c}: {n}" for c, n in allocation.items()])
            await cl.Message(content=f"Planned allocation:\n{alloc_text}").send()

            for cat, cnt in allocation.items():
                if cnt <= 0:
                    continue
                await generate_mcqs_for_topic_async(cat, cnt)

            await cl.Message(content="✅ Finished generating the full exam!").send()
        else:
            await generate_mcqs_for_topic_async(topic, num)

    # Wrap in cancellation-aware task
    task = asyncio.create_task(run_task())
    try:
        await task
    except asyncio.CancelledError:
       # await cl.Message(content="❌ Request cancelled by user.").send()
       pass 