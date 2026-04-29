from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import warnings
from dotenv import load_dotenv

# 1. Silence the messy errors
os.environ['ANONYMIZED_TELEMETRY'] = 'False'
warnings.filterwarnings("ignore", category=FutureWarning)


# 2. Setup
load_dotenv()
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Connect to DB
if not os.path.exists("./chroma_db"):
    print("Error: The folder 'chroma_db' does not exist. Run ingest.py first!")
else:
    vector_db = Chroma(persist_directory="./chroma_db",
                       embedding_function=embeddings)

    # 3. Fetch Data
    # .get() retrieves all IDs and Metadata from the database
    data = vector_db.get()

    if data and data['metadatas']:
        # We use a set comprehension to get unique filenames
        sources = {m['source_file']
                   for m in data['metadatas'] if 'source_file' in m}

        if sources:
            print(
                f"✅ The Brain currently contains these {len(sources)} files:")
            for s in sources:
                print(f"   - {s}")
        else:
            print("⚠️ The database exists, but no 'source_file' metadata was found.")
    else:
        print("❌ The database is currently empty.")
