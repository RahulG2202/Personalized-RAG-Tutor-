import os
import re
import fitz
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import ingestion_settings
from app.db.database import vector_db


class IngestService:
    def verify_pdf(self, input_path):
        try:
            loader = PyPDFLoader(input_path)
            pages = loader.load()
            if not pages:
                return False
            contents = False
            for i in range(min(len(pages), 10)):
                if len(pages[i].page_content.strip()) != 0:
                    contents = True
            return contents
        except Exception:
            return False

    def clean_text(slef, text):
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'Page \d+ of \d+', '', text)

        return text.strip()

    def compress_pdf(input_path, output_path):
        try:
            doc = fitz.open(input_path)
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()
        except Exception as e:
            print(f"Could not compress {input_path}: {e}")

    async def run_ingestion(self, reset_db: bool = False):
        if reset_db:
            vector_db.reset_db()

        existing_files = vector_db.get_existing_files()
        all_pages = []
        processed_files = []

        try:
            if not os.path.exists(ingestion_settings.DATA_DIR):
                raise FileNotFoundError("Data file does not exist")
        except FileNotFoundError as e:
            print(e)

        if not os.path.exists(ingestion_settings.TEMP_DIR):
            os.makedirs(ingestion_settings.TEMP_DIR)

        files_in_folders = [f for f in os.listdir(
            ingestion_settings.DATA_DIR) if f.endswith(".pdf")]
        print(
            f"Found {len(files_in_folders)} PDFs in foldeer: {files_in_folders}")

        for filename in os.listdir(ingestion_settings.DATA_DIR):
            if filename.endswith('.pdf') and filename not in existing_files:
                pdf_path = os.path.join(ingestion_settings.DATA_DIR, filename)

                if not self.verify_pdf(pdf_path):
                    continue

                compressed_path = os.path.join(
                    ingestion_settings.TEMP_DIR, filename)
                self.compress_pdf(pdf_path, compressed_path)

                loader = PyPDFLoader(compressed_path)
                pages = loader.load()

                for page in pages:
                    page.page_content = self.clean_text(page.page_content)
                    page.metadata['source_file'] = filename

                all_pages.extend(pages)
                processed_files.append(filename)

        if all_pages:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=ingestion_settings.CHUNK_SIZE,
                chunk_overlap=ingestion_settings.CHUNK_OVERLAP
            )
            chunks = splitter.split_documents(all_pages)
            vector_db.add_documents(chunks)

        return processed_files, len(all_pages)


ingest_service = IngestService()
