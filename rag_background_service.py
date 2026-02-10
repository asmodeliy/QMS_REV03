#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAG Background Indexing Service (Incremental Version)

For autonomous background indexing with high performance.
Only indexes files that have actually changed since last run.

Usage:
    python rag_background_service.py
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from modules.mcp.rag_indexer_incremental import IncrementalRAGIndexer
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("Error: RAG indexer not available")
    sys.exit(1)


class BackgroundRAGService:
    """Background indexing service with incremental updates"""
    
    def __init__(self):
        self.indexer = IncrementalRAGIndexer()
        self.running = True
        print("\n" + "="*70)
        print("🚀 RAG Background Service Started (Incremental Mode)")
        print("="*70)
    
    def run_once(self):
        """Run a single indexing cycle"""
        try:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting indexing cycle...")
            stats = self.indexer.index_incremental(batch_size=20)
            return stats
        except KeyboardInterrupt:
            print("\n\n⏹️  Service interrupted by user")
            self.running = False
            return None
        except Exception as e:
            print(f"\n❌ Error in indexing cycle: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_continuous(self, check_interval: int = 300):
        """
        Run indexing continuously at intervals
        
        Args:
            check_interval: Seconds between cycles (default 5 minutes)
        """
        cycle_count = 0
        try:
            while self.running:
                cycle_count += 1
                print(f"\n{'='*70}")
                print(f"📍 CYCLE #{cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*70}")
                
                stats = self.run_once()
                
                if stats:
                    print(f"\n✅ Cycle {cycle_count} complete")
                    if stats['indexed'] == 0:
                        print("   ℹ️  All files are up-to-date!")
                        # If all up-to-date, can increase interval
                        next_wait = min(check_interval * 2, 900)  # Max 15 min
                    else:
                        next_wait = check_interval
                    
                    print(f"   ⏳ Next check in {next_wait}s ({next_wait//60}m)...")
                    time.sleep(next_wait)
                else:
                    print(f"\n⚠️  Cycle {cycle_count} failed, retrying in 60s...")
                    time.sleep(60)
        
        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("⏹️  Service stopped by user")
            print("="*70)
        except Exception as e:
            print(f"\n\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point"""
    service = BackgroundRAGService()
    
    # Run continuously with 5-minute intervals
    # (or 1 minute if you want very frequent checks)
    service.run_continuous(check_interval=300)  # 5 minutes
    
    print("\n🏁 RAG Background Service Stopped")
    print("="*70)


if __name__ == "__main__":
    main()
