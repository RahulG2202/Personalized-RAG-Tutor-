# Personalized RAG Tutor

## S3 PDF ingestion

The website upload flow now sends selected PDFs to the backend, and the backend stores them in S3. Training reads PDFs back from S3 instead of `rag-tutor-ai-backend/data`.

Required backend environment variables:

```bash
GOOGLE_API_KEY=...
HUGGINGFACEHUB_API_TOKEN=...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name
```

The AWS identity needs `s3:PutObject`, `s3:ListBucket`, and `s3:GetObject` access for that bucket/prefix.
The Pinecone index must use 384 dimensions for the default Hugging Face embedding model.
Create `HUGGINGFACEHUB_API_TOKEN` as a Hugging Face fine-grained user access token with the `Make calls to Inference Providers` permission enabled. A token that can read Hub models can still fail hosted embeddings with HTTP 403 if this permission is missing.

Optional:

```bash
AWS_S3_PREFIX=materials
EMBEDDING_MODEL=ibm-granite/granite-embedding-97m-multilingual-r2
EMBEDDING_DIMENSIONS=384
HUGGINGFACE_EMBEDDING_API_URL=https://router.huggingface.co/hf-inference
```

Install backend dependencies after pulling this change:

```bash
cd rag-tutor-ai-backend
pip install -r requirements.txt
```
