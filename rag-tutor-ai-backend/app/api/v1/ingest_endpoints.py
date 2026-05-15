from fastapi import APIRouter, File, HTTPException, Query, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from app.services.ingest import ingest_service
from app.services.s3_storage import s3_storage_service
import fitz
from typing import List
router = APIRouter()

def process_pdf_pipeline(file, filename):
    print("Inside PDF background pipeline")

    try:
        doc = fitz.open(stream=file, filetype="pdf")
        
        for page in doc:
            page.clean_contents()

        from io import BytesIO
        compressed_buffer = BytesIO()
        doc.save(compressed_buffer, deflate=True, garbage=4, clean=True)
        compressed_pdf = compressed_buffer.getvalue()
        doc.close()

        print("Ready to upload to S3")

        pdf_file = BytesIO(compressed_pdf)
        uploaded = s3_storage_service.upload_pdf(pdf_file, filename or "material.pdf")
        print(f"Successfully uploaded {filename} to S3")
    except Exception as e:
        print(f"Faild to upload to S3: {str(e)}")



def verify_pdf(file_data):
    try:
        doc = fitz.open(stream=file_data, filetype="pdf")
        
        if doc.page_count == 0:
            print("No pages found in PDF")
            doc.close()
            return False
        
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
            return False
        
        return True
        
    except Exception as e:
        print(f"Uploaded PDF cannot be scanned: {str(e)}")
        return False


@router.post("/upload-multiple-pdf")
async def upload_multiple_pdfs(background_tasks: BackgroundTasks, files: List[UploadFile] = File(None)):
    # Validate files were provided
    if not files:
        raise HTTPException(status_code=400, detail="No files provided. Send files in 'files' field")
    
    uploaded_pdf = []
    failed_files = []

    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 files allowed at once")
    
    for file in files:
        filename = file.filename
        try:
            if not filename.endswith('.pdf'):
                failed_files.append({
                    "filename": filename,
                    "status": "This file format is not supported"
                })
                continue
            
            # Read the file data
            file_data = await file.read()
        
            # Verify PDF
            is_valid = await run_in_threadpool(verify_pdf, file_data)
            if not is_valid:
                failed_files.append({
                    "filename": filename,
                    "status": "This PDF cannot be scanned"
                })
                continue
            
            background_tasks.add_task(process_pdf_pipeline, file_data, filename)
            uploaded_pdf.append({
                "filename": filename,
                "status": "Accepted for processing"
            })

            del file_data
        except ValueError as e:
            failed_files.append({
                "filename": filename,
                "error": str(e)
            })
        except RuntimeError as e:
            failed_files.append({
                "filename": filename,
                "error": str(e)
            })
        except Exception as e:
            failed_files.append({
                "filename": filename,
                "error": f"S3 upload failed: {e}"
            })
        finally:
            await file.close()

    if not uploaded_pdf and failed_files:
        raise HTTPException(status_code=400, detail={
            "message": "No PDFS were uploaded",
            "failed_files": failed_files
        })
    
    status_code = 207 if failed_files else 201
    status = "Partial Success" if failed_files else "Success"

    return JSONResponse(
        status_code= status_code,
        content={
            "status": status,
            "message": f"Uploaded {len(uploaded_pdf)} PDF file(s) to S3.",
            "files_uploaded": uploaded_pdf,
            "files_failed": failed_files,
            "uploaded_count": len(uploaded_pdf),
            "failed_count": len(failed_files)
        }
    )

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
