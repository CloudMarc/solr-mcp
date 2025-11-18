# Advanced Indexing Features

This guide covers the Phase 1 advanced indexing features in Solr MCP: Atomic Updates, Optimistic Concurrency Control, Enhanced Commits, and Real-Time Get.

## Table of Contents

- [Overview](#overview)
- [Atomic Updates](#atomic-updates)
  - [Supported Operations](#supported-operations)
  - [Basic Usage](#basic-usage)
  - [Advanced Examples](#advanced-examples)
- [Optimistic Concurrency Control](#optimistic-concurrency-control)
  - [How It Works](#how-it-works)
  - [Usage Examples](#usage-examples)
  - [Handling Conflicts](#handling-conflicts)
- [Enhanced Commits](#enhanced-commits)
  - [Soft vs Hard Commits](#soft-vs-hard-commits)
  - [Commit Options](#commit-options)
  - [Best Practices](#best-practices)
- [Real-Time Get](#real-time-get)
  - [How It Works](#how-it-works-1)
  - [Usage Examples](#usage-examples-1)
  - [Use Cases](#use-cases)
- [Common Workflows](#common-workflows)
- [Performance Considerations](#performance-considerations)
- [Troubleshooting](#troubleshooting)

## Overview

Phase 1 advanced indexing features provide fine-grained control over document updates and commit strategies:

- **Atomic Updates**: Update specific fields without reindexing entire documents
- **Optimistic Concurrency**: Prevent concurrent update conflicts with version-based locking
- **Soft vs Hard Commits**: Choose between fast visibility or durability
- **Real-Time Get**: Retrieve documents immediately, even before commit

These features are essential for building high-performance, real-time applications with Solr.

## Atomic Updates

Atomic updates allow you to modify specific fields in a document without having to reindex the entire document. This is much more efficient than retrieving, modifying, and re-adding the complete document.

### Supported Operations

Solr supports several atomic update operations:

| Operation | Description | Use Case |
|-----------|-------------|----------|
| `set` | Replace field value | Update a product price |
| `inc` | Increment numeric field | Increment view count |
| `add` | Add value to multi-valued field | Add tag to document |
| `remove` | Remove value from multi-valued field | Remove tag from document |
| `removeregex` | Remove values matching regex | Remove tags matching pattern |

### Basic Usage

#### Update a Single Field

Update a product's price:

```python
from solr_mcp.tools import execute_atomic_update

result = await execute_atomic_update(
    mcp,
    collection="products",
    doc_id="PROD-123",
    updates={
        "price": {"set": 29.99}
    }
)
```

Response:
```json
{
  "status": "success",
  "doc_id": "PROD-123",
  "collection": "products",
  "version": 42,
  "updates_applied": 1
}
```

#### Increment a Counter

Increment a view count:

```python
result = await execute_atomic_update(
    mcp,
    collection="products",
    doc_id="PROD-123",
    updates={
        "view_count": {"inc": 1}
    }
)
```

#### Add to Multi-Valued Field

Add tags to a product:

```python
result = await execute_atomic_update(
    mcp,
    collection="products",
    doc_id="PROD-123",
    updates={
        "tags": {"add": ["sale", "featured"]}
    }
)
```

#### Remove from Multi-Valued Field

Remove specific tags:

```python
result = await execute_atomic_update(
    mcp,
    collection="products",
    doc_id="PROD-123",
    updates={
        "tags": {"remove": ["old", "discontinued"]}
    }
)
```

### Advanced Examples

#### Multiple Field Updates

Update multiple fields in a single atomic operation:

```python
result = await execute_atomic_update(
    mcp,
    collection="products",
    doc_id="PROD-123",
    updates={
        "price": {"set": 24.99},           # Update price
        "stock": {"inc": -1},              # Decrement stock
        "tags": {"add": ["popular"]},      # Add tag
        "status": {"set": "active"}        # Update status
    }
)
```

Response shows all updates applied:
```json
{
  "status": "success",
  "doc_id": "PROD-123",
  "collection": "products",
  "version": 45,
  "updates_applied": 4
}
```

#### Atomic Update with Commit

Immediately commit the changes:

```python
result = await execute_atomic_update(
    mcp,
    collection="products",
    doc_id="PROD-123",
    updates={
        "price": {"set": 19.99}
    },
    commit=True
)
```

#### Atomic Update with commitWithin

Auto-commit within 5 seconds (5000ms):

```python
result = await execute_atomic_update(
    mcp,
    collection="products",
    doc_id="PROD-123",
    updates={
        "price": {"set": 19.99}
    },
    commitWithin=5000
)
```

## Optimistic Concurrency Control

Optimistic concurrency control prevents concurrent update conflicts using document version numbers. Solr maintains a `_version_` field for each document that increments with every update.

### How It Works

1. Read document and note its `_version_`
2. Make modifications locally
3. Send update with the original `_version_`
4. Solr only applies update if version matches
5. If version changed (concurrent update), Solr rejects with conflict error

This ensures that your update doesn't overwrite changes made by another process.

### Usage Examples

#### Basic Optimistic Locking

```python
# 1. First, get the document with real-time get to retrieve current version
doc_result = await execute_realtime_get(
    mcp,
    collection="products",
    doc_ids=["PROD-123"]
)

current_version = doc_result["docs"][0]["_version_"]

# 2. Update with version check
try:
    result = await execute_atomic_update(
        mcp,
        collection="products",
        doc_id="PROD-123",
        updates={
            "stock": {"inc": -1}
        },
        version=current_version  # Optimistic lock
    )
    print(f"Update successful, new version: {result['version']}")
except IndexingError as e:
    if "version conflict" in str(e).lower():
        print("Document was modified by another process, retry needed")
        # Handle conflict - retry logic here
    else:
        raise
```

#### Retry Logic for Conflicts

Implement automatic retry with exponential backoff:

```python
import asyncio

async def atomic_update_with_retry(
    mcp, collection, doc_id, updates, max_retries=3
):
    """Atomic update with automatic retry on version conflict."""

    for attempt in range(max_retries):
        try:
            # Get current version
            doc_result = await execute_realtime_get(
                mcp, collection=collection, doc_ids=[doc_id]
            )

            if not doc_result["docs"]:
                raise ValueError(f"Document {doc_id} not found")

            current_version = doc_result["docs"][0]["_version_"]

            # Attempt update with version
            result = await execute_atomic_update(
                mcp,
                collection=collection,
                doc_id=doc_id,
                updates=updates,
                version=current_version
            )

            return result  # Success!

        except IndexingError as e:
            if "version conflict" in str(e).lower() and attempt < max_retries - 1:
                # Version conflict, retry with backoff
                wait_time = (2 ** attempt) * 0.1  # Exponential backoff
                print(f"Version conflict, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            else:
                raise  # Max retries exceeded or different error

    raise IndexingError("Max retries exceeded for atomic update")
```

Usage:

```python
result = await atomic_update_with_retry(
    mcp,
    collection="products",
    doc_id="PROD-123",
    updates={"stock": {"inc": -1}}
)
```

### Handling Conflicts

When a version conflict occurs:

1. **Retry the operation**: Fetch the latest version and retry
2. **Merge changes**: If both updates are non-conflicting, merge them
3. **User notification**: Ask user to resolve conflict manually
4. **Abandon update**: If update is no longer valid

Example conflict handling:

```python
async def handle_price_update(mcp, doc_id, new_price):
    """Update price with conflict handling."""

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Get current document
            doc = await execute_realtime_get(
                mcp, collection="products", doc_ids=[doc_id]
            )

            if not doc["docs"]:
                return {"error": "Document not found"}

            current_doc = doc["docs"][0]
            current_version = current_doc["_version_"]
            current_price = current_doc.get("price", 0)

            # Business logic: only update if price changed significantly
            if abs(current_price - new_price) < 0.01:
                return {"status": "skipped", "reason": "Price unchanged"}

            # Attempt update
            result = await execute_atomic_update(
                mcp,
                collection="products",
                doc_id=doc_id,
                updates={"price": {"set": new_price}},
                version=current_version
            )

            return result

        except IndexingError as e:
            if "version conflict" in str(e).lower():
                if attempt < max_attempts - 1:
                    print(f"Conflict detected, retrying... (attempt {attempt + 1})")
                    await asyncio.sleep(0.1 * (2 ** attempt))
                    continue
                else:
                    return {"error": "Too many conflicts, manual intervention needed"}
            raise

    return {"error": "Update failed after max retries"}
```

## Enhanced Commits

Solr supports two types of commits with different trade-offs between visibility and durability.

### Soft vs Hard Commits

| Feature | Soft Commit | Hard Commit |
|---------|-------------|-------------|
| Visibility | Documents visible in search | Documents visible in search |
| Durability | NOT durable (no fsync) | Durable to disk (fsync) |
| Speed | Very fast (milliseconds) | Slower (seconds) |
| Transaction Log | Changes in transaction log | Changes flushed to disk |
| Crash Recovery | May lose uncommitted changes | Survives crashes |
| Use Case | Near real-time search | Durability guarantee |

### Commit Options

The `solr_commit` tool supports multiple options:

```python
from solr_mcp.tools import execute_commit

# Hard commit (default) - durable to disk
result = await execute_commit(
    mcp,
    collection="products"
)

# Soft commit - make visible immediately without fsync
result = await execute_commit(
    mcp,
    collection="products",
    soft=True
)

# Hard commit with wait_searcher=False (return immediately)
result = await execute_commit(
    mcp,
    collection="products",
    soft=False,
    wait_searcher=False
)

# Hard commit with expunge_deletes (merge away deleted docs)
result = await execute_commit(
    mcp,
    collection="products",
    soft=False,
    expunge_deletes=True
)
```

### Best Practices

#### Near Real-Time (NRT) Pattern

For applications requiring both speed and durability:

```python
# 1. Add documents without immediate commit
await execute_add_documents(
    mcp,
    collection="products",
    documents=[
        {"id": "PROD-123", "name": "Product 1", "price": 29.99},
        {"id": "PROD-124", "name": "Product 2", "price": 39.99}
    ],
    commit=False
)

# 2. Soft commit for immediate visibility
await execute_commit(mcp, collection="products", soft=True)

# Documents are now searchable immediately

# 3. Hard commit periodically (e.g., every 60 seconds via background job)
await execute_commit(mcp, collection="products", soft=False)

# Documents are now durable to disk
```

#### High-Throughput Indexing

For maximum indexing throughput:

```python
# 1. Index in batches without commits
for batch in document_batches:
    await execute_add_documents(
        mcp,
        collection="products",
        documents=batch,
        commit=False
    )

# 2. Use commitWithin for automatic commits
await execute_add_documents(
    mcp,
    collection="products",
    documents=final_batch,
    commit=False,
    commit_within=10000  # Auto-commit within 10 seconds
)

# 3. Manual soft commit when needed
await execute_commit(mcp, collection="products", soft=True)

# 4. Final hard commit
await execute_commit(mcp, collection="products", soft=False)
```

#### Low-Latency Updates

For updates that must be immediately visible:

```python
# Atomic update with immediate soft commit
await execute_atomic_update(
    mcp,
    collection="products",
    doc_id="PROD-123",
    updates={"stock": {"inc": -1}},
    commit=False  # Don't commit in update
)

# Immediate soft commit for visibility
await execute_commit(mcp, collection="products", soft=True)

# Document is immediately searchable
```

## Real-Time Get

Real-Time Get (RTG) allows you to retrieve documents immediately from the transaction log, even before they've been committed and made searchable.

### How It Works

Solr's Real-Time Get bypasses the search index and retrieves documents from:
1. **Transaction log** for uncommitted changes
2. **Search index** for committed documents

This provides immediate access to the latest document state without waiting for commits.

### Usage Examples

#### Get Single Document

```python
from solr_mcp.tools import execute_realtime_get

result = await execute_realtime_get(
    mcp,
    collection="products",
    doc_ids=["PROD-123"]
)
```

Response:
```json
{
  "docs": [
    {
      "id": "PROD-123",
      "name": "Product 1",
      "price": 29.99,
      "_version_": 1234567890
    }
  ],
  "num_found": 1,
  "collection": "products"
}
```

#### Get Multiple Documents

```python
result = await execute_realtime_get(
    mcp,
    collection="products",
    doc_ids=["PROD-123", "PROD-124", "PROD-125"]
)
```

Response includes all found documents:
```json
{
  "docs": [
    {"id": "PROD-123", "name": "Product 1", "_version_": 123},
    {"id": "PROD-124", "name": "Product 2", "_version_": 124},
    {"id": "PROD-125", "name": "Product 3", "_version_": 125}
  ],
  "num_found": 3,
  "collection": "products"
}
```

#### Get with Field List

Retrieve only specific fields:

```python
result = await execute_realtime_get(
    mcp,
    collection="products",
    doc_ids=["PROD-123"],
    fl="id,name,price"  # Only return these fields
)
```

#### Non-Existent Document

If document doesn't exist:

```python
result = await execute_realtime_get(
    mcp,
    collection="products",
    doc_ids=["NONEXISTENT"]
)

# Returns empty result
{
  "docs": [],
  "num_found": 0,
  "collection": "products"
}
```

### Use Cases

#### Read-After-Write Consistency

Ensure you can read what you just wrote:

```python
# 1. Add document without commit
await execute_add_documents(
    mcp,
    collection="products",
    documents=[{"id": "PROD-NEW", "name": "New Product", "price": 49.99}],
    commit=False
)

# 2. Immediately read it back with RTG
result = await execute_realtime_get(
    mcp,
    collection="products",
    doc_ids=["PROD-NEW"]
)

# Document is available even though not yet committed!
print(result["docs"][0])  # {"id": "PROD-NEW", "name": "New Product", ...}
```

#### Verify Update Before Commit

Verify atomic update was applied correctly:

```python
# 1. Atomic update
await execute_atomic_update(
    mcp,
    collection="products",
    doc_id="PROD-123",
    updates={"price": {"set": 19.99}},
    commit=False
)

# 2. Verify with RTG
result = await execute_realtime_get(
    mcp,
    collection="products",
    doc_ids=["PROD-123"]
)

assert result["docs"][0]["price"] == 19.99  # Verify update

# 3. Commit if verification passed
await execute_commit(mcp, collection="products", soft=True)
```

#### Get Current Version for Optimistic Locking

```python
# Get current document version
doc = await execute_realtime_get(
    mcp,
    collection="products",
    doc_ids=["PROD-123"]
)

current_version = doc["docs"][0]["_version_"]

# Use version for optimistic locking
await execute_atomic_update(
    mcp,
    collection="products",
    doc_id="PROD-123",
    updates={"stock": {"inc": -1}},
    version=current_version
)
```

## Common Workflows

### E-Commerce Inventory Management

Handle concurrent inventory updates with optimistic locking:

```python
async def purchase_product(mcp, product_id, quantity):
    """
    Purchase product with inventory management.
    Uses optimistic locking to prevent overselling.
    """

    max_retries = 3

    for attempt in range(max_retries):
        # 1. Get current stock with RTG
        doc = await execute_realtime_get(
            mcp,
            collection="products",
            doc_ids=[product_id]
        )

        if not doc["docs"]:
            return {"error": "Product not found"}

        product = doc["docs"][0]
        current_stock = product.get("stock", 0)
        current_version = product["_version_"]

        # 2. Check if enough stock
        if current_stock < quantity:
            return {"error": "Insufficient stock"}

        # 3. Attempt to decrement stock with optimistic lock
        try:
            result = await execute_atomic_update(
                mcp,
                collection="products",
                doc_id=product_id,
                updates={
                    "stock": {"inc": -quantity},
                    "last_purchased": {"set": datetime.now().isoformat()}
                },
                version=current_version,
                commit=False
            )

            # 4. Soft commit for immediate visibility
            await execute_commit(mcp, collection="products", soft=True)

            return {
                "status": "success",
                "product_id": product_id,
                "quantity": quantity,
                "new_stock": current_stock - quantity
            }

        except IndexingError as e:
            if "version conflict" in str(e).lower() and attempt < max_retries - 1:
                # Stock changed, retry
                await asyncio.sleep(0.1 * (2 ** attempt))
                continue
            raise

    return {"error": "Purchase failed after retries"}
```

### Real-Time Analytics Dashboard

Update metrics with immediate visibility:

```python
async def record_page_view(mcp, page_id, user_id):
    """
    Record page view with immediate visibility for dashboard.
    """

    # 1. Increment view count atomically
    await execute_atomic_update(
        mcp,
        collection="analytics",
        doc_id=page_id,
        updates={
            "view_count": {"inc": 1},
            "last_viewed": {"set": datetime.now().isoformat()},
            "recent_viewers": {"add": [user_id]}
        },
        commit=False
    )

    # 2. Soft commit for dashboard visibility
    await execute_commit(mcp, collection="analytics", soft=True)

    # 3. Get updated stats with RTG for immediate display
    result = await execute_realtime_get(
        mcp,
        collection="analytics",
        doc_ids=[page_id],
        fl="id,view_count,last_viewed"
    )

    return result["docs"][0]
```

### Near Real-Time Indexing Pipeline

Batch indexing with NRT visibility:

```python
async def index_documents_nrt(mcp, collection, documents, batch_size=100):
    """
    Index documents with near real-time visibility.
    """

    total_indexed = 0

    # 1. Index in batches
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]

        await execute_add_documents(
            mcp,
            collection=collection,
            documents=batch,
            commit=False
        )

        total_indexed += len(batch)
        print(f"Indexed {total_indexed}/{len(documents)} documents")

    # 2. Soft commit for immediate searchability
    await execute_commit(mcp, collection=collection, soft=True)
    print("Documents now searchable")

    # 3. Hard commit for durability (can be async/background)
    await execute_commit(mcp, collection=collection, soft=False)
    print("Documents committed to disk")

    return {"indexed": total_indexed, "committed": True}
```

### Update with Validation

Validate before committing:

```python
async def update_product_price(mcp, product_id, new_price, min_price=0):
    """
    Update product price with validation.
    """

    # 1. Get current product
    doc = await execute_realtime_get(
        mcp,
        collection="products",
        doc_ids=[product_id]
    )

    if not doc["docs"]:
        return {"error": "Product not found"}

    product = doc["docs"][0]
    current_version = product["_version_"]
    current_price = product.get("price", 0)

    # 2. Validate new price
    if new_price < min_price:
        return {"error": f"Price below minimum: {min_price}"}

    # 3. Update with version lock
    await execute_atomic_update(
        mcp,
        collection="products",
        doc_id=product_id,
        updates={
            "price": {"set": new_price},
            "price_updated_at": {"set": datetime.now().isoformat()},
            "previous_price": {"set": current_price}
        },
        version=current_version,
        commit=False
    )

    # 4. Verify update with RTG
    updated_doc = await execute_realtime_get(
        mcp,
        collection="products",
        doc_ids=[product_id]
    )

    if updated_doc["docs"][0]["price"] != new_price:
        return {"error": "Update verification failed"}

    # 5. Soft commit
    await execute_commit(mcp, collection="products", soft=True)

    return {
        "status": "success",
        "product_id": product_id,
        "old_price": current_price,
        "new_price": new_price
    }
```

## Performance Considerations

### Atomic Updates

- **Faster than full reindex**: Only updates specified fields
- **Reduces network traffic**: Don't need to send entire document
- **Index size**: Requires `stored=true` for fields being updated
- **Best for**: Frequent updates to small number of fields

### Commits

#### Soft Commits
- Very fast (milliseconds)
- High frequency possible (every 1-10 seconds)
- Minimal I/O overhead
- Not durable (may lose data on crash)

#### Hard Commits
- Slower (seconds to minutes)
- Lower frequency recommended (every 15-60 seconds)
- Significant I/O overhead (fsync)
- Durable (survives crashes)

#### Recommendations

- **High-throughput**: Use commitWithin instead of immediate commits
- **NRT search**: Soft commits every 1-10 seconds, hard commits every 15-60 seconds
- **Batch indexing**: Commit after batches, not after each document
- **Critical updates**: Hard commit immediately for durability

### Real-Time Get

- **Very fast**: Bypasses search index
- **No commit needed**: Works with uncommitted changes
- **Scalability**: Handle with care on large document sets
- **Best for**: Single document lookups by ID

### Optimistic Concurrency

- **Minimal overhead**: Just version number check
- **Retry logic**: Add exponential backoff for conflicts
- **Conflict rate**: Monitor and adjust retry strategy
- **Best for**: Updates to frequently modified documents

## Troubleshooting

### Atomic Update Fails

**Problem**: Atomic update returns error

**Solutions**:
1. Ensure document exists (use RTG to check)
2. Verify field is `stored=true` in schema
3. Check field type matches operation (numeric for `inc`)
4. Verify multi-valued field for `add`/`remove` operations

```python
# Check document exists first
doc = await execute_realtime_get(mcp, collection="products", doc_ids=["PROD-123"])
if not doc["docs"]:
    print("Document doesn't exist, use add_documents instead")
```

### Version Conflicts

**Problem**: Getting frequent version conflicts

**Solutions**:
1. Implement retry logic with exponential backoff
2. Reduce concurrent update frequency
3. Use higher-level locking if needed
4. Consider partitioning data to reduce conflicts

```python
# Add retry with backoff
for attempt in range(3):
    try:
        await execute_atomic_update(..., version=current_version)
        break
    except IndexingError as e:
        if "version conflict" in str(e).lower():
            await asyncio.sleep(0.1 * (2 ** attempt))
            # Refetch version and retry
```

### Soft Commits Not Visible

**Problem**: Documents not appearing in search after soft commit

**Solutions**:
1. Wait a moment (soft commit is asynchronous)
2. Check commit actually succeeded
3. Verify no errors in Solr logs
4. Use hard commit if immediate visibility critical

```python
# Verify commit succeeded
result = await execute_commit(mcp, collection="products", soft=True)
assert result["status"] == "success"
assert result["committed"] is True
```

### Real-Time Get Returns Empty

**Problem**: RTG returns no documents for known IDs

**Solutions**:
1. Verify document ID is correct (case-sensitive)
2. Check document exists in collection
3. Ensure collection name is correct
4. Try with hard commit first

```python
# Debug RTG issue
result = await execute_realtime_get(
    mcp,
    collection="products",
    doc_ids=["PROD-123"]
)

if not result["docs"]:
    # Try regular query to see if document exists after commit
    query_result = await execute_select_query(
        mcp,
        query="SELECT * FROM products WHERE id = 'PROD-123'"
    )
    print(f"Query found: {query_result['num_docs']} documents")
```

### Memory Issues with Large Commits

**Problem**: Out of memory errors during large commits

**Solutions**:
1. Reduce batch sizes
2. Use commitWithin instead of immediate commits
3. Increase JVM heap size for Solr
4. Spread commits over time

```python
# Use smaller batches with commitWithin
batch_size = 100  # Reduce from 1000
for batch in chunks(documents, batch_size):
    await execute_add_documents(
        mcp,
        collection="products",
        documents=batch,
        commit=False,
        commit_within=10000  # Auto-commit within 10s
    )
```

### Transaction Log Growing Too Large

**Problem**: Transaction log consuming too much disk space

**Solutions**:
1. Increase hard commit frequency
2. Reduce soft commit frequency
3. Monitor transaction log size
4. Configure autoCommit in solrconfig.xml

```python
# More frequent hard commits to flush transaction log
import asyncio

async def periodic_hard_commit(mcp, collection, interval=60):
    """Periodic hard commit every N seconds."""
    while True:
        await asyncio.sleep(interval)
        await execute_commit(
            mcp,
            collection=collection,
            soft=False
        )
        print(f"Hard commit completed at {datetime.now()}")
```

## Additional Resources

- [Solr Atomic Updates Documentation](https://solr.apache.org/guide/solr/latest/indexing-guide/partial-document-updates.html)
- [Solr Real-Time Get Documentation](https://solr.apache.org/guide/solr/latest/query-guide/realtime-get.html)
- [Solr Commits and Optimization](https://solr.apache.org/guide/solr/latest/indexing-guide/commits-transaction-logs.html)
- [Near Real-Time Search](https://solr.apache.org/guide/solr/latest/indexing-guide/near-real-time-searching.html)

## Summary

Phase 1 advanced indexing features provide:

- **Atomic Updates**: Efficient field-level updates with multiple operations
- **Optimistic Concurrency**: Version-based conflict prevention
- **Soft/Hard Commits**: Flexible visibility vs durability trade-offs
- **Real-Time Get**: Immediate document retrieval from transaction log

These features enable building high-performance, real-time applications with Solr while maintaining data consistency and durability.
