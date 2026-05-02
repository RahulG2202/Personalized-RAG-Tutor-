import os
import re
import fitz
from pathlib import Path
from uuid import uuid4
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import ingestion_settings
from app.db.database import vector_db
from app.services.s3_storage import s3_storage_service


class IngestService:
    def clean_text(self, text):
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'Page \d+ of \d+', '', text)

        return text.strip()

    def compress_pdf(self, input_path, output_path):
        try:
            doc = fitz.open(input_path)
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()
        except Exception as e:
            print(f"Could not compress {input_path}: {e}")

    def build_temp_paths(self, filename):
        stem = Path(filename).stem
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._")
        safe_stem = safe_stem[:80] or "material"
        token = uuid4().hex

        source_path = os.path.join(
            ingestion_settings.TEMP_DIR,
            f"{token}_{safe_stem}.pdf"
        )
        compressed_path = os.path.join(
            ingestion_settings.TEMP_DIR,
            f"{token}_{safe_stem}_compressed.pdf"
        )

        return source_path, compressed_path

    async def run_ingestion(self, reset_db: bool = False):
        if reset_db:
            vector_db.reset_db()

        existing_files = vector_db.get_existing_files()
        all_pages = []
        processed_files = []

        if not os.path.exists(ingestion_settings.TEMP_DIR):
            os.makedirs(ingestion_settings.TEMP_DIR)

        pdf_objects = s3_storage_service.list_pdfs()
        print(f"Found {len(pdf_objects)} PDFs in S3: {[pdf.filename for pdf in pdf_objects]}")

        for pdf in pdf_objects:
            if pdf.key in existing_files:
                continue

            pdf_path, compressed_path = self.build_temp_paths(pdf.filename)

            try:
                s3_storage_service.download_pdf(pdf.key, pdf_path)

                self.compress_pdf(pdf_path, compressed_path)
                load_path = compressed_path if os.path.exists(compressed_path) else pdf_path

                loader = PyPDFLoader(load_path)
                pages = loader.load()

                for page in pages:
                    page.page_content = self.clean_text(page.page_content)
                    page.metadata['source_file'] = pdf.key
                    page.metadata['source_name'] = pdf.filename

                all_pages.extend(pages)
                processed_files.append(pdf.filename)
            finally:
                for path in (pdf_path, compressed_path):
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except OSError:
                        pass

        if all_pages:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=ingestion_settings.CHUNK_SIZE,
                chunk_overlap=ingestion_settings.CHUNK_OVERLAP
            )
            chunks = splitter.split_documents(all_pages)
            vector_db.add_documents(chunks)

        return processed_files, len(all_pages)


ingest_service = IngestService()
