import requests
import os
import hashlib
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import OpenAI
import openai


# Step 1: Download PDF from arXiv URL
def download_pdf(url):
    if url.startswith("https://arxiv.org/abs/"):
        url = url.replace("abs", "pdf")

    url_hash = hashlib.md5(url.encode()).hexdigest()
    pdf_path = f"pdfs/{url_hash}.pdf"

    if os.path.exists(pdf_path):
        print("PDF already downloaded.")
        return pdf_path
    
    os.makedirs("pdfs", exist_ok=True)

    response = requests.get(url)
    with open(pdf_path, "wb") as f:
        f.write(response.content)
    return pdf_path

# Step 2: Extract content from PDF
# def extract_text_from_pdf(pdf_path):
#     text = ""
#     with open(pdf_path, "rb") as file:
#         pdf_reader = PdfReader(file)
#         for page in pdf_reader.pages:
#             text += page.extract_text()
#     return text

async def extract_text_from_pdf(pdf_path):
    # curl -X POST -F "file=@2401.01854.pdf" http://localhost:8000/parse_document/pdf 
    url = "http://localhost:8000/parse_document/pdf"
    files = {"file": open(pdf_path, "rb")}
    response = requests.post(url, files=files, timeout=240)
    text = response.json()["text"]
    with open(f"{pdf_path}.txt", "w") as f:
        f.write(text)
    return text

def get_vector_store(url, pdf_text, use_cache = True):
    # URL을 해시하여 고유한 파일 이름 생성
    url_hash = hashlib.md5(url.encode()).hexdigest()
    vector_store_path = f"vector_stores/{url_hash}"

    if os.path.exists(vector_store_path) and use_cache:
        # 기존 벡터 스토어 로드
        embeddings = OpenAIEmbeddings()
        vector_store = FAISS.load_local(vector_store_path, embeddings, allow_dangerous_deserialization=True)
        print("Loaded existing vector store.")
    else:
        # 새 벡터 스토어 생성
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        chunks = text_splitter.split_text(pdf_text)
        
        embeddings = OpenAIEmbeddings()
        vector_store = FAISS.from_texts(chunks, embeddings)
        
        # 벡터 스토어를 로컬에 저장
        vector_store.save_local(vector_store_path)
        with open(f"vector_stores/{url_hash}/text.md", "w") as f:
            f.write(pdf_text)
        print("Created and saved new vector store.")

    return vector_store

def setup_conversational_chain(vector_store):
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=OpenAI(temperature=0),
        retriever=vector_store.as_retriever(search_kwargs={"k": 5}),  # Increased from 3 to 5
        memory=memory,
        max_tokens_limit=3500  # Increased from 3000 to 3500
    )
    return conversation_chain

# Updated main chatbot function
def chatbot():
    print("Welcome to the arXiv PDF QA Chatbot!")
    arxiv_url = input("Please enter the arXiv PDF URL: ")
    
    pdf_path = download_pdf(arxiv_url)
    pdf_text = extract_text_from_pdf(pdf_path)
    
    vector_store = get_vector_store(arxiv_url, pdf_text)
    conversation_chain = setup_conversational_chain(vector_store)
    
    print("PDF processed. You can now ask questions about its content.")
    
    while True:
        user_question = input("You: ")
        if user_question.lower() in ["exit", "quit", "bye"]:
            print("Chatbot: Goodbye!")
            break
        
        try:
            response = conversation_chain({"question": user_question})
            print("Chatbot:", response['answer'])
        except Exception as e:
            print(f"Error: {e}")
            print("An error occurred. Please try asking a different question.")

# Run the chatbot
if __name__ == "__main__":
    chatbot()