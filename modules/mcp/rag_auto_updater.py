#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAG Auto-Update Scheduler

Automatically indexes new/modified files to keep RAG knowledge base current.
Runs periodic full indexing and file change detection.
"""

import os
import time
import threading
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

try:
    from modules.mcp.rag_indexer import RAGIndexer
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("Warning: RAG indexer not available")


class FileChangeTracker:
    """Track file changes using file hashes"""
    
    def __init__(self, state_file: str = ".rag_file_state.json"):
        self.state_file = state_file
        self.file_hashes: Dict[str, str] = {}
        self.load_state()
    
    def load_state(self):
        """Load previous file state"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.file_hashes = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load file state: {e}")
                self.file_hashes = {}
    
    def save_state(self):
        """Save current file state"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_hashes, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save file state: {e}")
    
    def get_file_hash(self, file_path: str) -> str:
        """Calculate file hash"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def get_changed_files(self, directory: str, extensions: List[str] = None) -> List[str]:
        """
        Get list of changed/new files
        
        Args:
            directory: Directory to scan
            extensions: File extensions to check (e.g., ['.py', '.html', '.md'])
        
        Returns:
            List of changed file paths
        """
        if extensions is None:
            extensions = ['.py', '.html', '.css', '.md', '.js', '.docx', '.pdf', '.pptx']
        
        changed_files = []
        
        try:
            for root, dirs, files in os.walk(directory):
                # Skip common ignored directories
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']]
                
                for file in files:
                    if any(file.endswith(ext) for ext in extensions):
                        file_path = os.path.join(root, file)
                        current_hash = self.get_file_hash(file_path)
                        
                        if not current_hash:
                            continue
                        
                        previous_hash = self.file_hashes.get(file_path, "")
                        
                        # New or changed file
                        if current_hash != previous_hash:
                            changed_files.append(file_path)
                            self.file_hashes[file_path] = current_hash
        except Exception as e:
            print(f"Error scanning directory: {e}")
        
        return changed_files


class RAGAutoUpdater:
    """Automatic RAG knowledge base updater"""
    
    def __init__(
        self,
        project_root: str = ".",
        db_path: str = "rag_knowledge_base.db",
        interval_seconds: int = 3600,
        full_index_interval_hours: int = 24
    ):
        """
        Initialize RAG auto-updater
        
        Args:
            project_root: Root directory to scan for files
            db_path: Path to RAG database
            interval_seconds: Check for changes every N seconds (default: 1 hour)
            full_index_interval_hours: Full reindex every N hours (default: 24h)
        """
        self.project_root = project_root
        self.db_path = db_path
        self.interval_seconds = interval_seconds
        self.full_index_interval_hours = full_index_interval_hours
        
        self.tracker = FileChangeTracker()
        self.indexer = RAGIndexer(db_path=db_path) if RAG_AVAILABLE else None
        
        self.is_running = False
        self.last_full_index = datetime.now()
        self.thread = None
    
    def index_files(self, file_paths: List[str]):
        """Index specific files"""
        if not self.indexer or not RAG_AVAILABLE:
            print("RAG indexer not available")
            return
        
        if not file_paths:
            print("No files to index")
            return
        
        print(f"[RAG] Indexing {len(file_paths)} files...")
        indexed_count = 0
        
        for file_path in file_paths:
            try:
                # Convert string to Path object
                path_obj = Path(file_path)
                if self.indexer.index_file(path_obj):
                    indexed_count += 1
                    print(f"  [OK] {file_path}")
            except Exception as e:
                print(f"  [ERROR] {file_path}: {e}")
        
        self.tracker.save_state()
        print(f"[RAG] Indexed {indexed_count}/{len(file_paths)} files")
    
    def full_index(self):
        """Perform full reindexing of all project files"""
        if not self.indexer or not RAG_AVAILABLE:
            print("RAG indexer not available")
            return
        
        print("[RAG] Starting full reindex...")
        start_time = time.time()
        
        # Get all files
        all_files = []
        extensions = ['.py', '.html', '.css', '.md', '.js', '.docx', '.pdf', '.pptx']
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'build', 'dist']]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    all_files.append(file_path)
        
        print(f"[RAG] Found {len(all_files)} files to index...")
        self.index_files(all_files)
        
        # Update tracker
        for file_path in all_files:
            file_hash = self.tracker.get_file_hash(file_path)
            if file_hash:
                self.tracker.file_hashes[file_path] = file_hash
        self.tracker.save_state()
        
        elapsed = time.time() - start_time
        print(f"[RAG] Full reindex completed in {elapsed:.1f}s")
        self.last_full_index = datetime.now()
    
    def _updater_loop(self):
        """Background update loop"""
        print("[RAG Updater] Started")
        
        while self.is_running:
            try:
                # Check if full index is needed
                hours_since_full = (datetime.now() - self.last_full_index).total_seconds() / 3600
                
                if hours_since_full >= self.full_index_interval_hours:
                    print(f"[RAG] Triggering full reindex (overdue by {hours_since_full - self.full_index_interval_hours:.1f}h)")
                    self.full_index()
                else:
                    # Check for file changes
                    changed_files = self.tracker.get_changed_files(self.project_root)
                    
                    if changed_files:
                        print(f"[RAG] Detected {len(changed_files)} changed/new files")
                        self.index_files(changed_files)
                
                # Sleep before next check
                time.sleep(self.interval_seconds)
                
            except Exception as e:
                print(f"[RAG Updater] Error: {e}")
                time.sleep(self.interval_seconds)
    
    def start(self):
        """Start automatic updates in background thread"""
        if self.is_running:
            print("[RAG Updater] Already running")
            return
        
        if not RAG_AVAILABLE:
            print("[RAG Updater] RAG not available, skipping")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._updater_loop, daemon=True)
        self.thread.start()
        print("[RAG Updater] Started in background thread")
    
    def stop(self):
        """Stop automatic updates"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[RAG Updater] Stopped")
    
    def index_documentation(self):
        """Index tool documentation for better RAG results"""
        if not self.indexer or not RAG_AVAILABLE:
            return
        
        print("[RAG] Indexing tool documentation...")
        
        doc_content = """
## QMS MCP Tools Documentation

### SVIT (Silicon Verification Issue Tracking)
- list_issues: Get all SVIT issues with optional filters
- get_issue_details: Get detailed information about specific issue
- list_shuttles: Get all shuttle devices

### RPMT (Risk & Project Management)
- list_rpmt_projects: List all RPMT projects
- list_rpmt_tasks: Get tasks with status tracking
- get_pdk_dk_entries: View PDK/DK verification entries

### CITS (Customer Issue Tracking System)
- list_customers: View all registered customers
- list_customer_issues: Get customer support issues
- get_issue_conversations: View issue discussion history

### Spec-Center (Specification Management)
- list_spec_categories: Browse specification categories
- list_spec_files: Find specification files

### General Tools
- list_users: View QMS system users
- list_projects: Browse projects
- list_tasks: Check task status
- get_project_summary: Get system statistics
"""
        
        try:
            # Store as special documentation file
            from modules.mcp.rag_indexer import SQLiteRAG
            rag = SQLiteRAG(db_path=self.db_path)
            
            rag.add_document(
                file_path="TOOLS_DOCUMENTATION.md",
                content=doc_content,
                file_type="documentation"
            )
            print("[RAG] Tool documentation indexed")
        except Exception as e:
            print(f"[RAG] Failed to index documentation: {e}")
    
    def index_spec_center_documents(self):
        """Index spec-center documents into RAG"""
        if not self.indexer or not RAG_AVAILABLE:
            print("[RAG] RAG indexer not available, skipping spec-center indexing")
            return
        
        try:
            from modules.spec_center.parser import SpecCenterParser
            
            print("[RAG] Indexing spec-center documents...")
            
            parser = SpecCenterParser(spec_center_path="uploads/spec_center")
            
            # Try to load from index first
            if not parser.documents:
                if not parser.load_index(".spec_center_index.json"):
                    parser.parse_all_documents()
            
            # Index each document with full content
            indexed_count = 0
            for doc_name, doc_info in parser.documents.items():
                try:
                    # Create structured content for RAG
                    content = f"""# {doc_name}

**Keywords:** {', '.join(doc_info.get('keywords', []))}

**File Size:** {doc_info.get('file_size', 0) / 1024:.1f}KB

**Content:**
{doc_info.get('full_content', '')}
"""
                    
                    self.indexer.add_document(
                        file_path=f"spec_center/{doc_name}",
                        content=content,
                        file_type="specification"
                    )
                    indexed_count += 1
                except Exception as e:
                    print(f"  [WARN] Failed to index {doc_name}: {e}")
            
            print(f"[RAG] Successfully indexed {indexed_count} spec-center documents")
        except Exception as e:
            print(f"[RAG] Error indexing spec-center: {e}")


def get_rag_updater(auto_start: bool = False) -> Optional[RAGAutoUpdater]:
    """
    Get or create RAG auto-updater instance
    
    Args:
        auto_start: If True, start updater immediately
    
    Returns:
        RAGAutoUpdater instance or None if RAG not available
    """
    if not RAG_AVAILABLE:
        return None
    
    updater = RAGAutoUpdater(
        project_root=".",
        interval_seconds=300,  # Check every 5 minutes
        full_index_interval_hours=12  # Full reindex every 12 hours
    )
    
    if auto_start:
        updater.start()
    
    return updater


if __name__ == "__main__":
    # Test the updater
    updater = RAGAutoUpdater(
        interval_seconds=60,  # Check every minute for testing
        full_index_interval_hours=1
    )
    
    print("RAG Auto-Updater Test")
    print("=" * 50)
    
    # Initial full index
    updater.full_index()
    updater.index_documentation()
    
    # Start background updates
    updater.start()
    
    print("\nUpdater running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping updater...")
        updater.stop()
