#!/usr/bin/env python3
"""
Script to index the codebase directory contents into Solr.
Processes Python, Markdown, and other text files.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import httpx


async def get_embeddings(text: str, ollama_url: str = "http://localhost:11434") -> List[float]:
    """Generate embeddings for text using Ollama."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ollama_url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
            )

            if response.status_code == 200:
                return response.json()["embedding"]
            else:
                print(f"Warning: Failed to get embeddings: {response.status_code}")
                return None
    except Exception as e:
        print(f"Warning: Error getting embeddings: {e}")
        return None


def should_index_file(file_path: Path) -> bool:
    """Determine if a file should be indexed."""
    # Skip directories, hidden files, and binary files
    if file_path.is_dir():
        return False

    if any(part.startswith('.') for part in file_path.parts):
        return False

    # Skip certain directories
    skip_dirs = {
        '__pycache__', 'venv', '.venv', 'node_modules',
        'htmlcov', '.pytest_cache', '.mypy_cache', '.ruff_cache',
        '.git', 'data/processed'
    }

    if any(skip_dir in str(file_path) for skip_dir in skip_dirs):
        return False

    # Include specific file extensions
    extensions = {
        '.py', '.md', '.txt', '.json', '.yaml', '.yml',
        '.toml', '.sh', '.dockerfile', '.sql', '.html',
        '.js', '.ts', '.jsx', '.tsx', '.css'
    }

    # Also check for Dockerfile, Makefile, etc.
    special_names = {'Dockerfile', 'Makefile', 'README', 'LICENSE', 'CHANGELOG'}

    return (
        file_path.suffix.lower() in extensions or
        file_path.name in special_names or
        any(file_path.name.startswith(name) for name in special_names)
    )


def get_file_category(file_path: Path) -> List[str]:
    """Determine categories for a file."""
    categories = []

    # Extension-based categories
    if file_path.suffix == '.py':
        categories.append('python')
        if 'test' in file_path.name:
            categories.append('tests')
    elif file_path.suffix == '.md':
        categories.append('documentation')
    elif file_path.suffix in {'.json', '.yaml', '.yml', '.toml'}:
        categories.append('configuration')
    elif file_path.suffix in {'.sh'}:
        categories.append('scripts')

    # Directory-based categories
    parts = file_path.parts
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


async def process_file(file_path: Path, base_path: Path) -> Dict[str, Any]:
    """Process a single file into a document."""
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Create relative path for ID
        rel_path = file_path.relative_to(base_path)
        doc_id = str(rel_path).replace('/', '_').replace('\\', '_')

        # Get file stats
        stat = file_path.stat()

        # Determine title
        title = file_path.name
        if file_path.suffix == '.md' and content.startswith('#'):
            # Try to extract markdown title
            first_line = content.split('\n')[0]
            if first_line.startswith('#'):
                title = first_line.lstrip('#').strip()

        # Create document
        doc = {
            'id': doc_id,
            'title': title,
            'content': content,
            'source': str(rel_path),
            'date_indexed_dt': datetime.utcnow().isoformat() + 'Z',
            'category_ss': get_file_category(file_path),
            'tags_ss': [file_path.suffix.lstrip('.') if file_path.suffix else 'no-extension'],
        }

        # Generate embeddings
        # Truncate content for embedding if too long
        embed_text = content[:8000] if len(content) > 8000 else content
        embedding = await get_embeddings(embed_text)

        if embedding:
            doc['embedding'] = embedding
            doc['vector_model_s'] = 'nomic-embed-text'
            doc['dimensions_i'] = len(embedding)

        return doc

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None


async def index_documents(docs: List[Dict[str, Any]], collection: str = "codebase"):
    """Index documents into Solr."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"http://localhost:8983/solr/{collection}/update/json/docs",
                json=docs,
                params={"commit": "true"},
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                print(f"Indexed {len(docs)} documents")
                return True
            else:
                print(f"Error indexing: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print(f"Error indexing documents: {e}")
        return False


async def main():
    """Main entry point."""
    # Get the base directory (project root)
    base_path = Path(__file__).parent.parent
    collection = sys.argv[1] if len(sys.argv) > 1 else "codebase"

    print(f"Indexing codebase from: {base_path}")
    print(f"Target collection: {collection}")

    # Find all files to index
    files_to_index = []
    for root, dirs, files in os.walk(base_path):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
            '__pycache__', 'venv', '.venv', 'node_modules', 'htmlcov',
            '.pytest_cache', '.mypy_cache', '.ruff_cache'
        }]

        for file in files:
            file_path = Path(root) / file
            if should_index_file(file_path):
                files_to_index.append(file_path)

    print(f"Found {len(files_to_index)} files to index")

    # Process files in batches
    batch_size = 10
    all_docs = []

    for i, file_path in enumerate(files_to_index):
        print(f"Processing [{i+1}/{len(files_to_index)}]: {file_path.relative_to(base_path)}")
        doc = await process_file(file_path, base_path)
        if doc:
            all_docs.append(doc)

        # Index in batches
        if len(all_docs) >= batch_size:
            await index_documents(all_docs, collection)
            all_docs = []

    # Index remaining documents
    if all_docs:
        await index_documents(all_docs, collection)

    print(f"\n✅ Indexing complete! Total files processed: {len(files_to_index)}")


if __name__ == "__main__":
    asyncio.run(main())
