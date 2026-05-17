import chromadb
import os
import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

# Ensure the directory for chroma data exists
db_path = os.path.join(os.getcwd(), "chroma_db")
if not os.path.exists(db_path):
    os.makedirs(db_path)

client = chromadb.PersistentClient(path=db_path)
collection = client.get_or_create_collection(settings.CHROMA_COLLECTION_NAME)

def add_to_collection(content: str, metadata: dict = None):
    doc_id = str(uuid.uuid4())
    collection.add(
        documents=[content],
        metadatas=[metadata] if metadata else [{}],
        ids=[doc_id]
    )
    return doc_id

def upsert_to_collection(doc_id: str, content: str, metadata: dict = None):
    collection.upsert(
        documents=[content],
        metadatas=[metadata] if metadata else [{}],
        ids=[doc_id]
    )
    return doc_id

def delete_from_collection(doc_id: str):
    try:
        collection.delete(ids=[doc_id])
    except Exception as e:
        print(f"ChromaDB Error: Failed to delete {doc_id}: {e}")

def query_collection(query_text: str, n_results: int = 5, where: dict = None):
    kwargs = {
        "query_texts": [query_text],
        "n_results": n_results
    }
    if where:
        kwargs["where"] = where
    results = collection.query(**kwargs)
    return results

def load_default_documents():
    # Only load if the collection is empty
    if collection.count() > 0:
        print("ChromaDB: Collection already has documents. Skipping default load.")
        return

    # Initialize text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        length_function=len,
    )

    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(current_dir)
    context_dir = os.path.join(app_dir, "context")
    
    if not os.path.exists(context_dir):
        print(f"ChromaDB Warning: Context directory not found at {context_dir}")
        return

    print(f"ChromaDB: Loading and chunking default documents from {context_dir}...")
    for filename in os.listdir(context_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(context_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.strip():
                        # Split content into chunks
                        chunks = text_splitter.split_text(content)
                        for i, chunk in enumerate(chunks):
                            add_to_collection(chunk, {"source": filename, "chunk": i})
                        print(f"ChromaDB: Loaded {filename} ({len(chunks)} chunks)")
            except Exception as e:
                print(f"ChromaDB Error: Failed to load {filename}: {e}")

