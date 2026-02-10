"""
Model Context Protocol (MCP) Module for QMS

This module provides:
- GPT4All LLM integration with QMS data access
- RAG (Retrieval Augmented Generation) system
- MCP server implementation
- FastAPI routes for chat and AI features
"""

try:
    from modules.mcp.gpt4all_client import QMSAssistant, GPT4ALL_AVAILABLE
except ImportError:
    QMSAssistant = None
    GPT4ALL_AVAILABLE = False

try:
    from modules.mcp.rag_indexer import RAGIndexer
except ImportError:
    RAGIndexer = None

try:
    from modules.mcp.rag_retriever import RAGRetriever, RAGContextBuilder
except ImportError:
    RAGRetriever = None
    RAGContextBuilder = None

__all__ = [
    'QMSAssistant',
    'RAGIndexer',
    'RAGRetriever',
    'RAGContextBuilder',
    'GPT4ALL_AVAILABLE',
]
