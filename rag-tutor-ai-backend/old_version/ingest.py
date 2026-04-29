import os
import shutil
import re
import sys
import fitz
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv()


def verify_pdf(input_path):
    try:
        loader = PyPDFLoader(input_path)
        pages = loader.load()

        if not pages:
            return False

        test_limit = min(len(pages), 10)
        for i in range(test_limit):
            if len(pages[i].page_content.strip()) != 0:
                return True
        return False
    except Exception:
        return False


def clean_and_compress_text(text):
    """
    This function acts as our compressor. 
    It removes noise that confuses AI models.
    """
    # 1. Remove multiple newlines (Compresses empty space)
    text = re.sub(r'\n+', ' ', text)

    # 2. Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # 3. Remove weird symbols or page number patterns (Optional)
    # Example: Removing things like "--- Page 1 ---"
    text = re.sub(r'Page \d+ of \d+', '', text)

    # 4. Strip leading/trailing whitespace
    return text.strip()


def compress_pdf(input_path, output_path):
    try:
        doc = fitz.open(input_path)
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()
    except Exception as e:
        print(f"Could not compress {input_path}: {e}")


def ingest_data(reset_db=False):
    data_dir = "data"
    temp_dir = "temp_compressed"
    db_path = "./chroma_db"
    all_pages = []
    existing_files = set()

    # Initialize embeddings early (needed for existing DB connection)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    if reset_db and os.path.exists(db_path):
        shutil.rmtree(db_path)
        print("--- RESET: Old database deleted ---")

    if not os.path.exists(data_dir):
        print(f"Error: Folder {data_dir} not found")
        return

    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    if os.path.exists(db_path):
        # Connect to existing DB
        vector_db = Chroma(persist_directory=db_path,
                           embedding_function=embeddings)
        # Fetch all metadata from the database
        data = vector_db.get()
        # Extract unique filenames from the metadata
        existing_files = {m['source_file']
                          for m in data['metadatas'] if 'source_file' in m}
        print(f"Files already in database: {existing_files}")

    print(f"Scanning for PDFs in {data_dir}...")
    files_in_folder = [f for f in os.listdir(data_dir) if f.endswith(".pdf")]
    print(f"Found {len(files_in_folder)} PDFs in folder: {files_in_folder}")

    for filename in files_in_folder:
        if filename in existing_files:
            print(f">>> Skipping {filename}: Already exists in database.")
            continue

        pdf_path = os.path.join(data_dir, filename)

        if not verify_pdf(pdf_path):
            print(
                f"❌ Skipping {filename}: No readable text (might be a scanned image).")
            continue

        compressed_file = os.path.join(temp_dir, filename)
        print(f"--- Processing: {filename} ---")

        try:
            compress_pdf(pdf_path, compressed_file)
            loader = PyPDFLoader(compressed_file)
            pages = loader.load()

            for page in pages:
                page.page_content = clean_and_compress_text(page.page_content)
                page.metadata['source_file'] = filename

            all_pages.extend(pages)
            print(f"Successfully extracted {len(pages)} pages from {filename}")
        except Exception as e:
            print(f"ERROR processing {filename}: {str(e)}")

    if not all_pages:
        print("No PDF files found in the directory")
        return

    # Chunking: Split the text into manageable pieces
    print(f"Splitting total of {len(all_pages)} pages into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=100)
    # Create Embeddings and save to Vector Database
    chunks = text_splitter.split_documents(all_pages)

    # Use from_documents for fresh DB, or add_documents for existing DB
    if os.path.exists(db_path) and not reset_db:
        # Incremental: add to existing database
        print("Adding to existing database...")
        vector_db = Chroma(
            persist_directory=db_path,
            embedding_function=embeddings
        )
        vector_db.add_documents(documents=chunks)
        print(f"Added {len(chunks)} new chunks to the database")
    else:
        # Create new database
        Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=db_path
        )
        print(f"Created new database with {len(chunks)} chunks")

    # Cleanup temp folder (Optional - remove if you want to keep compressed PDFs)
    # shutil.rmtree(temp_dir)

    print("Done! Your library is ready.")


if __name__ == "__main__":
    reset_db = "--reset" in sys.argv
    if reset_db:
        print("Running in RESET mode - old database will be cleared")
    else:
        print("Running in INCREMENTAL mode - new PDFs will be added to existing database")
        print("Use 'python ingest.py --reset' to clear the database first")
    ingest_data(reset_db=reset_db)
