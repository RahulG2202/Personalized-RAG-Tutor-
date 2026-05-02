# Personalized RAG Tutor

## S3 PDF ingestion

The website upload flow now sends selected PDFs to the backend, and the backend stores them in S3. Training reads PDFs back from S3 instead of `rag-tutor-ai-backend/data`.

Required backend environment variables:

```bash
GOOGLE_API_KEY=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name
```

The AWS identity needs `s3:PutObject`, `s3:ListBucket`, and `s3:GetObject` access for that bucket/prefix.

Optional:

```bash
AWS_S3_PREFIX=materials
```

Install backend dependencies after pulling this change:

```bash
cd rag-tutor-ai-backend
pip install -r requirements.txt
```
