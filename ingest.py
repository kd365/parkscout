import json
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

# Configuration
DATA_FILE = "source_data/fairfax_parks.json"
DB_PATH = "db/chroma_parks"

def load_parks():
    """Load park data from JSON file."""
    # TODO: Open and read the JSON file
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_documents(parks):
    """Convert each park dict into a LangChain Document."""
    documents = []
    for park in parks:
        # TODO: Create a text string from park data
        amenities = park.get('amenities', {})
        
        text = f"Park: {park.get('park_name', '')}\n"
        text += f"Description: {park.get('description', '')}\n"
        text += f"Address: {park.get('address', '')}\n"
        text += f"Classification: {park.get('classification', '')}\n"
        
        # Add amenities (searchable terms!)
        text += f"Playground: {amenities.get('playground', 'No')}\n"
        text += f"Restrooms: {amenities.get('restrooms', 'No')}\n"
        text += f"Picnic Shelters: {amenities.get('picnic_shelters', 'No')}\n"
        text += f"Trails: {amenities.get('trails', 'None')}\n"
        text += f"Water Activities: {amenities.get('water_activities', 'None')}\n"
        text += f"Dog Friendly: {amenities.get('dog_friendly', 'Unknown')}\n"

        # Special features as comma-separated list
        special = amenities.get('special_features', [])
        if special:
            text += f"Special Features: {', '.join(special)}\n"
        
        # Best for tags (great for semantic search!)
        best_for = park.get('best_for', [])
        if best_for:
            text += f"Best For: {', '.join(best_for)}\n"
        

        # TODO: Create Document with page_content and metadata
        documents.append(Document(
            page_content=text,
            metadata={"park_name": park.get("park_name", "")}
        ))
    return documents

def main():
    print("Loading Fairfax County Parks data...")
    parks = load_parks()
    print(f"Found {len(parks)} parks")
    
    # TODO: Create documents

    documents = create_documents(parks)
    print(f"Created {len(documents)} documents")

    # TODO: Initialize OllamaEmbeddings with nomic-embed-text
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    print("Initialized Ollama embeddings")
    # TODO: Create ChromaDB and persist
    chroma_db = Chroma.from_documents(
        documents,
        embedding=embeddings,
        persist_directory=DB_PATH
    )
    print("Done! Database ready.")

if __name__ == "__main__":
    main()