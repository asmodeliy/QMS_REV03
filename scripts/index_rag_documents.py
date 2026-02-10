#!/usr/bin/env python3
"""
RAG Document Indexing Script for QMS Server

This script indexes all documents in the QMS project for RAG (Retrieval Augmented Generation).

Usage:
    python scripts/index_rag_documents.py [options]

Options:
    --db-path PATH          Path to RAG knowledge base database (default: rag_knowledge_base.db)
    --project-dir PATH      Path to project root directory (default: detect automatically)
    --reindex               Force reindex of all documents
    --verbose               Enable verbose output
    --stats                 Show statistics without indexing
    --search QUERY          Search the knowledge base with given query
"""

import sys
import argparse
from pathlib import Path

# Add parent dir to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.mcp.rag_indexer import RAGIndexer
from modules.mcp.rag_retriever import RAGRetriever


def main():
    parser = argparse.ArgumentParser(
        description="Index QMS project documents for RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--db-path',
        default='rag_knowledge_base.db',
        help='Path to RAG knowledge base database'
    )
    
    parser.add_argument(
        '--project-dir',
        type=Path,
        default=None,
        help='Path to project root directory'
    )
    
    parser.add_argument(
        '--reindex',
        action='store_true',
        help='Force reindex of all documents'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics without indexing'
    )
    
    parser.add_argument(
        '--search',
        type=str,
        default=None,
        help='Search the knowledge base with given query'
    )
    
    args = parser.parse_args()
    
    # Initialize indexer
    try:
        print(f"Initializing RAG indexer (database: {args.db_path})...")
        indexer = RAGIndexer(db_path=args.db_path, base_dir=args.project_dir)
        
        # Show stats only
        if args.stats:
            print("\n" + "=" * 60)
            print("RAG KNOWLEDGE BASE STATISTICS")
            print("=" * 60)
            stats = indexer.get_stats()
            print(f"Total Documents: {stats['total_documents']}")
            print(f"Total Chunks: {stats['total_chunks']}")
            print(f"Database: {stats['db_path']}")
            print("\nModule Breakdown:")
            for module, count in stats['modules'].items():
                print(f"  {module}: {count} files")
            return
        
        # Search the knowledge base
        if args.search:
            print(f"\nSearching for: '{args.search}'")
            print("=" * 60)
            retriever = RAGRetriever(indexer=indexer, db_path=args.db_path)
            results = retriever.retrieve(args.search, limit=5)
            
            if not results:
                print("No results found.")
                return
            
            for i, result in enumerate(results, 1):
                print(f"\n[{i}] {result['file_path']}")
                print(f"    Score: {result['score']}")
                if result['summary']:
                    print(f"    Summary: {result['summary']}")
                if result['keywords']:
                    print(f"    Keywords: {', '.join(result['keywords'][:5])}")
                print(f"    Preview: {result['content'][:200]}...")
            return
        
        # Index the project
        print("\n" + "=" * 60)
        print("INDEXING QMS PROJECT")
        print("=" * 60)
        
        if args.reindex:
            print("Reindexing all documents...")
        
        print("Indexing Python files...")
        py_count = indexer.index_directory(indexer.base_dir, "*.py")
        print(f"  Indexed {py_count} Python files")
        
        print("Indexing HTML templates...")
        templates_dir = indexer.base_dir / "templates"
        html_count = indexer.index_directory(templates_dir, "*.html")
        print(f"  Indexed {html_count} HTML files")
        
        print("Indexing JavaScript files...")
        static_dir = indexer.base_dir / "static"
        js_count = indexer.index_directory(static_dir, "*.js")
        print(f"  Indexed {js_count} JavaScript files")
        
        print("Indexing CSS files...")
        css_count = indexer.index_directory(static_dir, "*.css")
        print(f"  Indexed {css_count} CSS files")
        
        print("Indexing Markdown documentation...")
        docs_dir = indexer.base_dir / "docs"
        md_count = indexer.index_directory(docs_dir, "*.md")
        print(f"  Indexed {md_count} Markdown files")
        
        print("\n" + "=" * 60)
        print("INDEXING COMPLETE")
        print("=" * 60)
        
        stats = indexer.get_stats()
        print(f"Total Documents: {stats['total_documents']}")
        print(f"Total Chunks: {stats['total_chunks']}")
        print("\nModule Distribution:")
        for module, count in sorted(stats['modules'].items(), key=lambda x: -x[1]):
            print(f"  {module}: {count} files")
        
        print("\n✓ RAG knowledge base ready!")
        print(f"Database: {stats['db_path']}")
        
        if args.verbose:
            print("\nInitializing RAG retriever and performing test search...")
            retriever = RAGRetriever(indexer=indexer, db_path=args.db_path)
            context = retriever.build_context("project management", max_context_length=500)
            if context:
                print("Test context retrieval successful!")
            else:
                print("Warning: No context retrieved in test search")
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
