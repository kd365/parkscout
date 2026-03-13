import os
import json
from datetime import datetime
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Configuration
DB_PATH = "db/chroma_parks"
OUTPUT_DIR = "output"
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.2:1b"
SYSTEM_PROMPT = """You are a friendly Fairfax County parks guide helping families find parks.
Always recommend at least 2 parks and compare their amenities.
For each park, mention the name, key amenities, and what makes it a good fit.
If one park is clearly better for the request, explain why but still offer an alternative."""

def get_retriever():
    """Load ChromaDB and return a retriever."""
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    chroma_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    return chroma_db.as_retriever()

def create_chain(retriever):
    """Create a RAG chain with prompt template."""
    llm = OllamaLLM(model=LLM_MODEL)
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", "Parks data:\n{context}\n\nQuestion: {question}")
    ])
    def format_docs(docs):
        return "\n\n---\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt_template
        | llm
        | StrOutputParser()
    )
    return chain

def log_interaction(question, answer, response_time):
    """Log each Q&A interaction to a JSON file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now()
    filename = f"{OUTPUT_DIR}/session_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"

    # Check if session file exists, append to it
    session_file = None
    for f in os.listdir(OUTPUT_DIR):
        if f.startswith("session_") and f.endswith(".json"):
            # Use most recent session file from today
            if timestamp.strftime('%Y%m%d') in f:
                session_file = f"{OUTPUT_DIR}/{f}"
                break

    if session_file and os.path.exists(session_file):
        with open(session_file, 'r') as f:
            data = json.load(f)
    else:
        session_file = filename
        data = {
            "session_start": timestamp.isoformat(),
            "config": {
                "embedding_model": EMBEDDING_MODEL,
                "llm_model": LLM_MODEL,
                "system_prompt": SYSTEM_PROMPT,
                "db_path": DB_PATH
            },
            "interactions": []
        }

    data["interactions"].append({
        "timestamp": timestamp.isoformat(),
        "question": question,
        "answer": answer,
        "response_time_seconds": round(response_time, 2)
    })

    with open(session_file, 'w') as f:
        json.dump(data, f, indent=2)

    return session_file

def main():
    print("\n" + "="*50)
    print("  Welcome to Fairfax County Parks Finder!")
    print("="*50)
    print("\nI can help you find the perfect park for your family.")
    print("Try asking things like:")
    print("  - Which parks have playgrounds for toddlers?")
    print("  - Where can I take my dog?")
    print("  - What parks have a carousel?")
    print("\nType 'quit' to exit.\n")

    retriever = get_retriever()
    chain = create_chain(retriever)

    # Interactive loop
    import time
    while True:
        question = input("You: ")
        if question.lower() == 'quit':
            print("\nThanks for using Parks Finder. Have a great day!")
            break

        print("\nSearching parks...\n")
        start_time = time.time()
        result = chain.invoke(question)
        response_time = time.time() - start_time

        print(f"Parks Guide: {result}\n")
        print(f"(Response time: {response_time:.1f}s)")

        # Log to file
        log_file = log_interaction(question, result, response_time)
        print(f"(Logged to: {log_file})\n")

if __name__ == "__main__":
    main()
