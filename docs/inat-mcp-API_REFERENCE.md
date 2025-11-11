# iNaturalist MCP Server API Reference

**Version:** 1.0.0
**Protocol:** Model Context Protocol (MCP)
**Transport:** HTTP/SSE or STDIO
**Base URL:** `http://your-server:8811` (for HTTP/SSE deployment)

---

## Table of Contents

1. [Overview](#overview)
2. [Connection Methods](#connection-methods)
3. [MCP Protocol Basics](#mcp-protocol-basics)
4. [Tool Reference](#tool-reference)
   - [search_species](#search_species)
   - [get_species_info](#get_species_info)
   - [search_places](#search_places)
   - [count_observations](#count_observations)
   - [list_recent_observations](#list_recent_observations)
   - [health_check](#health_check)
   - [get_config_status](#get_config_status)
   - [get_cache_stats](#get_cache_stats)
5. [Error Handling](#error-handling)
6. [Code Examples](#code-examples)
7. [Performance & Caching](#performance--caching)

---

## Overview

The iNaturalist MCP Server provides programmatic access to iNaturalist biodiversity data through the Model Context Protocol (MCP). It exposes 8 tools for searching species, places, and observations, with built-in caching and error handling.

**Key Features:**
- **Persistent SQLite cache** (50-200× performance improvement)
- **Exponential backoff retry** with circuit breaker
- **Flexible input** (accept both IDs and human-readable names)
- **Domain-specific errors** (clear error messages, not stack traces)
- **Production-ready** (validated on TrueNAS Scale)

**Use Cases:**
- Biodiversity data analysis applications
- Educational tools and citizen science platforms
- Research data collection pipelines
- Conservation monitoring dashboards
- Species identification systems

---

## Connection Methods

### Option 1: HTTP/SSE Transport (Remote)

For programmatic access from any language/platform:

```bash
# Server runs on port 8811 by default
curl http://192.168.51.99:8811/sse
```

**Connection URL:** `http://your-server:8811/sse`
**Protocol:** Server-Sent Events (SSE) for notifications + HTTP POST for requests

### Option 2: STDIO Transport (Local)

For local processes on the same machine:

```bash
docker exec -i inat-mcp-server python -m inat_mcp.server.stdio
```

**Protocol:** JSON-RPC over stdin/stdout

### Recommended: Use MCP SDK

The easiest way to integrate is using the official MCP SDK for your language:

**Python:**
```python
from mcp import ClientSession
from mcp.client.sse import sse_client

async with sse_client("http://192.168.51.99:8811/sse") as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        # Use tools here
```

**TypeScript/JavaScript:**
```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

const transport = new SSEClientTransport(new URL("http://192.168.51.99:8811/sse"));
const client = new Client({ name: "my-app", version: "1.0.0" }, { capabilities: {} });
await client.connect(transport);
```

---

## MCP Protocol Basics

### Tool Invocation

MCP tools are invoked using JSON-RPC 2.0 messages:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_species",
    "arguments": {
      "query": "monarch butterfly",
      "limit": 5
    }
  }
}
```

### Response Format

Successful responses:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"results\": [...], \"metadata\": {...}}"
      }
    ]
  }
}
```

Error responses:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32000,
    "message": "Taxon ID 999999 not found in iNaturalist database"
  }
}
```

---

## Tool Reference

### search_species

Search for species by name with fuzzy matching.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | Yes | - | Species name to search for (scientific or common) |
| `limit` | integer | No | 10 | Maximum results (1-100) |

**Returns:**

```json
{
  "results": [
    {
      "taxon_id": 48662,
      "name": "Danaus plexippus",
      "common_name": "Monarch",
      "rank": "species",
      "preferred_common_name": "Monarch",
      "observations_count": 847538,
      "wikipedia_url": "https://en.wikipedia.org/wiki/Monarch_butterfly",
      "iconic_taxon_name": "Insecta",
      "conservation_status": null
    }
  ],
  "metadata": {
    "query": "monarch butterfly",
    "limit": 10,
    "total_results": 1,
    "cache_hit": false
  }
}
```

**Example Usage:**

```python
result = await session.call_tool("search_species", {
    "query": "luna moth",
    "limit": 5
})
```

**Use Cases:**
- Autocomplete for species search fields
- Finding taxon IDs for downstream queries
- Species name disambiguation
- Building species catalogs

**Performance:**
- **Cache TTL:** 7 days (species data rarely changes)
- **Typical latency:** 10-50ms (cached), 200-800ms (uncached)

---

### get_species_info

Get detailed information about a specific species by taxon ID.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `taxon_id` | integer | Yes | iNaturalist taxon ID |

**Returns:**

```json
{
  "taxon_id": 47157,
  "name": "Lepidoptera",
  "common_name": "Butterflies and Moths",
  "rank": "order",
  "preferred_common_name": "Butterflies and Moths",
  "observations_count": 5847291,
  "wikipedia_url": "https://en.wikipedia.org/wiki/Lepidoptera",
  "iconic_taxon_name": "Insecta",
  "conservation_status": null,
  "complete_species_count": 180943,
  "ancestry": "48460/1/47120/372739/47158",
  "photo_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/...",
  "default_photo": {
    "square_url": "https://...",
    "medium_url": "https://...",
    "attribution": "..."
  }
}
```

**Example Usage:**

```python
result = await session.call_tool("get_species_info", {
    "taxon_id": 48662  # Monarch butterfly
})
```

**Use Cases:**
- Species detail pages
- Taxonomy lookups
- Building species hierarchies
- Photo retrieval for UI

**Performance:**
- **Cache TTL:** 7 days
- **Typical latency:** 10-50ms (cached), 200-800ms (uncached)

**Error Cases:**
- Invalid taxon ID → `ValueError: Taxon ID 999999 not found in iNaturalist database`
- API timeout → Automatic retry with exponential backoff

---

### search_places

Search for geographic places by name (countries, states, counties, parks, etc.).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | Yes | - | Place name to search for |
| `limit` | integer | No | 10 | Maximum results (1-100) |

**Returns:**

```json
{
  "results": [
    {
      "id": 1,
      "name": "United States",
      "display_name": "United States",
      "admin_level": 0,
      "bbox_area": 5306.81,
      "location": "37.5,-120.37",
      "ancestor_place_ids": [97394, 97391, 97389],
      "place_type": "country"
    }
  ],
  "metadata": {
    "query": "United States",
    "limit": 10,
    "total_results": 1,
    "cache_hit": false
  }
}
```

**Example Usage:**

```python
result = await session.call_tool("search_places", {
    "query": "Door County, Wisconsin",
    "limit": 5
})
place_id = result["results"][0]["id"]  # 1499
```

**Use Cases:**
- Geographic search autocomplete
- Finding place IDs for observation queries
- Building location hierarchies
- Map integration

**Performance:**
- **Cache TTL:** 24 hours (place data rarely changes)
- **Typical latency:** 10-50ms (cached), 200-800ms (uncached)

**Special Features:**
- **Exact match prioritization:** Searching "United States" returns "United States" first, not "United States Virgin Islands"
- **Fuzzy matching:** Handles typos and partial matches
- **Admin levels:** Returns hierarchy information (country, state, county)

---

### count_observations

Count observations matching filters (location, species, year).

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `taxon_id` | integer | No* | iNaturalist taxon ID to filter by |
| `taxon_name` | string | No* | Species name (will be resolved to taxon_id) |
| `place_id` | integer | No* | iNaturalist place ID to filter by |
| `place_name` | string | No* | Place name (will be resolved to place_id) |
| `year` | integer | No | Year to filter by (e.g., 2024) |
| `quality_grade` | string | No | Quality filter: "research", "needs_id", "casual" |

**Note:** Either `taxon_id` or `taxon_name` must be provided. Either `place_id` or `place_name` must be provided.

**Returns:**

```json
{
  "total_results": 4,
  "taxon_id": 47922,
  "taxon_name": "Actias luna",
  "place_id": 1499,
  "place_name": "Door County, WI, US",
  "year": 2024,
  "quality_grade": "research",
  "query_url": "https://www.inaturalist.org/observations?taxon_id=47922&place_id=1499&year=2024&quality_grade=research"
}
```

**Example Usage:**

```python
# Using IDs (fastest - no name resolution)
result = await session.call_tool("count_observations", {
    "taxon_id": 47922,    # Actias luna
    "place_id": 1499,      # Door County, WI
    "year": 2024
})

# Using names (user-friendly)
result = await session.call_tool("count_observations", {
    "taxon_name": "luna moth",
    "place_name": "Door County, Wisconsin",
    "year": 2024
})
```

**Use Cases:**
- Biodiversity dashboards
- Conservation monitoring
- Citizen science metrics
- Research data collection

**Performance:**
- **Cache TTL:** 1 hour (observation counts change frequently)
- **Typical latency:** 10-50ms (cached), 200-800ms (uncached)
- **Name resolution:** Adds 1-2 API calls if using names instead of IDs

---

### list_recent_observations

List recent observations matching filters.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `taxon_id` | integer | No* | iNaturalist taxon ID to filter by |
| `taxon_name` | string | No* | Species name (will be resolved to taxon_id) |
| `place_id` | integer | No* | iNaturalist place ID to filter by |
| `place_name` | string | No* | Place name (will be resolved to place_id) |
| `limit` | integer | No | Maximum results (default: 10) |
| `quality_grade` | string | No | Quality filter: "research", "needs_id", "casual" |

**Note:** At least one of `taxon_id`/`taxon_name` or `place_id`/`place_name` must be provided.

**Returns:**

```json
{
  "results": [
    {
      "id": 12345678,
      "observed_on": "2024-10-15",
      "quality_grade": "research",
      "location": "43.5,-87.2",
      "place_guess": "Door County, WI, US",
      "user": {
        "login": "naturalist123"
      },
      "photos": [
        {
          "url": "https://inaturalist-open-data.s3.amazonaws.com/photos/..."
        }
      ],
      "taxon": {
        "id": 47922,
        "name": "Actias luna",
        "common_name": "Luna Moth"
      }
    }
  ],
  "metadata": {
    "total_results": 4,
    "taxon_id": 47922,
    "place_id": 1499,
    "limit": 10,
    "cache_hit": false
  }
}
```

**Example Usage:**

```python
# Recent monarchs in California
result = await session.call_tool("list_recent_observations", {
    "taxon_name": "monarch butterfly",
    "place_name": "California",
    "limit": 5
})

for obs in result["results"]:
    print(f"Observed on {obs['observed_on']} at {obs['place_guess']}")
```

**Use Cases:**
- Real-time observation feeds
- Species occurrence mapping
- Photo galleries
- User activity tracking

**Performance:**
- **Cache TTL:** 15 minutes (recent observations change frequently)
- **Typical latency:** 10-50ms (cached), 200-800ms (uncached)

---

### health_check

Check server health and API connectivity.

**Parameters:** None

**Returns:**

```json
{
  "status": "healthy",
  "api_status": "connected",
  "cache_status": "operational",
  "timestamp": "2024-10-15T10:30:45.123Z",
  "version": "1.0.0"
}
```

**Example Usage:**

```python
result = await session.call_tool("health_check", {})
if result["status"] == "healthy":
    print("Server is ready")
```

**Use Cases:**
- Monitoring dashboards
- Health checks in CI/CD
- Service discovery
- Load balancer health probes

**Performance:**
- **No caching** (always fresh)
- **Typical latency:** 50-150ms

---

### get_config_status

Get server configuration details.

**Parameters:** None

**Returns:**

```json
{
  "taxon_scope": {
    "scope": "taxon_id",
    "taxon_id": 47157,
    "taxon_name": "Lepidoptera",
    "include_descendants": true
  },
  "geographic_scope": {
    "type": "global",
    "countries": [],
    "regions": [],
    "places": []
  },
  "optimization": {
    "profile": "lepidoptera",
    "cache_enabled": true,
    "cache_backend": "sqlite"
  },
  "rate_limiting": {
    "max_requests_per_minute": 60,
    "timeout_seconds": 30,
    "max_retries": 3
  }
}
```

**Example Usage:**

```python
result = await session.call_tool("get_config_status", {})
print(f"Taxon scope: {result['taxon_scope']['taxon_name']}")
print(f"Cache enabled: {result['optimization']['cache_enabled']}")
```

**Use Cases:**
- Configuration validation
- Debugging scope issues
- Monitoring configuration drift
- Documentation generation

**Performance:**
- **No caching** (always fresh)
- **Typical latency:** 5-10ms (no API calls)

---

### get_cache_stats

Get cache performance statistics.

**Parameters:** None

**Returns:**

```json
{
  "backend": "sqlite",
  "total_entries": 1247,
  "hit_rate": 0.73,
  "total_hits": 8234,
  "total_misses": 3012,
  "avg_hit_latency_ms": 12.5,
  "avg_miss_latency_ms": 450.2,
  "cache_size_mb": 15.7
}
```

**Example Usage:**

```python
result = await session.call_tool("get_cache_stats", {})
print(f"Cache hit rate: {result['hit_rate'] * 100:.1f}%")
print(f"Average cached latency: {result['avg_hit_latency_ms']}ms")
```

**Use Cases:**
- Performance monitoring
- Cache optimization
- Capacity planning
- Troubleshooting slow queries

**Performance:**
- **No caching** (always fresh)
- **Typical latency:** 10-20ms

---

## Error Handling

### Error Types

The server returns domain-specific errors for common issues:

**1. Invalid Input**
```json
{
  "error": {
    "code": -32602,
    "message": "Limit must be between 1 and 100. Requested: 1000"
  }
}
```

**2. Not Found**
```json
{
  "error": {
    "code": -32000,
    "message": "Taxon ID 999999 not found in iNaturalist database"
  }
}
```

**3. API Errors**
```json
{
  "error": {
    "code": -32000,
    "message": "iNaturalist API request failed after 3 retries: 503 Service Unavailable"
  }
}
```

**4. Circuit Breaker Open**
```json
{
  "error": {
    "code": -32000,
    "message": "Circuit breaker open: too many API failures. Try again in 60 seconds."
  }
}
```

### Error Handling Best Practices

```python
from mcp import ClientSession

async def safe_search_species(session, query):
    try:
        result = await session.call_tool("search_species", {
            "query": query,
            "limit": 10
        })
        return result
    except Exception as e:
        if "not found" in str(e).lower():
            return {"results": [], "metadata": {"error": "not_found"}}
        elif "circuit breaker" in str(e).lower():
            # Wait and retry
            await asyncio.sleep(60)
            return await safe_search_species(session, query)
        else:
            # Log and re-raise
            logger.error(f"Unexpected error: {e}")
            raise
```

---

## Code Examples

### Example 1: Species Search Application

```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def species_search_app(query: str):
    """Search for species and display results."""
    async with sse_client("http://192.168.51.99:8811/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Search for species
            result = await session.call_tool("search_species", {
                "query": query,
                "limit": 5
            })

            print(f"\nFound {len(result['results'])} species:\n")
            for species in result['results']:
                print(f"  • {species['preferred_common_name']} ({species['name']})")
                print(f"    Taxon ID: {species['taxon_id']}")
                print(f"    Observations: {species['observations_count']:,}")
                print()

# Run
asyncio.run(species_search_app("luna moth"))
```

### Example 2: Observation Counter

```python
async def count_observations_app(species: str, location: str, year: int):
    """Count observations for species in location during year."""
    async with sse_client("http://192.168.51.99:8811/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Count observations
            result = await session.call_tool("count_observations", {
                "taxon_name": species,
                "place_name": location,
                "year": year,
                "quality_grade": "research"
            })

            print(f"\n{result['total_results']} observations of {species}")
            print(f"in {location} during {year}")
            print(f"\nView on iNaturalist: {result['query_url']}")

# Run
asyncio.run(count_observations_app(
    species="monarch butterfly",
    location="California",
    year=2024
))
```

### Example 3: Recent Observations Feed

```python
async def recent_observations_feed(species: str, limit: int = 10):
    """Display recent observations of a species."""
    async with sse_client("http://192.168.51.99:8811/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get recent observations
            result = await session.call_tool("list_recent_observations", {
                "taxon_name": species,
                "limit": limit
            })

            print(f"\nRecent {species} observations:\n")
            for obs in result['results']:
                print(f"  • {obs['observed_on']} - {obs['place_guess']}")
                print(f"    by {obs['user']['login']}")
                if obs.get('photos'):
                    print(f"    Photo: {obs['photos'][0]['url']}")
                print()

# Run
asyncio.run(recent_observations_feed("sphinx vashti", limit=5))
```

### Example 4: TypeScript/Node.js Integration

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

async function searchSpecies(query: string, limit: number = 10) {
  const transport = new SSEClientTransport(
    new URL("http://192.168.51.99:8811/sse")
  );

  const client = new Client(
    { name: "species-app", version: "1.0.0" },
    { capabilities: {} }
  );

  await client.connect(transport);

  const result = await client.callTool("search_species", {
    query: query,
    limit: limit
  });

  console.log(JSON.stringify(result, null, 2));

  await client.close();
}

// Run
searchSpecies("luna moth", 5);
```

### Example 5: Monitoring Dashboard

```python
async def monitoring_dashboard():
    """Display server health and cache statistics."""
    async with sse_client("http://192.168.51.99:8811/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get health status
            health = await session.call_tool("health_check", {})

            # Get cache stats
            cache = await session.call_tool("get_cache_stats", {})

            # Get config
            config = await session.call_tool("get_config_status", {})

            print("=== Server Status ===")
            print(f"Status: {health['status']}")
            print(f"API: {health['api_status']}")
            print(f"Version: {health['version']}")
            print()

            print("=== Cache Performance ===")
            print(f"Hit rate: {cache['hit_rate'] * 100:.1f}%")
            print(f"Total entries: {cache['total_entries']:,}")
            print(f"Avg hit latency: {cache['avg_hit_latency_ms']:.1f}ms")
            print(f"Avg miss latency: {cache['avg_miss_latency_ms']:.1f}ms")
            print(f"Cache size: {cache['cache_size_mb']:.1f} MB")
            print()

            print("=== Configuration ===")
            print(f"Taxon scope: {config['taxon_scope']['taxon_name']}")
            print(f"Cache backend: {config['optimization']['cache_backend']}")
            print(f"Rate limit: {config['rate_limiting']['max_requests_per_minute']}/min")

# Run
asyncio.run(monitoring_dashboard())
```

---

## Performance & Caching

### Cache Strategy

The server uses a tiered caching strategy based on data volatility:

| Tool | Cache TTL | Rationale |
|------|-----------|-----------|
| `search_species` | 7 days | Species taxonomy rarely changes |
| `get_species_info` | 7 days | Species metadata stable |
| `search_places` | 24 hours | Place data mostly stable |
| `count_observations` | 1 hour | Observation counts change frequently |
| `list_recent_observations` | 15 minutes | Recent observations very dynamic |
| `health_check` | No cache | Always fresh status |
| `get_config_status` | No cache | Configuration changes |
| `get_cache_stats` | No cache | Live statistics |

### Performance Optimization Tips

1. **Use IDs instead of names when possible**
   ```python
   # Slower (requires name resolution)
   count_observations(taxon_name="luna moth", place_name="Wisconsin")

   # Faster (direct API call)
   count_observations(taxon_id=47922, place_id=1428)
   ```

2. **Limit result sizes**
   ```python
   # Don't request more data than you need
   search_species(query="butterfly", limit=10)  # Not 100
   ```

3. **Batch requests**
   ```python
   # Use parallel requests for independent queries
   results = await asyncio.gather(
       session.call_tool("search_species", {"query": "monarch"}),
       session.call_tool("search_species", {"query": "luna moth"}),
       session.call_tool("search_species", {"query": "sphinx vashti"})
   )
   ```

4. **Monitor cache performance**
   ```python
   # Check cache stats regularly
   stats = await session.call_tool("get_cache_stats", {})
   if stats['hit_rate'] < 0.5:
       # Consider warming cache or adjusting query patterns
       pass
   ```

### Expected Latencies

| Scenario | Latency | Notes |
|----------|---------|-------|
| Cache hit | 10-50ms | SQLite lookup |
| Cache miss (single API call) | 200-800ms | iNaturalist API latency |
| Cache miss (with name resolution) | 400-1600ms | 2-3 API calls |
| API timeout/retry | 5-15s | Exponential backoff |
| Circuit breaker open | 0ms (immediate error) | After 5 consecutive failures |

---

## Advanced Topics

### Rate Limiting

The server respects iNaturalist API rate limits:
- **Default:** 60 requests/minute
- **Timeout:** 30 seconds per request
- **Max retries:** 3 (with exponential backoff)

**Circuit Breaker:**
- Opens after 5 consecutive API failures
- Closes after 60 seconds
- Prevents cascading failures

### Name Resolution

When using `taxon_name` or `place_name` parameters:

1. Server searches for the name (cached for 7/24 hours)
2. Selects the best match (exact match prioritized)
3. Uses the resolved ID for the main query

**Trade-offs:**
- ✅ User-friendly (no need to look up IDs)
- ✅ Cached (fast for repeated queries)
- ❌ Adds 1-2 API calls on cache miss
- ❌ Ambiguous names may match wrong entity

### Quality Grades

iNaturalist observations have three quality levels:

- **`research`**: Verified by experts, suitable for scientific research
- **`needs_id`**: Photos present but needs community ID
- **`casual`**: Incomplete or cultivated specimens

**Recommendation:** Use `quality_grade="research"` for data analysis.

---

## Troubleshooting

### Common Issues

**1. Connection refused**
```
Error: Failed to connect to http://192.168.51.99:8811/sse
```
→ Check server is running: `docker ps | grep inat-mcp`

**2. Slow queries**
```
Warning: Query took 5.2 seconds
```
→ Check cache stats: `get_cache_stats`
→ Use IDs instead of names
→ Reduce `limit` parameter

**3. Empty results**
```
{"results": [], "total_results": 0}
```
→ Try broader search terms
→ Check spelling
→ Verify taxon/place IDs are correct

**4. Circuit breaker open**
```
Error: Circuit breaker open: too many API failures
```
→ Wait 60 seconds
→ Check iNaturalist API status: https://www.inaturalist.org/pages/api+recommended+practices

---

## Support & Resources

- **GitHub:** https://github.com/coloradeo/inat-mcp
- **Issues:** https://github.com/coloradeo/inat-mcp/issues
- **iNaturalist API Docs:** https://api.inaturalist.org/v1/docs/
- **MCP Specification:** https://modelcontextprotocol.io/

---

## License

MIT License - See LICENSE file for details.

---

**Generated with Claude Code** 🤖
**Version:** 1.0.0
**Last Updated:** 2024-10-15
