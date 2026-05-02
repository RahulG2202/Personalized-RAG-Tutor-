from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from app.services.ingest import ingest_service
from app.services.s3_storage import s3_storage_service
from langchain_community.document_loaders import PyPDFLoader
from io import BytesIO
import fitz
router = APIRouter()


@router.get("/upload-pdf")
async def upload_pdf_help():
    return {
        "status": "Ready",
        "message": "Send a POST multipart/form-data request with a PDF field named 'file'.",
        "field_name": "file"
    }

def verify_pdf(file_data):
    try:
        doc = fitz.open(stream=file_data, filetype="pdf")
        
        # Check if PDF has pages
        if doc.page_count == 0:
            print("No pages found in PDF")
            doc.close()
            return False, None
        
        # Check if at least one page has content
        has_content = False
        for page_num in range(min(doc.page_count, 10)):
            page = doc[page_num]
            text = page.get_text().strip()
            if len(text) > 0:
                print(f"Found content in page {page_num}")
                has_content = True
                break
        
        if not has_content:
            print("No text content found in first 10 pages")
            doc.close()
            return False, None
        
        # Compress the PDF
        compressed_pdf = doc.tobytes(deflate=True, garbage=1, linear=False)
        doc.close()
        
        print("PDF verified and compressed successfully")
        return True, compressed_pdf
        
    except Exception as e:
        print(f"Uploaded PDF cannot be scanned: {str(e)}")
        return False, None


@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Read the file data
        file_data = await file.read()
        
        # Verify PDF and compress it
        is_valid, compressed_data = await run_in_threadpool(verify_pdf, file_data)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="PDF file is not readable or contains no text content"
            )
        
        del file_data
        
        # Create a BytesIO object with compressed data
        compressed_file = BytesIO(compressed_data)

        print(f"PDF Verified and Compressed {compressed_file}")
        
        uploaded = await run_in_threadpool(
            s3_storage_service.upload_pdf,
            compressed_file,
            file.filename or "material.pdf"
        )
        return JSONResponse(
            status_code=201,
            content={
                "status": "Success",
                "message": "PDF uploaded to S3.",
                "filename": uploaded.filename,
                "size": uploaded.size,
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {e}")
    finally:
        await file.close()


@router.get("/s3-pdfs")
async def list_s3_pdfs():
    try:
        pdfs = await run_in_threadpool(s3_storage_service.list_pdfs)
        return {
            "status": "Success",
            "count": len(pdfs),
            "files": [
                {
                    "filename": pdf.filename,
                    "s3_key": pdf.key
                }
                for pdf in pdfs
            ]
        }
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 list failed: {e}")


@router.post("/run-ingestion")
async def run_ingestion(reset_db: bool = Query(False)):
    try:
        files, page_count = await ingest_service.run_ingestion(reset_db=reset_db)
        return {
            "status": "Success",
            "files_processed": files,
            "total_pages_extracted": page_count
        }
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
