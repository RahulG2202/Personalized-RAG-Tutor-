import os
import warnings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

os.environ['ANONYMIZED_TELEMETRY'] = "False"
warnings.filterwarnings("ignore", category=FutureWarning)

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory="./chroma_db",
                   embedding_function=embeddings)

data = vector_db.get()

print(f"Total Chunks in Database: {len(data['ids'])}")

stats = {}

for metadata in data['metadatas']:
    file = metadata.get('source_file', 'Unknown Source')
    stats[file] = stats.get(file, 0) + 1

print("Breakdown by FIle")
for file, count in stats.items():
    print(F"FIle: {file} | Chunks: {count}")


if len(data['ids']) > 0:
    print("\n--- Sample Content from first chunk ---")
    print(data['documents'][0][:200])
