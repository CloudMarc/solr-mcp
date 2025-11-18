#!/usr/bin/env python3
"""
File system watcher for automatic Solr index updates.

Watches the codebase for file changes and automatically updates the Solr index.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import httpx

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Try to import watchdog
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
except ImportError:
    print("Error: watchdog not installed")
    print("Install with: pip install watchdog")
    sys.exit(1)


class CodebaseIndexer(FileSystemEventHandler):
    """Watches codebase and updates Solr index on file changes."""

    def __init__(
        self,
        base_path: Path,
        solr_url: str = "http://localhost:8983/solr",
        collection: str = "codebase",
        ollama_url: str = "http://localhost:11434"
    ):
        self.base_path = base_path
        self.solr_url = solr_url
        self.collection = collection
        self.ollama_url = ollama_url

        # Debounce rapid file changes
        self.pending_updates: Dict[str, float] = {}
        self.update_delay = 1.0  # Wait 1 second before indexing

        # Statistics
        self.stats = {
            'files_indexed': 0,
            'files_deleted': 0,
            'errors': 0
        }

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification."""
        if not event.is_directory and self._should_index(event.src_path):
            self._schedule_reindex(event.src_path)

    def on_created(self, event: FileSystemEvent):
        """Handle file creation."""
        if not event.is_directory and self._should_index(event.src_path):
            self._schedule_reindex(event.src_path)

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion."""
        if not event.is_directory and self._should_index(event.src_path):
            asyncio.create_task(self._delete_from_index(event.src_path))

    def on_moved(self, event: FileSystemEvent):
        """Handle file move/rename."""
        if hasattr(event, 'dest_path'):
            # Delete old path
            if self._should_index(event.src_path):
                asyncio.create_task(self._delete_from_index(event.src_path))

            # Index new path
            if self._should_index(event.dest_path):
                self._schedule_reindex(event.dest_path)

    def _should_index(self, path: str) -> bool:
        """Check if file should be indexed."""
        path_obj = Path(path)

        # Skip hidden files and directories
        if any(part.startswith('.') for part in path_obj.parts):
            return False

        # Skip excluded directories
        skip_dirs = {
            '__pycache__', 'venv', '.venv', 'node_modules',
            'htmlcov', '.pytest_cache', '.mypy_cache', '.ruff_cache'
        }
        if any(skip_dir in str(path_obj) for skip_dir in skip_dirs):
            return False

        # Include specific extensions
        extensions = {
            '.py', '.md', '.txt', '.json', '.yaml', '.yml',
            '.toml', '.sh', '.sql', '.html', '.js', '.ts'
        }
        return path_obj.suffix in extensions

    def _schedule_reindex(self, path: str):
        """Schedule file for reindexing (with debounce)."""
        self.pending_updates[path] = asyncio.get_event_loop().time()
        asyncio.create_task(self._debounced_reindex(path))

    async def _debounced_reindex(self, path: str):
        """Wait for debounce period then reindex."""
        await asyncio.sleep(self.update_delay)

        # Check if file was modified again during wait
        if path in self.pending_updates:
            scheduled_time = self.pending_updates[path]
            if asyncio.get_event_loop().time() - scheduled_time >= self.update_delay:
                del self.pending_updates[path]
                await self._reindex_file(path)

    async def _reindex_file(self, path: str):
        """Reindex a single file."""
        try:
            # Check if file still exists
            if not os.path.exists(path):
                return

            # Read file content
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Get relative path
            try:
                rel_path = Path(path).relative_to(self.base_path)
            except ValueError:
                # Path not relative to base, skip
                return

            # Generate document ID
            doc_id = str(rel_path).replace('/', '_').replace('\\', '_')

            # Determine categories
            categories = self._get_categories(rel_path)

            # Determine tags
            tags = [rel_path.suffix.lstrip('.') if rel_path.suffix else 'no-extension']

            # Create base document
            doc = {
                'id': doc_id,
                'source': str(rel_path),
                'title': rel_path.name,
                'content': content,
                'date_indexed_dt': datetime.utcnow().isoformat() + 'Z',
                'category_ss': categories,
                'tags_ss': tags
            }

            # Generate embeddings (optional, can be slow)
            try:
                embed_text = content[:8000] if len(content) > 8000 else content
                async with httpx.AsyncClient(timeout=10.0) as client:
                    embed_response = await client.post(
                        f"{self.ollama_url}/api/embeddings",
                        json={"model": "nomic-embed-text", "prompt": embed_text}
                    )

                    if embed_response.status_code == 200:
                        embedding = embed_response.json()["embedding"]
                        doc['embedding'] = embedding
                        doc['vector_model_s'] = 'nomic-embed-text'
                        doc['dimensions_i'] = len(embedding)
            except Exception as e:
                # Embedding generation failed, continue without it
                print(f"⚠️  Could not generate embedding for {rel_path}: {e}")

            # Update in Solr
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.solr_url}/{self.collection}/update/json/docs",
                    json=[doc],
                    params={"commit": "true"}
                )

                if response.status_code == 200:
                    self.stats['files_indexed'] += 1
                    print(f"✅ Indexed: {rel_path}")
                else:
                    self.stats['errors'] += 1
                    print(f"❌ Error indexing {rel_path}: {response.status_code}")

        except Exception as e:
            self.stats['errors'] += 1
            print(f"❌ Error indexing {path}: {e}")

    async def _delete_from_index(self, path: str):
        """Remove file from Solr index."""
        try:
            # Get relative path
            try:
                rel_path = Path(path).relative_to(self.base_path)
            except ValueError:
                return

            doc_id = str(rel_path).replace('/', '_').replace('\\', '_')

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.solr_url}/{self.collection}/update",
                    json={"delete": {"id": doc_id}},
                    params={"commit": "true"},
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    self.stats['files_deleted'] += 1
                    print(f"🗑️  Deleted: {rel_path}")
                else:
                    self.stats['errors'] += 1
                    print(f"❌ Error deleting {rel_path}: {response.status_code}")

        except Exception as e:
            self.stats['errors'] += 1
            print(f"❌ Error deleting {path}: {e}")

    def _get_categories(self, path: Path) -> List[str]:
        """Determine file categories."""
        categories = []

        # Extension-based
        if path.suffix == '.py':
            categories.append('python')
            if 'test' in path.name:
                categories.append('tests')
        elif path.suffix == '.md':
            categories.append('documentation')
        elif path.suffix in {'.json', '.yaml', '.yml', '.toml'}:
            categories.append('configuration')
        elif path.suffix == '.sh':
            categories.append('scripts')

        # Directory-based
        parts = path.parts
        if 'tests' in parts:
            categories.append('tests')
        if 'docs' in parts:
            categories.append('documentation')
        if 'scripts' in parts:
            categories.append('scripts')
        if 'solr_mcp' in parts:
            categories.append('source')
            if 'tools' in parts:
                categories.append('tools')
            if 'vector_provider' in parts:
                categories.append('vector')

        return categories if categories else ['other']

    def print_stats(self):
        """Print indexing statistics."""
        print("\n" + "=" * 60)
        print("📊 Indexing Statistics")
        print("=" * 60)
        print(f"Files indexed:  {self.stats['files_indexed']}")
        print(f"Files deleted:  {self.stats['files_deleted']}")
        print(f"Errors:         {self.stats['errors']}")
        print("=" * 60)


async def main():
    """Main entry point."""
    # Get base path (project root)
    base_path = Path(__file__).parent.parent
    collection = sys.argv[1] if len(sys.argv) > 1 else "codebase"

    print("=" * 80)
    print("🔄 Solr Codebase Watcher - Real-time Index Updates")
    print("=" * 80)
    print(f"📂 Watching: {base_path}")
    print(f"📡 Collection: {collection}")
    print(f"🔗 Solr: http://localhost:8983/solr/{collection}")
    print("=" * 80)
    print("\nPress Ctrl+C to stop\n")

    # Create event handler
    event_handler = CodebaseIndexer(
        base_path=base_path,
        collection=collection
    )

    # Create observer
    observer = Observer()
    observer.schedule(event_handler, str(base_path), recursive=True)
    observer.start()

    print("👀 Watcher started! Monitoring file changes...\n")

    try:
        # Run forever
        while True:
            await asyncio.sleep(10)

            # Print stats periodically
            if (event_handler.stats['files_indexed'] +
                event_handler.stats['files_deleted'] +
                event_handler.stats['errors']) > 0:
                event_handler.print_stats()
                # Reset stats
                event_handler.stats = {
                    'files_indexed': 0,
                    'files_deleted': 0,
                    'errors': 0
                }

    except KeyboardInterrupt:
        print("\n\n⏸️  Stopping watcher...")
        observer.stop()
        observer.join()

        print("✅ Watcher stopped")
        event_handler.print_stats()


if __name__ == '__main__':
    # Run with asyncio
    asyncio.run(main())
