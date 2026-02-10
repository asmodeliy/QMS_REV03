"""
Incremental RAG Indexer - High Performance Version

Only indexes files that have changed since last indexing.
Tracks file modification times and checksums to avoid re-processing.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, List, Tuple
import time

try:
    from .rag_indexer import RAGIndexer
except ImportError:
    RAGIndexer = None


class IncrementalRAGIndexer:
    """Efficient RAG indexer that only processes changed files"""
    
    def __init__(self):
        self.indexer = RAGIndexer() if RAGIndexer else None
        self.state_file = Path(".rag_indexed_state.json")
        self.state = self._load_state()
        self.priority_dirs = [
            'uploads/spec_center',
            'docs',
            'modules',
            'templates',
            'data'
        ]
        self.file_extensions = {'.pdf', '.py', '.md', '.txt', '.docx', '.xlsx', '.json', '.yml', '.yaml', '.html'}
    
    def _load_state(self) -> Dict:
        """Load previous indexing state"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load state: {e}")
                return {}
        return {}
    
    def _save_state(self):
        """Save current indexing state"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WARN] Failed to save state: {e}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Get quick hash of file (first 1MB + size)"""
        try:
            size = file_path.stat().st_size
            mtime = file_path.stat().st_mtime
            # Quick hash: size + mtime + first 1MB
            with open(file_path, 'rb') as f:
                chunk = f.read(min(1024*1024, size))
                file_hash = hashlib.md5(chunk + str(size).encode()).hexdigest()
            return f"{mtime}:{file_hash}"
        except Exception:
            return ""
    
    def _should_index_file(self, file_path: Path) -> bool:
        """Check if file needs indexing"""
        path_str = str(file_path)
        current_hash = self._get_file_hash(file_path)
        stored_hash = self.state.get(path_str, {}).get('hash', '')
        
        # Index if hash changed
        if current_hash != stored_hash:
            return True
        return False
    
    def _collect_files(self) -> List[Tuple[Path, int]]:
        """Collect files that need indexing, sorted by priority"""
        files_by_priority = {i: [] for i in range(len(self.priority_dirs))}
        files_other = []
        
        # Recursively find files
        for root, dirs, filenames in os.walk('.'):
            # Skip common unneeded directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.pytest_cache', 'build', 'dist'}]
            
            for filename in filenames:
                if not any(filename.endswith(ext) for ext in self.file_extensions):
                    continue
                
                file_path = Path(root) / filename
                
                # Skip certain patterns
                if any(x in str(file_path) for x in {'test_', '.bak', '.tmp', '__pycache__'}):
                    continue
                
                if not self._should_index_file(file_path):
                    continue
                
                # Categorize by priority
                found_priority = False
                for idx, priority_dir in enumerate(self.priority_dirs):
                    if priority_dir in str(file_path):
                        files_by_priority[idx].append(file_path)
                        found_priority = True
                        break
                
                if not found_priority:
                    files_other.append(file_path)
        
        # Combine: priority files first, then others
        all_files = []
        for idx in range(len(self.priority_dirs)):
            all_files.extend(files_by_priority[idx])
        all_files.extend(files_other)
        
        return all_files
    
    def index_incremental(self, batch_size: int = 20) -> Dict[str, int]:
        """
        Index only changed files in batches
        
        Args:
            batch_size: Number of files per batch
            
        Returns:
            Stats dict with counts
        """
        print("\n" + "="*70)
        print(f"[RAG] INCREMENTAL Indexing Started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        if not self.indexer:
            print("[ERROR] RAGIndexer not available")
            return {'total': 0, 'indexed': 0, 'skipped': 0, 'failed': 0}
        
        files_to_index = self._collect_files()
        
        if not files_to_index:
            print("[INFO] ✅ All files up-to-date! No changes detected.")
            print("="*70)
            return {'total': 0, 'indexed': 0, 'skipped': 0, 'failed': 0}
        
        print(f"[INFO] Found {len(files_to_index)} files to index")
        print("="*70)
        
        stats = {'total': len(files_to_index), 'indexed': 0, 'skipped': 0, 'failed': 0}
        
        # Process in batches
        for i in range(0, len(files_to_index), batch_size):
            batch = files_to_index[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(files_to_index) + batch_size - 1) // batch_size
            
            print(f"\n[Batch {batch_num}/{total_batches}] Processing {len(batch)} files...")
            
            for file_path in batch:
                try:
                    # Index file
                    if self.indexer.index_single_file(str(file_path)):
                        print(f"  ✅ {file_path.name}")
                        stats['indexed'] += 1
                        
                        # Update state
                        path_str = str(file_path)
                        self.state[path_str] = {
                            'hash': self._get_file_hash(file_path),
                            'indexed_at': datetime.now().isoformat()
                        }
                    else:
                        print(f"  ⏭️  {file_path.name} (skipped)")
                        stats['skipped'] += 1
                except Exception as e:
                    print(f"  ❌ {file_path.name}: {str(e)[:50]}")
                    stats['failed'] += 1
            
            # Save state after each batch
            self._save_state()
            time.sleep(0.5)  # Brief pause between batches
        
        print("\n" + "="*70)
        print(f"[RAG] Indexing Complete")
        print(f"  📊 Total: {stats['total']}")
        print(f"  ✅ Indexed: {stats['indexed']}")
        print(f"  ⏭️  Skipped: {stats['skipped']}")
        print(f"  ❌ Failed: {stats['failed']}")
        print("="*70)
        
        return stats
    
    def get_status(self) -> Dict:
        """Get indexing status"""
        return {
            'total_indexed': len(self.state),
            'last_updated': max(
                [v.get('indexed_at', '') for v in self.state.values()],
                default='Never'
            ),
            'files': list(self.state.keys())[:10]
        }


def run_incremental_indexing():
    """Main entry point"""
    indexer = IncrementalRAGIndexer()
    stats = indexer.index_incremental(batch_size=20)
    return stats


if __name__ == "__main__":
    run_incremental_indexing()
