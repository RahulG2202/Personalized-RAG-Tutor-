import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.core.config import s3_settings


@dataclass(frozen=True)
class S3PdfObject:
    key: str
    filename: str


@dataclass(frozen=True)
class UploadedPdf:
    bucket: str
    key: str
    filename: str
    size: int
    etag: str

    @property
    def s3_uri(self):
        return f"s3://{self.bucket}/{self.key}"


class S3StorageService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:
                raise RuntimeError(
                    "boto3 is not installed. Run pip install -r requirements.txt."
                ) from exc

            client_kwargs = {
                "region_name": s3_settings.AWS_REGION or None
            }

            if s3_settings.AWS_ACCESS_KEY_ID and s3_settings.AWS_SECRET_ACCESS_KEY:
                client_kwargs.update({
                    "aws_access_key_id": s3_settings.AWS_ACCESS_KEY_ID,
                    "aws_secret_access_key": s3_settings.AWS_SECRET_ACCESS_KEY
                })

                if s3_settings.AWS_SESSION_TOKEN:
                    client_kwargs["aws_session_token"] = s3_settings.AWS_SESSION_TOKEN

            self._client = boto3.client("s3", **client_kwargs)
        return self._client

    def _bucket(self):
        if not s3_settings.AWS_S3_BUCKET:
            raise RuntimeError("AWS_S3_BUCKET is not configured.")
        return s3_settings.AWS_S3_BUCKET

    def _prefix(self):
        prefix = s3_settings.AWS_S3_PREFIX.strip("/")
        return f"{prefix}/" if prefix else ""

    def _safe_filename(self, filename):
        name = Path(filename or "material.pdf").name
        name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" ._")
        name = re.sub(r"\s+", "_", name)
        return name or "material.pdf"

    def _sha256(self, fileobj: BinaryIO):
        digest = hashlib.sha256()

        while chunk := fileobj.read(1024 * 1024):
            digest.update(chunk)

        fileobj.seek(0)
        return digest.hexdigest()

    def upload_pdf(self, fileobj: BinaryIO, filename: str) -> UploadedPdf:
        safe_filename = self._safe_filename(filename)

        if not safe_filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF files can be uploaded.")

        fileobj.seek(0)
        header = fileobj.read(5)
        fileobj.seek(0)

        if header != b"%PDF-":
            raise ValueError("The uploaded file is not a valid PDF.")

        digest = self._sha256(fileobj)
        key = f"{self._prefix()}{digest[:16]}/{safe_filename}"
        bucket = self._bucket()

        self.client.upload_fileobj(
            fileobj,
            bucket,
            key,
            ExtraArgs={
                "ContentType": "application/pdf",
                "Metadata": {
                    "sha256": digest,
                    "original-filename": safe_filename
                }
            }
        )
        uploaded = self.client.head_object(Bucket=bucket, Key=key)

        return UploadedPdf(
            bucket=bucket,
            key=key,
            filename=safe_filename,
            size=uploaded.get("ContentLength", 0),
            etag=uploaded.get("ETag", "").strip('"')
        )

    def list_pdfs(self):
        bucket = self._bucket()
        paginator = self.client.get_paginator("list_objects_v2")
        pdfs = []

        for page in paginator.paginate(Bucket=bucket, Prefix=self._prefix()):
            for item in page.get("Contents", []):
                key = item.get("Key", "")

                if key.lower().endswith(".pdf"):
                    pdfs.append(S3PdfObject(key=key, filename=Path(key).name))

        return pdfs

    def download_pdf(self, key: str, destination_path: str):
        self.client.download_file(self._bucket(), key, destination_path)


s3_storage_service = S3StorageService()
