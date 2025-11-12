# Highlighting and Stats Component Guide

This guide covers the highlighting and stats features available in the Solr MCP server through the `solr_query` tool.

## Table of Contents

- [Overview](#overview)
- [Highlighting](#highlighting)
  - [Basic Usage](#basic-highlighting-usage)
  - [Configuration Options](#highlighting-configuration)
  - [Highlighting Methods](#highlighting-methods)
  - [Use Cases](#highlighting-use-cases)
- [Stats Component](#stats-component)
  - [Basic Usage](#basic-stats-usage)
  - [Available Statistics](#available-statistics)
  - [Multiple Fields](#stats-on-multiple-fields)
  - [Use Cases](#stats-use-cases)
- [Combined Usage](#combined-highlighting-and-stats)
- [Examples](#real-world-examples)

## Overview

The `solr_query` tool provides access to Solr's standard query parser with support for two powerful components:

- **Highlighting**: Shows WHY documents matched by highlighting matched terms in context
- **Stats Component**: Computes statistical aggregations on numeric fields

These features work with Solr's standard `/select` endpoint and complement the SQL-based `solr_select` tool.

## Highlighting

### Basic Highlighting Usage

Highlighting shows matched terms in context, helping users understand why a document matched their query.

```python
# Basic highlighting example
result = solr_query(
    collection="articles",
    q="machine learning",
    highlight_fields=["title", "content"]
)
```

**Response Structure:**
```json
{
  "num_found": 25,
  "docs": [
    {"id": "1", "title": "Machine Learning Guide"}
  ],
  "highlighting": {
    "1": {
      "title": ["<em>Machine Learning</em> Guide"],
      "content": ["Introduction to <em>machine learning</em> algorithms"]
    }
  }
}
```

### Highlighting Configuration

The `solr_query` tool supports these highlighting parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `highlight_fields` | List[str] | None | Fields to highlight (required to enable highlighting) |
| `highlight_snippets` | int | 3 | Number of snippets per field |
| `highlight_fragsize` | int | 100 | Size of each snippet in characters |
| `highlight_method` | str | "unified" | Highlighting method to use |

**Example with all options:**
```python
result = solr_query(
    collection="articles",
    q="artificial intelligence",
    highlight_fields=["title", "abstract", "content"],
    highlight_snippets=5,        # Up to 5 snippets per field
    highlight_fragsize=200,      # 200 characters per snippet
    highlight_method="unified"   # Use unified highlighter
)
```

### Highlighting Methods

Solr supports three highlighting methods, each with different performance characteristics:

#### 1. Unified Highlighter (Default - Recommended)
```python
highlight_method="unified"
```
- **Best for**: Most use cases
- **Pros**: Fast, accurate, supports all query types
- **Cons**: None for most scenarios

#### 2. Original Highlighter
```python
highlight_method="original"
```
- **Best for**: Complex queries with wildcards/regex
- **Pros**: Most flexible
- **Cons**: Slower than unified

#### 3. FastVector Highlighter
```python
highlight_method="fastVector"
```
- **Best for**: Very large documents
- **Pros**: Fastest for large text
- **Cons**: Requires `termVectors` enabled in schema

### Highlighting Use Cases

#### 1. Search Results Preview
Show users WHY results matched:
```python
result = solr_query(
    collection="documents",
    q="renewable energy",
    fl="id,title,author",
    highlight_fields=["content"],
    highlight_snippets=3,
    highlight_fragsize=150
)

# Display to user:
# Title: "Solar Power Innovations"
# Author: "Dr. Jane Smith"
# ...found in: "...advances in <em>renewable energy</em> technologies..."
```

#### 2. Document Preview
Preview matching sections:
```python
result = solr_query(
    collection="research_papers",
    q="neural networks",
    highlight_fields=["abstract", "introduction", "conclusions"],
    highlight_snippets=2
)
# Shows matched terms in key sections
```

#### 3. Multi-field Search
Highlight across multiple fields:
```python
result = solr_query(
    collection="products",
    q="wireless bluetooth",
    highlight_fields=["title", "description", "features", "reviews"]
)
# Shows where matches occurred in different fields
```

## Stats Component

### Basic Stats Usage

The Stats Component computes statistical aggregations on numeric fields.

```python
result = solr_query(
    collection="products",
    q="*:*",
    stats_fields=["price"]
)
```

**Response Structure:**
```json
{
  "num_found": 100,
  "docs": [...],
  "stats": {
    "price": {
      "min": 9.99,
      "max": 199.99,
      "count": 100,
      "missing": 0,
      "sum": 5499.50,
      "mean": 54.995,
      "stddev": 35.42
    }
  }
}
```

### Available Statistics

For each numeric field, stats component returns:

| Statistic | Description |
|-----------|-------------|
| `min` | Minimum value |
| `max` | Maximum value |
| `count` | Number of documents with this field |
| `missing` | Number of documents without this field |
| `sum` | Sum of all values |
| `mean` | Average value |
| `stddev` | Standard deviation |

### Stats on Multiple Fields

Compute stats for multiple fields simultaneously:

```python
result = solr_query(
    collection="products",
    q="category:electronics",
    stats_fields=["price", "rating", "review_count"]
)
```

**Response:**
```json
{
  "stats": {
    "price": {
      "min": 19.99,
      "max": 499.99,
      "mean": 125.50
    },
    "rating": {
      "min": 1.0,
      "max": 5.0,
      "mean": 4.2
    },
    "review_count": {
      "min": 0,
      "max": 1523,
      "mean": 87.3
    }
  }
}
```

### Stats Use Cases

#### 1. Price Range Discovery
```python
# Find price range for a category
result = solr_query(
    collection="products",
    q="category:laptops",
    rows=0,  # Don't need docs, just stats
    stats_fields=["price"]
)

price_stats = result["stats"]["price"]
print(f"Laptops range from ${price_stats['min']} to ${price_stats['max']}")
print(f"Average price: ${price_stats['mean']:.2f}")
```

#### 2. Data Quality Checks
```python
# Check for missing data
result = solr_query(
    collection="products",
    q="*:*",
    rows=0,
    stats_fields=["price", "weight", "dimensions"]
)

for field, stats in result["stats"].items():
    if stats["missing"] > 0:
        print(f"Warning: {stats['missing']} products missing {field}")
```

#### 3. Trend Analysis
```python
# Analyze rating distribution
result = solr_query(
    collection="products",
    q="launch_year:2024",
    rows=0,
    stats_fields=["rating", "review_count"]
)

rating = result["stats"]["rating"]
print(f"2024 products have average rating: {rating['mean']:.1f}")
print(f"Standard deviation: {rating['stddev']:.2f}")
```

## Combined Highlighting and Stats

Use both features together for rich search results:

```python
result = solr_query(
    collection="books",
    q="data science",
    fl="id,title,author,price",
    rows=10,
    # Highlighting
    highlight_fields=["title", "description"],
    highlight_snippets=2,
    # Stats
    stats_fields=["price", "rating"]
)
```

**Response:**
```json
{
  "num_found": 45,
  "docs": [
    {
      "id": "book123",
      "title": "Data Science Handbook",
      "author": "John Doe",
      "price": 49.99
    }
  ],
  "highlighting": {
    "book123": {
      "title": ["<em>Data Science</em> Handbook"],
      "description": ["Comprehensive guide to <em>data science</em>..."]
    }
  },
  "stats": {
    "price": {
      "min": 19.99,
      "max": 79.99,
      "mean": 45.50,
      "stddev": 15.20
    },
    "rating": {
      "min": 3.5,
      "max": 5.0,
      "mean": 4.3,
      "stddev": 0.45
    }
  }
}
```

## Real-World Examples

### Example 1: E-commerce Search

```python
# Search with highlighting and price stats
result = solr_query(
    collection="products",
    q="wireless headphones",
    fq=["in_stock:true", "category:electronics"],
    sort="price asc",
    rows=20,
    highlight_fields=["name", "description", "features"],
    highlight_snippets=2,
    highlight_fragsize=120,
    stats_fields=["price", "rating"]
)

# Use results:
# 1. Show highlighted search results
for doc in result["docs"]:
    doc_id = doc["id"]
    highlights = result["highlighting"].get(doc_id, {})
    print(f"Title: {doc['name']}")
    if "name" in highlights:
        print(f"  Matched: {highlights['name'][0]}")

# 2. Show price range filter options
price_stats = result["stats"]["price"]
print(f"\nPrice range: ${price_stats['min']} - ${price_stats['max']}")
print(f"Average: ${price_stats['mean']:.2f}")
```

### Example 2: Document Search with Context

```python
# Research paper search
result = solr_query(
    collection="research_papers",
    q="quantum computing applications",
    fq=["year:[2020 TO 2024]", "peer_reviewed:true"],
    fl="id,title,authors,year,citations",
    highlight_fields=["abstract", "introduction", "conclusions"],
    highlight_snippets=3,
    highlight_fragsize=200,
    stats_fields=["citations", "year"]
)

# Show results with context
for doc in result["docs"]:
    print(f"\n{doc['title']} ({doc['year']})")
    print(f"Authors: {', '.join(doc['authors'])}")
    print(f"Citations: {doc['citations']}")

    highlights = result["highlighting"][doc["id"]]
    if "abstract" in highlights:
        print(f"\nAbstract snippet:")
        print(f"  {highlights['abstract'][0]}")

# Show research trends
print(f"\nCitation stats:")
print(f"  Range: {result['stats']['citations']['min']} - {result['stats']['citations']['max']}")
print(f"  Average: {result['stats']['citations']['mean']:.0f}")
```

### Example 3: Blog Search with Snippets

```python
# Blog article search
result = solr_query(
    collection="blog_posts",
    q="machine learning tutorial",
    sort="published_date desc",
    rows=10,
    highlight_fields=["title", "content"],
    highlight_snippets=3,
    highlight_fragsize=150,
    highlight_method="unified",
    stats_fields=["word_count", "read_time"]
)

# Display search results
for doc in result["docs"]:
    doc_id = doc["id"]
    highlights = result["highlighting"][doc_id]

    print(f"\n{doc['title']}")
    print(f"Published: {doc['published_date']}")
    print(f"\nRelevant excerpts:")
    for snippet in highlights.get("content", []):
        print(f"  ...{snippet}...")

# Show content stats
print(f"\nArticle stats:")
print(f"  Average words: {result['stats']['word_count']['mean']:.0f}")
print(f"  Average read time: {result['stats']['read_time']['mean']:.1f} minutes")
```

## Best Practices

### Highlighting Best Practices

1. **Choose appropriate fragment size**:
   - Short snippets (50-100 chars) for previews
   - Long snippets (200+ chars) for context

2. **Limit snippet count**:
   - Use 1-3 snippets for performance
   - More snippets = more processing time

3. **Select relevant fields**:
   - Highlight searchable text fields
   - Avoid highlighting IDs or dates

4. **Use unified highlighter**:
   - Best performance for most cases
   - Only switch if you have specific requirements

### Stats Best Practices

1. **Use `rows=0` for stats-only queries**:
   ```python
   solr_query(q="*:*", rows=0, stats_fields=["price"])
   ```

2. **Combine with filters**:
   ```python
   solr_query(q="*:*", fq=["category:electronics"], stats_fields=["price"])
   ```

3. **Check for missing values**:
   - Always review the `missing` count
   - Consider data quality implications

4. **Use appropriate field types**:
   - Stats work best on numeric fields (pint, pfloat, pdouble)
   - Ensure fields have `docValues` enabled for best performance

## Troubleshooting

### Highlighting Issues

**Problem**: No highlights returned
- **Solution**: Ensure fields are stored and indexed
- **Solution**: Check that query actually matches the fields

**Problem**: Highlights are truncated
- **Solution**: Increase `highlight_fragsize`
- **Solution**: Increase `highlight_snippets`

**Problem**: Slow highlighting performance
- **Solution**: Use unified highlighter (default)
- **Solution**: Reduce number of highlighted fields
- **Solution**: Reduce `highlight_snippets` count

### Stats Issues

**Problem**: No stats returned
- **Solution**: Ensure fields are numeric types
- **Solution**: Check that documents actually have values

**Problem**: Unexpected `missing` count
- **Solution**: Review your data indexing
- **Solution**: Consider making field required or providing defaults

**Problem**: Stats on text fields fail
- **Solution**: Stats only work on numeric fields
- **Solution**: Use faceting for text field analysis instead

## API Reference

### solr_query Parameters

```python
solr_query(
    collection: str,           # Collection name (required)
    q: str = "*:*",           # Query string
    fq: List[str] = None,     # Filter queries
    fl: str = None,           # Fields to return
    rows: int = 10,           # Number of results
    start: int = 0,           # Pagination offset
    sort: str = None,         # Sort specification

    # Highlighting
    highlight_fields: List[str] = None,
    highlight_snippets: int = 3,
    highlight_fragsize: int = 100,
    highlight_method: str = "unified",

    # Stats
    stats_fields: List[str] = None
)
```

## Further Reading

- [Solr Highlighting Documentation](https://solr.apache.org/guide/solr/latest/query-guide/highlighting.html)
- [Solr Stats Component Documentation](https://solr.apache.org/guide/solr/latest/query-guide/stats-component.html)
- [Solr Query Syntax](https://solr.apache.org/guide/solr/latest/query-guide/standard-query-parser.html)
