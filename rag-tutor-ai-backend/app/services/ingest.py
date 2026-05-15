import re
from io import BytesIO
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document
from pypdf import PdfReader
from app.core.config import ingestion_settings
from app.db.database import vector_db
from app.services.s3_storage import s3_storage_service


class IngestService:
    def clean_text(self, text):
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'Page \d+ of \d+', '', text)

        return text.strip()

    async def run_ingestion(self, reset_db: bool = False):
        if reset_db:
            vector_db.reset_db()

        all_pages = []
        processed_files = []

        pdf_objects = s3_storage_service.list_pdfs()
        print(f"Found {len(pdf_objects)} PDFs in S3: {[pdf.filename for pdf in pdf_objects]}")

        for pdf in pdf_objects:
            print(f"Processing PDF: {pdf.key}")
            
            if vector_db.check_file_exists(pdf.key):
                print(f"PDF already in vector DB: {pdf.filename}")
                continue

            try:
                # Stream PDF directly from S3 into memory
                pdf_bytes = s3_storage_service.download_pdf_bytes(pdf.key)
                pdf_file = BytesIO(pdf_bytes)
                
                # Extract pages using pypdf
                reader = PdfReader(pdf_file)
                pages = []
                
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    cleaned_text = self.clean_text(text)
                    
                    doc = Document(
                        page_content=cleaned_text,
                        metadata={
                            'source_file': pdf.key,
                            'source_name': pdf.filename,
                            'page': page_num
                        }
                    )
                    pages.append(doc)

                all_pages.extend(pages)
                processed_files.append(pdf.filename)
                print(f"Successfully loaded {len(pages)} pages from {pdf.filename}")
            except Exception as e:
                print(f"Error processing {pdf.filename}: {str(e)}")

        if all_pages:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=ingestion_settings.CHUNK_SIZE,
                chunk_overlap=ingestion_settings.CHUNK_OVERLAP
            )
            chunks = splitter.split_documents(all_pages)
            vector_db.add_documents(chunks)
            print(f"Added {len(chunks)} chunks to vector database")

        return processed_files, len(all_pages)


ingest_service = IngestService()
