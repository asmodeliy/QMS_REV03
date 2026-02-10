#!/usr/bin/env python3
"""
QMS Server - RAG System Integration Test

This script tests the RAG system integration with GPT4All and the QMS server.

Tests:
  1. RAG Indexer initialization
  2. Document indexing
  3. Search functionality
  4. Context retrieval
  5. GPT4All assistant with RAG
  6. API integration
"""

import sys
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.mcp.rag_indexer import RAGIndexer
from modules.mcp.rag_retriever import RAGRetriever

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_rag_indexer():
    """Test RAG indexer"""
    print_section("TEST 1: RAG Indexer Initialization")
    
    try:
        indexer = RAGIndexer()
        print("✓ RAG Indexer initialized successfully")
        
        # Show initial stats
        stats = indexer.get_stats()
        print(f"  Current documents in DB: {stats['total_documents']}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to initialize RAG Indexer: {e}")
        return False


def test_indexing():
    """Test document indexing"""
    print_section("TEST 2: Document Indexing")
    
    try:
        indexer = RAGIndexer()
        
        print("Indexing sample files...")
        
        # Index core directory
        print("  - Indexing core/ directory...", end=' ')
        core_dir = Path(__file__).parent.parent / "core"
        core_count = indexer.index_directory(core_dir, "*.py", recursive=False)
        print(f"✓ ({core_count} files)")
        
        # Index models
        print("  - Indexing app.py...", end=' ')
        app_file = Path(__file__).parent.parent / "app.py"
        if indexer.index_file(app_file, "main"):
            print("✓")
        else:
            print("✗")
        
        # Get stats
        stats = indexer.get_stats()
        print(f"\n  Total documents indexed: {stats['total_documents']}")
        
        return stats['total_documents'] > 0
    except Exception as e:
        print(f"✗ Indexing failed: {e}")
        return False


def test_search():
    """Test search functionality"""
    print_section("TEST 3: Search Functionality")
    
    try:
        indexer = RAGIndexer()
        
        test_queries = [
            "FastAPI application",
            "database models",
            "authentication"
        ]
        
        for query in test_queries:
            print(f"Searching for '{query}'...", end=' ')
            results = indexer.search(query, limit=3)
            print(f"✓ (found {len(results)} results)")
            if results:
                for result in results[:2]:
                    print(f"    - {result['file_name']} (score: {result['score']})")
        
        return True
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return False


def test_retriever():
    """Test RAG retriever"""
    print_section("TEST 4: RAG Retriever")
    
    try:
        indexer = RAGIndexer()
        retriever = RAGRetriever(indexer=indexer)
        
        print("Testing retrieval methods...")
        
        print("  - Basic retrieval...", end=' ')
        results = retriever.retrieve("QMS project management")
        print(f"✓ (retrieved {len(results)} documents)")
        
        print("  - Context building...", end=' ')
        context = retriever.build_context("FastAPI")
        if context:
            print(f"✓ (context length: {len(context)} chars)")
        else:
            print("✗ (no context)")
        
        print("  - Module context...", end=' ')
        try:
            module_ctx = retriever.get_module_context("rpmt")
            print(f"✓" if module_ctx else "✗")
        except:
            print("- (skipped)")
        
        return True
    except Exception as e:
        print(f"✗ Retriever test failed: {e}")
        return False


def test_gpt4all_integration():
    """Test GPT4All integration"""
    print_section("TEST 5: GPT4All Integration")
    
    try:
        from modules.mcp.gpt4all_client import QMSAssistant, GPT4ALL_AVAILABLE
        
        if not GPT4ALL_AVAILABLE:
            print("⚠ GPT4All not installed - skipping model test")
            print("  To use: pip install gpt4all")
            return False
        
        print("✓ GPT4All is available")
        
        print("Initializing assistant with RAG...", end=' ')
        assistant = QMSAssistant(enable_rag=True)
        print("✓")
        
        print(f"  Model: {assistant.model_name}")
        print(f"  Model path: {assistant.model_path}")
        print(f"  RAG enabled: {assistant.enable_rag}")
        
        return True
    except Exception as e:
        print(f"✗ GPT4All integration failed: {e}")
        return False


def test_api_routes():
    """Test API routes are properly integrated"""
    print_section("TEST 6: API Routes Integration")
    
    try:
        from modules.mcp.gpt4all_routes import router as gpt4all_router
        from modules.mcp.routes import router as mcp_router
        
        print("✓ gpt4all_routes imported successfully")
        print("✓ mcp routes imported successfully")
        
        # Check routes
        gpt4all_routes = [route.path for route in gpt4all_router.routes]
        mcp_routes = [route.path for route in mcp_router.routes]
        
        print(f"\nGPT4All routes ({len(gpt4all_routes)}):")
        for route in gpt4all_routes[:5]:
            print(f"  - {route}")
        if len(gpt4all_routes) > 5:
            print(f"  ... and {len(gpt4all_routes) - 5} more")
        
        print(f"\nMCP routes ({len(mcp_routes)}):")
        for route in mcp_routes[:5]:
            print(f"  - {route}")
        if len(mcp_routes) > 5:
            print(f"  ... and {len(mcp_routes) - 5} more")
        
        return True
    except Exception as e:
        print(f"✗ API routes test failed: {e}")
        return False


def test_config():
    """Test configuration"""
    print_section("TEST 7: Configuration")
    
    try:
        from core.config import BASE_DIR, SESSION_SECRET, DB_PATH
        
        print(f"✓ Base directory: {BASE_DIR}")
        print(f"✓ Database path: {DB_PATH}")
        print(f"✓ Session secret: {'*' * len(SESSION_SECRET)}")
        
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  QMS SERVER - RAG SYSTEM INTEGRATION TEST")
    print("=" * 70)
    print(f"Project root: {project_root}")
    
    tests = [
        ("RAG Indexer", test_rag_indexer),
        ("Document Indexing", test_indexing),
        ("Search Functionality", test_search),
        ("RAG Retriever", test_retriever),
        ("GPT4All Integration", test_gpt4all_integration),
        ("API Routes", test_api_routes),
        ("Configuration", test_config),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Unexpected error in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! RAG system is ready.")
        print("\nNext steps:")
        print("  1. Run: python scripts/index_rag_documents.py")
        print("  2. Start: python app.py")
        print("  3. Visit: http://localhost:8000/ai-chat (admin only)")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
