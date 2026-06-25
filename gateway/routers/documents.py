"""documents.py — Document ingestion router for RAG"""
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.database import get_db
from gateway.models import User, Document
from gateway.auth import get_current_user
from gateway.schemas import DocumentIngest, DocumentResponse
from agents.rag_agent import get_rag_agent

router = APIRouter()


@router.post("/", response_model=DocumentResponse, status_code=201)
async def ingest_document(
    payload: DocumentIngest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rag = get_rag_agent()
    result = await rag.ingest(
        title=payload.title,
        content=payload.content,
        metadata=payload.metadata,
        namespace=payload.namespace,
    )

    doc = Document(
        title=payload.title,
        namespace=payload.namespace,
        chunk_count=result["chunk_count"],
        metadata_=payload.metadata,
    )
    db.add(doc)
    await db.flush()

    return DocumentResponse(
        id=str(doc.id),
        title=doc.title,
        chunk_count=doc.chunk_count,
        namespace=doc.namespace,
        created_at=doc.created_at or datetime.utcnow(),
    )


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    namespace: str = Form("default"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a .txt or .md file for ingestion."""
    if file.content_type not in ["text/plain", "text/markdown"]:
        raise HTTPException(status_code=400, detail="Only .txt and .md files are supported")

    content = (await file.read()).decode("utf-8")
    rag = get_rag_agent()
    result = await rag.ingest(
        title=file.filename or "Uploaded Document",
        content=content,
        namespace=namespace,
    )

    doc = Document(
        title=file.filename or "Uploaded Document",
        namespace=namespace,
        chunk_count=result["chunk_count"],
    )
    db.add(doc)
    await db.flush()

    return DocumentResponse(
        id=str(doc.id),
        title=doc.title,
        chunk_count=doc.chunk_count,
        namespace=doc.namespace,
        created_at=doc.created_at or datetime.utcnow(),
    )
