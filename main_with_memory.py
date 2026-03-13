"""
Parks Finder RAG with Conversation Memory

Supports follow-up questions like:
- "What about the first one?"
- "Does it have restrooms?"
- "Which is closer to me?"
"""
import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

# Configuration
DB_PATH = "db/chroma_parks"
OUTPUT_DIR = "output"
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.2:1b"
MAX_HISTORY = 6  # Keep last 6 messages (3 exchanges)

SYSTEM_PROMPT = """You are a friendly Fairfax County parks guide helping families find parks.
Always recommend at least 2 parks and compare their amenities.
For each park, mention the name, key amenities, and what makes it a good fit.
If one park is clearly better for the request, explain why but still offer an alternative.

When the user asks follow-up questions about parks you previously mentioned,
refer back to those parks by name and provide the requested details."""


class ConversationMemory:
    """Manages conversation history for context-aware responses."""

    def __init__(self, max_messages: int = MAX_HISTORY):
        self.max_messages = max_messages
        self.messages: List[Dict[str, str]] = []

    def add_user_message(self, content: str):
        """Add a user message to history."""
        self.messages.append({"role": "user", "content": content})
        self._trim()

    def add_ai_message(self, content: str):
        """Add an AI response to history."""
        self.messages.append({"role": "assistant", "content": content})
        self._trim()

    def _trim(self):
        """Keep only the last N messages."""
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_history_string(self) -> str:
        """Format history as a string for the prompt."""
        if not self.messages:
            return "No previous conversation."

        history = []
        for msg in self.messages[:-1]:  # Exclude current question
            role = "User" if msg["role"] == "user" else "Assistant"
            history.append(f"{role}: {msg['content']}")

        return "\n".join(history)

    def get_langchain_messages(self):
        """Convert to LangChain message format."""
        lc_messages = []
        for msg in self.messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            else:
                lc_messages.append(AIMessage(content=msg["content"]))
        return lc_messages

    def clear(self):
        """Clear conversation history."""
        self.messages = []

    def to_dict(self) -> List[Dict[str, str]]:
        """Export for JSON serialization."""
        return self.messages.copy()


def get_retriever():
    """Load ChromaDB and return a retriever."""
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    chroma_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    return chroma_db.as_retriever(search_kwargs={"k": 4})


def create_chain_with_memory(retriever):
    """Create a RAG chain that includes conversation history."""
    llm = OllamaLLM(model=LLM_MODEL)

    # Prompt that includes conversation history
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", """Previous conversation:
{history}

Relevant parks data:
{context}

Current question: {question}

Provide a helpful response. If this is a follow-up question about previously mentioned parks,
reference them by name and answer specifically about those parks.""")
    ])

    def format_docs(docs):
        return "\n\n---\n\n".join(doc.page_content for doc in docs)

    # Chain that processes context and history
    chain = (
        {
            "context": lambda x: format_docs(retriever.invoke(x["question"])),
            "history": lambda x: x["history"],
            "question": lambda x: x["question"]
        }
        | prompt_template
        | llm
        | StrOutputParser()
    )

    return chain


def log_interaction(question: str, answer: str, response_time: float,
                   memory: ConversationMemory) -> str:
    """Log interaction with full conversation context."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now()
    filename = f"{OUTPUT_DIR}/session_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"

    # Find existing session file from today
    session_file = None
    for f in os.listdir(OUTPUT_DIR):
        if f.startswith("session_") and f.endswith(".json"):
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
                "db_path": DB_PATH,
                "memory_enabled": True,
                "max_history": MAX_HISTORY
            },
            "interactions": []
        }

    data["interactions"].append({
        "timestamp": timestamp.isoformat(),
        "question": question,
        "answer": answer,
        "response_time_seconds": round(response_time, 2),
        "conversation_context": memory.to_dict()
    })

    with open(session_file, 'w') as f:
        json.dump(data, f, indent=2)

    return session_file


def main():
    print("\n" + "=" * 50)
    print("  Fairfax County Parks Finder")
    print("  (with Conversation Memory)")
    print("=" * 50)
    print("\nI can help you find the perfect park for your family.")
    print("I remember our conversation, so you can ask follow-ups like:")
    print("  - 'What about the first one?'")
    print("  - 'Does it have restrooms?'")
    print("  - 'Which is better for toddlers?'")
    print("\nCommands:")
    print("  'clear' - Start a new conversation")
    print("  'quit'  - Exit")
    print()

    retriever = get_retriever()
    chain = create_chain_with_memory(retriever)
    memory = ConversationMemory()

    while True:
        question = input("You: ").strip()

        if not question:
            continue

        if question.lower() == 'quit':
            print("\nThanks for using Parks Finder. Have a great day!")
            break

        if question.lower() == 'clear':
            memory.clear()
            print("\n[Conversation cleared. Starting fresh!]\n")
            continue

        # Add question to memory before processing
        memory.add_user_message(question)

        print("\nSearching parks...\n")
        start_time = time.time()

        # Invoke chain with history
        result = chain.invoke({
            "question": question,
            "history": memory.get_history_string()
        })

        response_time = time.time() - start_time

        # Add response to memory
        memory.add_ai_message(result)

        print(f"Parks Guide: {result}\n")
        print(f"(Response time: {response_time:.1f}s)")

        # Log with memory context
        log_file = log_interaction(question, result, response_time, memory)
        print(f"(Logged to: {log_file})\n")


if __name__ == "__main__":
    main()
