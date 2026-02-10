"""
RAG Retriever for QMS Assistant

This module provides document retrieval and context generation for the GPT4All assistant.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from modules.mcp.rag_indexer import RAGIndexer


class RAGRetriever:
    """Retrieve documents and generate context for LLM"""
    
    def __init__(self, indexer: Optional[RAGIndexer] = None, db_path: str = "rag_knowledge_base.db"):
        """Initialize the RAG retriever
        
        Args:
            indexer: RAGIndexer instance (creates new one if not provided)
            db_path: Path to the knowledge base database
        """
        self.indexer = indexer or RAGIndexer(db_path=db_path)
        self.retrieval_history = []
    
    def retrieve(
        self, 
        query: str, 
        limit: int = 5,
        min_score: int = 0,
        include_chunks: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a query
        
        Args:
            query: Search query
            limit: Maximum number of documents to return
            min_score: Minimum relevance score (0-100 scale approx)
            include_chunks: If True, include chunk-level information
        
        Returns:
            List of relevant documents
        """
        results = self.indexer.search(query, limit=limit * 2)  # Get extra results
        
        # Filter by score and limit
        filtered = [r for r in results if r['score'] >= min_score][:limit]
        
        # Add to history
        self.retrieval_history.append({
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'results_count': len(filtered)
        })
        
        return filtered
    
    def build_context(
        self,
        query: str,
        max_context_length: int = 3000,
        include_metadata: bool = True,
        result_limit: int = 5
    ) -> str:
        """Build a context string for the LLM prompt
        
        Args:
            query: Search query
            max_context_length: Maximum character length of context
            include_metadata: If True, include document metadata
            result_limit: Maximum number of documents to include
        
        Returns:
            Formatted context string ready for prompt injection
        """
        results = self.retrieve(query, limit=result_limit)
        
        if not results:
            return ""
        
        context_lines = [
            "=" * 80,
            "RETRIEVED CONTEXT FROM QMS KNOWLEDGE BASE",
            "=" * 80
        ]
        
        current_length = sum(len(line) for line in context_lines) + 200
        
        for i, result in enumerate(results, 1):
            if current_length > max_context_length:
                context_lines.append(f"\n... (truncated, {len(results) - i + 1} more documents available)")
                break
            
            doc_section = []
            doc_section.append(f"\n[Document {i}] {result['file_name']}")
            
            if include_metadata:
                doc_section.append(f"Path: {result['file_path']}")
                doc_section.append(f"Relevance Score: {result['score']}")
                if result['keywords']:
                    doc_section.append(f"Keywords: {', '.join(result['keywords'][:5])}")
            
            if result['summary']:
                doc_section.append(f"Summary: {result['summary']}")
            
            doc_section.append(f"\nContent:\n{result['content']}")
            doc_section.append("-" * 40)
            
            section_text = "\n".join(doc_section)
            current_length += len(section_text)
            context_lines.append(section_text)
        
        context_lines.append("=" * 80)
        return "\n".join(context_lines[:len(context_lines)])
    
    def get_module_context(self, module_name: str) -> str:
        """Get context for a specific module
        
        Args:
            module_name: Name of the module (e.g., 'rpmt', 'svit', 'cits')
        
        Returns:
            Context string containing module documentation
        """
        query = f"{module_name} module overview structure"
        return self.build_context(query, max_context_length=5000, result_limit=10)
    
    def get_system_architecture_context(self) -> str:
        """Get high-level system architecture context"""
        queries = [
            "QMS system architecture application structure",
            "FastAPI routes endpoints middleware",
            "database models schema"
        ]
        
        all_results = []
        for query in queries:
            results = self.retrieve(query, limit=3)
            all_results.extend(results)
        
        # Deduplicate by file path
        seen = set()
        unique_results = []
        for result in all_results:
            if result['file_path'] not in seen:
                seen.add(result['file_path'])
                unique_results.append(result)
        
        context_lines = [
            "=" * 80,
            "QMS SYSTEM ARCHITECTURE CONTEXT",
            "=" * 80,
        ]
        
        for i, result in enumerate(unique_results[:10], 1):
            context_lines.append(f"\n[{i}] {result['file_path']}")
            if result['summary']:
                context_lines.append(f"Overview: {result['summary']}")
            if result['keywords']:
                context_lines.append(f"Components: {', '.join(result['keywords'][:8])}")
        
        context_lines.append("=" * 80)
        return "\n".join(context_lines)
    
    def get_feature_context(self, feature_name: str) -> str:
        """Get context for a specific feature or functionality
        
        Args:
            feature_name: Name of the feature (e.g., 'authentication', 'file_upload')
        
        Returns:
            Context string for the feature
        """
        query = f"{feature_name} implementation"
        return self.build_context(query, max_context_length=4000, result_limit=8)
    
    def create_prompt_with_context(
        self,
        user_query: str,
        include_system_context: bool = True,
        include_module_context: bool = False,
        module_name: Optional[str] = None
    ) -> Tuple[str, str]:
        """Create a complete prompt with retrieved context
        
        Args:
            user_query: The user's question
            include_system_context: If True, include system architecture
            include_module_context: If True, include specific module context
            module_name: Module name to include context for
        
        Returns:
            Tuple of (system_context, enhanced_user_query)
        """
        context_parts = [
            "You are an intelligent QMS (Quality Management System) assistant.",
            "You have access to comprehensive documentation about the QMS system."
        ]
        
        # Add system architecture context
        if include_system_context:
            arch_context = self.get_system_architecture_context()
            context_parts.append(f"\n{arch_context}")
        
        # Add specific module context if requested
        if include_module_context and module_name:
            module_context = self.get_module_context(module_name)
            context_parts.append(f"\n{module_context}")
        
        # Add query-specific context
        query_context = self.build_context(user_query, max_context_length=2000, result_limit=5)
        if query_context:
            context_parts.append(f"\n{query_context}")
        
        # Combine all context
        system_context = "\n".join(context_parts)
        
        # Create enhanced user query
        enhanced_query = f"""Based on the QMS system documentation provided above, please answer the following question:

{user_query}

Please provide a detailed, accurate response based on the retrieved documentation."""
        
        return system_context, enhanced_query
    
    def format_for_system_prompt(self, context: str) -> str:
        """Format context for use in system prompt
        
        Args:
            context: Context string
        
        Returns:
            Formatted context ready for system prompt
        """
        return f"""
------- QMS KNOWLEDGE BASE -------
{context}
------- END KNOWLEDGE BASE -------
"""
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics"""
        return {
            'retrieval_history_size': len(self.retrieval_history),
            'indexer_stats': self.indexer.get_stats(),
            'recent_queries': self.retrieval_history[-10:] if self.retrieval_history else []
        }
    
    def clear_history(self):
        """Clear retrieval history"""
        self.retrieval_history = []


class RAGContextBuilder:
    """Helper class to build various types of context"""
    
    def __init__(self, retriever: RAGRetriever):
        """Initialize the context builder
        
        Args:
            retriever: RAGRetriever instance
        """
        self.retriever = retriever
    
    def build_code_analysis_context(self, code_snippet: str) -> str:
        """Build context for analyzing code snippets
        
        Args:
            code_snippet: Code to analyze
        
        Returns:
            Context string with relevant documentation
        """
        # Extract potential module/function names from code
        lines = code_snippet.split('\n')
        queries = []
        
        for line in lines[:20]:  # Sample first 20 lines
            if 'import' in line:
                parts = line.split()
                for part in parts:
                    if part not in ['import', 'from', 'as']:
                        queries.append(part)
            elif 'def ' in line or 'class ' in line:
                queries.append(line.split('(')[0].replace('def ', '').replace('class ', ''))
        
        # Get context for each q
        contexts = []
        for query in queries[:5]:
            context = self.retriever.build_context(query, max_context_length=1000, result_limit=3)
            if context:
                contexts.append(context)
        
        return "\n".join(contexts)
    
    def build_troubleshooting_context(self, error_message: str) -> str:
        """Build context for troubleshooting errors
        
        Args:
            error_message: Error message
        
        Returns:
            Context string with relevant troubleshooting information
        """
        query = f"error exception {error_message}"
        return self.retriever.build_context(query, max_context_length=3000, result_limit=8)
    
    def build_feature_request_context(self, feature_request: str) -> str:
        """Build context for feature requests
        
        Args:
            feature_request: Description of requested feature
        
        Returns:
            Context string with relevant implementation examples
        """
        return self.retriever.build_context(feature_request, max_context_length=4000, result_limit=10)


if __name__ == "__main__":
    # Example usage
    retriever = RAGRetriever()
    
    print("RAG Retriever initialized")
    print(f"Stats: {retriever.get_stats()}")
    
    # Example retrieval
    print("\n\nExample retrieval for 'project management':")
    context = retriever.build_context("project management", max_context_length=1000)
    print(context[:500] + "...")
