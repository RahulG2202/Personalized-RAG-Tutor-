import asyncio
import re
from concurrent.futures import ThreadPoolExecutor

import fitz
from langchain.schema import Document
from langchain_experimental.text_splitter import SemanticChunker

from app.db.database import vector_db
from app.services.s3_storage import s3_storage_service


class IngestService:
    SEMANTIC_BREAKPOINT_PERCENTILE = 70
    SEMANTIC_PAGE_BATCH_SIZE = 10
    SHORT_PAGE_CHAR_THRESHOLD = 600
    PREVIEW_CHUNK_COUNT = 10

    def clean_text(self, text):
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'Page \d+ of \d+', '', text)

        return text.strip()

    def semantic_chunk_pages(self, page_documents):
        print(f"Starting semantic chunking for {len(page_documents)} pages...")
        splitter = SemanticChunker(
            embeddings=vector_db.get_embeddings(),
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=self.SEMANTIC_BREAKPOINT_PERCENTILE,
            min_chunk_size=450,
        )
        print("Semantic chunking complete. Generating chunks...")
        chunks = []

        for start in range(0, len(page_documents), self.SEMANTIC_PAGE_BATCH_SIZE):
            page_batch = page_documents[start:start + self.SEMANTIC_PAGE_BATCH_SIZE]
            semantic_page_documents = [
                page_document
                for page_document in page_batch
                if len(page_document.page_content) >= self.SHORT_PAGE_CHAR_THRESHOLD
            ]
            page_chunks_by_key = {
                self.page_chunk_key(page_document.metadata): [
                    self.short_page_chunk(page_document)
                ]
                for page_document in page_batch
                if len(page_document.page_content) < self.SHORT_PAGE_CHAR_THRESHOLD
            }

            if semantic_page_documents:
                page_chunks = splitter.split_documents(semantic_page_documents)

                for chunk in page_chunks:
                    chunk.metadata = dict(chunk.metadata or {})
                    chunk.metadata["chunking_strategy"] = "langchain_page_semantic"
                    page_key = self.page_chunk_key(chunk.metadata)
                    page_chunks_by_key.setdefault(page_key, []).append(chunk)

            for page_document in page_batch:
                page_key = self.page_chunk_key(page_document.metadata)
                page_chunks = page_chunks_by_key.get(page_key, [])
                page_chunk_count = len(page_chunks)

                for index, chunk in enumerate(page_chunks):
                    chunk.metadata = dict(chunk.metadata or {})
                    chunk.metadata.update({
                        "page_chunk_index": index,
                        "page_chunk_count": page_chunk_count
                    })

                chunks.extend(page_chunks)
        print(f"Generated {len(chunks)} semantic chunks from {len(page_documents)} pages.")

        return chunks

    def short_page_chunk(self, page_document):
        metadata = dict(page_document.metadata or {})
        metadata["chunking_strategy"] = "short_page_skip"

        return Document(
            page_content=page_document.page_content,
            metadata=metadata
        )

    def page_chunk_key(self, metadata):
        return (
            metadata.get("source_file"),
            metadata.get("source_name"),
            metadata.get("page")
        )

    def print_top_chunks(self, chunks):
        if not chunks:
            print("No semantic chunks generated.")
            return

        print(f"Top {min(self.PREVIEW_CHUNK_COUNT, len(chunks))} semantic chunks:")

        for index, chunk in enumerate(chunks[:self.PREVIEW_CHUNK_COUNT], start=1):
            metadata = chunk.metadata or {}
            source_name = (
                metadata.get("source_name")
                or metadata.get("source_file")
                or "unknown"
            )
            page = metadata.get("page")
            page_label = page + 1 if isinstance(page, int) else page
            preview = self.clean_text(chunk.page_content)

            if len(preview) > 500:
                preview = f"{preview[:500]}..."

            print(
                f"{index}. source={source_name} "
                f"page={page_label} "
                f"chunk={metadata.get('page_chunk_index', 0) + 1}/"
                f"{metadata.get('page_chunk_count', 1)} "
                f"chars={len(chunk.page_content)}"
            )
            print(preview)

    async def run_ingestion(self, reset_db: bool = False):
        if reset_db:
            vector_db.reset_db()

        all_pages = []
        processed_files = []
        print("Starting ingestion process...")

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
                            page_content=cleaned_text,
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
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor(max_workers=5) as executor:
                tasks = [
                    loop.run_in_executor(executor, process_single_pdf, pdf)
                    for pdf in pdfs_to_process
                ]
                print(f"Processing {len(tasks)} PDFs concurrently...")
                results = await asyncio.gather(*tasks)
                print("PDF processing complete.")
            for filename, pages in results:
                if pages:
                    all_pages.extend(pages)
                    processed_files.append(filename)
                print(f"Processed PDF: {filename}")

        if all_pages:
            print(f"Total pages to be chunked: {len(all_pages)}")
            chunks = self.semantic_chunk_pages(all_pages)
            self.print_top_chunks(chunks)

            # batch_size = 100
            # print(f"Uploading {len(chunks)} chunks in batches of {batch_size}...")

            # vector_db.add_documents(chunks, batch_size=batch_size)

        return processed_files, len(all_pages)


ingest_service = IngestService()
