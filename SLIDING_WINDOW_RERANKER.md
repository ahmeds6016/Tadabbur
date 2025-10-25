# Sliding Window Reranker Implementation

## Overview

This document describes the sliding window approach implemented for the Jina reranker to handle large chunks that exceed the model's token limit.

## Problem Statement

- **Model Limit**: `jinaai/jina-reranker-v2-base-multilingual` has a **1024 token limit** for query + document combined
- **Chunk Sizes**: Your tafsir chunks can be up to **18K tokens**
- **Previous Issue**: Chunks were likely being silently truncated, losing critical context

## Solution: Sliding Window Approach

### Key Components

1. **Token Limit Correction**
   - Updated from incorrect 8192 to actual 1024 tokens
   - Limit includes both query and document text
   - Reserved ~150 tokens for typical queries

2. **Sliding Window Algorithm**
   - Splits large documents into overlapping windows
   - Each window: max 874 tokens (1024 - 150 for query)
   - Overlap: 200 tokens between consecutive windows
   - Ensures complete coverage without losing context

3. **Score Aggregation**
   - **Strategy**: Max pooling
   - Takes the highest score from all windows
   - Rationale: If ANY part is highly relevant, the chunk is relevant

## Implementation Details

### Configuration (app.py lines 73-93)

```python
RERANKER_MODELS = [
    {
        "name": "jinaai/jina-reranker-v2-base-multilingual",
        "max_length": 1024,  # Total limit for query + document
        "supports_sliding_window": True,
        "window_overlap": 200,
        "query_reserved_tokens": 150,
        "max_document_tokens": 874,  # 1024 - 150
    },
    ...
]
```

### Sliding Window Function (app.py lines 1603-1690)

The `create_sliding_windows()` function:
1. Uses tokenizer for accurate token counting (if available)
2. Falls back to character-based approximation (4 chars ≈ 1 token)
3. Returns list of (window_text, start_pos, end_pos) tuples

### Reranking with Windows (app.py lines 1734-1808)

The updated `rerank_chunks()` function:
1. Detects if chunks need sliding windows
2. Scores each window separately
3. Applies max pooling for final score
4. Tracks statistics for monitoring

## Monitoring

### Health Endpoint (`/health`)

Added sliding window status:
- `sliding_window_active`: Whether any chunks have used windows
- `windows_processed`: Total number of windows processed

### Reranker Stats Endpoint (`/reranker-stats`)

Detailed sliding window statistics:
```json
{
  "sliding_window": {
    "enabled": true,
    "tokenizer_loaded": true,
    "chunks_using_windows": 145,
    "total_windows_processed": 3567,
    "avg_windows_per_chunk": 24.6,
    "window_usage_rate": "15.3%"
  }
}
```

## Performance Impact

### Expected Behavior

| Chunk Size | Windows Needed | Processing Time |
|------------|---------------|-----------------|
| < 1K tokens | 1 (no sliding) | ~50ms |
| 2K tokens | 2-3 | ~100-150ms |
| 5K tokens | 6-7 | ~300-350ms |
| 18K tokens | 20-25 | ~1000-1250ms |

### Optimization Notes

- Windows are processed in batch for efficiency
- Thread-safe with global reranker lock
- Fallback to character approximation if tokenizer fails

## Testing

Use the provided test script to verify sliding window behavior:

```bash
python test_sliding_window.py
```

The script will:
1. Check service health
2. Get initial statistics
3. Run test queries of varying complexity
4. Analyze sliding window usage
5. Report detailed statistics

## Debugging

### Chunk-Level Information

Each chunk now includes debugging fields when sliding windows are used:
- `window_count`: Number of windows used
- `window_scores`: Individual scores for each window
- `rerank_strategy`: "sliding_window_max", "single_window", or "direct"

### Logging

The reranker logs sliding window usage:
```
📊 Large chunk used 23 windows (chunk_id: ibn-kathir:2:183)
Sliding windows: 5 chunks used 87 windows (avg: 17.4 per chunk)
```

## Fallback Behavior

If tokenizer is not available:
1. Uses character-based approximation (less accurate)
2. Logs warning about potential inaccuracy
3. Still provides sliding window functionality

If sliding window fails completely:
1. Truncates to first 3000 characters
2. Logs truncation event
3. Increments `chunks_truncated` counter

## Future Improvements

1. **Alternative Aggregation Strategies**
   - Mean pooling (average of all windows)
   - Weighted by position (early windows weighted higher)
   - Learnable aggregation based on query type

2. **Performance Optimizations**
   - Batch processing of windows from multiple chunks
   - Caching of window embeddings
   - Parallel processing with multiple model instances

3. **Advanced Features**
   - Dynamic window size based on content density
   - Smart overlap adjustment based on semantic boundaries
   - Query-aware window selection

## Conclusion

The sliding window implementation ensures that no content is lost due to token limits, maintaining the full context of even the largest tafsir chunks (up to 18K tokens). This results in more accurate reranking and better search results, especially for detailed theological explanations that require extensive context.