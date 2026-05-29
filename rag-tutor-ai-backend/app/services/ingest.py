import re
from io import BytesIO

import fitz
import asyncio
from concurrent.futures import ThreadPoolExecutor

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

        existing_files = vector_db.get_existing_files()
    
        pdfs_to_process = [pdf for pdf in pdf_objects if pdf.key not in existing_files]
        print(f"Need to process {len(pdfs_to_process)} new PDFs.")

        def process_single_pdf(pdf):
            print(f"Processing PDF: {pdf.key}")

            try:
                pdf_bytes = s3_storage_service.download_pdf_bytes(pdf.key)

                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                pages = []

                for page_num, page in enumerate(doc):
                    text = page.get_text()
                    cleaned_text = self.clean_text(text)

                    if len(cleaned_text) > 0:
                        pages.append(Document(
                            page_content = cleaned_text,
                            metadata={
                                'source_file': pdf.key,
                                'source_name': pdf.filename,
                                'page': page_num
                            }
                        ))
                doc.close()
                return pdf.filename, pages
            except Exception as e:
                print(f"Error processing {pdf.filename}: {str(e)}")
                return pdf.filename, []
            
        if pdfs_to_process:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=5) as executor:
                tasks = [
                    loop.run_in_executor(executor, process_single_pdf, pdf)
                    for pdf in pdfs_to_process
                ]
                results = await asyncio.gather(*tasks)

            for filename, pages in results:
                if pages:
                    all_pages.extend(pages)
                    processed_files.append(filename)

        if all_pages:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=ingestion_settings.CHUNK_SIZE,
                chunk_overlap=ingestion_settings.CHUNK_OVERLAP
            )
            chunks = splitter.split_documents(all_pages)

            batch_size = 100
            print(f"Uploading {len(chunks)} chunks in batches of {batch_size}...")

            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                vector_db.add_documents(batch)
                print(f"Uploaded batch {i // batch_size + 1}...")

        return processed_files, len(all_pages)
            

        # for pdf in pdf_objects:
        #     print(f"Processing PDF: {pdf.key}")
            
        #     if vector_db.check_file_exists(pdf.key):
        #         print(f"PDF already in vector DB: {pdf.filename}")
        #         continue

        #     try:
        #         # Stream PDF directly from S3 into memory
        #         pdf_bytes = s3_storage_service.download_pdf_bytes(pdf.key)
        #         pdf_file = BytesIO(pdf_bytes)
                
        #         # Extract pages using pypdf
        #         reader = PdfReader(pdf_file)
        #         pages = []
                
        #         for page_num, page in enumerate(reader.pages):
        #             text = page.extract_text()
        #             cleaned_text = self.clean_text(text)
                    
        #             doc = Document(
        #                 page_content=cleaned_text,
        #                 metadata={
        #                     'source_file': pdf.key,
        #                     'source_name': pdf.filename,
        #                     'page': page_num
        #                 }
        #             )
        #             pages.append(doc)

        #         all_pages.extend(pages)
        #         processed_files.append(pdf.filename)
        #         print(f"Successfully loaded {len(pages)} pages from {pdf.filename}")
        #     except Exception as e:
        #         print(f"Error processing {pdf.filename}: {str(e)}")

        # if all_pages:
        #     splitter = RecursiveCharacterTextSplitter(
        #         chunk_size=ingestion_settings.CHUNK_SIZE,
        #         chunk_overlap=ingestion_settings.CHUNK_OVERLAP
        #     )
        #     chunks = splitter.split_documents(all_pages)
        #     vector_db.add_documents(chunks)
        #     print(f"Added {len(chunks)} chunks to vector database")

        # return processed_files, len(all_pages)


ingest_service = IngestService()
