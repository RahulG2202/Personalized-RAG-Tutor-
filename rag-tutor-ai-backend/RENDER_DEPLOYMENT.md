# Render Deployment Guide

## Prerequisites

- Render account at [render.com](https://render.com)
- GitHub repository with this code
- All environment variables configured

## Environment Variables Required on Render

Set these in your Render service dashboard under **Environment**:

### Critical Variables

- `GOOGLE_API_KEY` - Google Generative AI API key
- `PINECONE_API_KEY` - Pinecone vector database API key
- `PINECONE_INDEX_NAME` - Your Pinecone index name
- `EMBEDDING_MODEL` - Embedding model name. Defaults to `models/text-embedding-004`
- `AWS_ACCESS_KEY_ID` - AWS access key for S3
- `AWS_SECRET_ACCESS_KEY` - AWS secret key for S3
- `AWS_S3_BUCKET` - S3 bucket name for PDF storage

### Optional Variables

- `CORS_ORIGINS` - Frontend URLs (comma-separated)
- `AWS_REGION` - AWS region (default: us-east-1)
- `AWS_S3_PREFIX` - S3 prefix (default: materials)

The default Google embedding model returns 768-dimensional vectors, so create or recreate the Pinecone index with dimension `768` before ingestion.

## Deployment Steps

### Option 1: Using render.yaml (Recommended)

1. Push the code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New +** → **Blueprint**
4. Connect your GitHub repository
5. Select the branch to deploy
6. Render will automatically read `render.yaml` and create the service
7. Add environment variables in the dashboard
8. Click **Create Blueprint**

### Option 2: Manual Deployment

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `rag-tutor-backend`
   - **Runtime**: `Python 3.11`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`
   - **Root Directory**: `rag-tutor-ai-backend`
5. Add environment variables
6. Click **Create Web Service**

## Verification

Once deployed, test the API:

```bash
# Health check
curl https://your-service-name.onrender.com/

# List S3 PDFs
curl https://your-service-name.onrender.com/api/v1/ingest/s3-pdfs

# Ask a question
curl -X POST https://your-service-name.onrender.com/api/v1/tutor/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "What was the Battle of Cannae?"}'
```

## Troubleshooting

### "ModuleNotFoundError" on Render

- Ensure `requirements.txt` is in the root of `rag-tutor-ai-backend`
- Check that `rootDir: rag-tutor-ai-backend` is set in render.yaml

### API timeouts

- May occur during large PDF ingestions
- Render free tier has 30s timeout; upgrade to Pro for longer processing

### Cold starts

- Free tier instances sleep after 15 mins of inactivity
- Upgrade to paid plan for always-on service

## Scaling Recommendations

- **Development**: Free tier is fine for testing
- **Production**: Use paid tier (at least $7/month) for:
  - Always-on service (no cold starts)
  - Higher concurrency
  - Longer timeout limits
