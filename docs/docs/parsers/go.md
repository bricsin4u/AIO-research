# Go AIO SDK Documentation

**Module**: `github.com/aifusion/aio-parser-go`  
**Version**: `0.9.0`  
**License**: MIT

The Go SDK is built for high-throughput crawling pipelines and Kubernetes-native operators. It prioritizes zero-allocation parsing where possible and strict type safety.

---

## Installation

```bash
go get github.com/aifusion/aio-parser-go
```

---

## Quick Start

```go
package main

import (
    "fmt"
    "log"
    "github.com/aifusion/aio-parser-go"
)

func main() {
    // 1. Create a Parser instance (reusable)
    client := aio.NewParser(aio.Config{
        Timeout: 10,
        UserAgent: "MyCrawler/1.0",
    })

    // 2. Parse URL
    envelope, err := client.Parse("https://example.com/article")
    if err != nil {
        log.Fatalf("Failed: %v", err)
    }

    fmt.Printf("Source: %s\n", envelope.SourceType)
    fmt.Printf("Tokens: %d\n", envelope.Tokens)
}
```

---

## API Reference

### `NewParser(config Config) *Parser`

Creates a new parser instance. Recommended to keep a singleton instance for connection pooling.

**Config Struct**:
```go
type Config struct {
    Timeout   int    // Seconds (Default: 10)
    UserAgent string // (Default: AIO-Go)
    Retries   int    // (Default: 0)
}
```

### `Parse(url string, query ...string) (*ContentEnvelope, error)`

Fetches and parses content.

- `url`: Target URL.
- `query`: Optional varargs for targeted retrieval keywords.

Returns `*ContentEnvelope` or error.

### `ContentEnvelope` Struct

```go
type ContentEnvelope struct {
    ID          string
    SourceURL   string
    SourceType  SourceType // "aio" | "scraped"
    Narrative   string     // Markdown content
    Tokens      int
    NoiseScore  float64
    Chunks      []Chunk
    GeneratedAt time.Time
}
```

---

## Patterns

### 1. High-Concurrency Crawling
Go's goroutines make it easy to process thousands of URLs.

```go
func worker(urls <-chan string, results chan<- *aio.ContentEnvelope) {
    p := aio.NewParser(aio.DefaultConfig())
    for url := range urls {
        if res, err := p.Parse(url); err == nil {
            results <- res
        }
    }
}
```

### 2. Error Handling
The SDK exports specific error types for robust handling.

```go
if err != nil {
    switch e := err.(type) {
    case *aio.DiscoveryError:
        // No AIO found, and scraping failed
    case *aio.ValidationError:
        // JSON schema invalid
    default:
        // Network or unknown error
    }
}
```

---
[GitHub Repository](https://github.com/aifusion/aio-parser-go) | [GoDoc](https://pkg.go.dev/github.com/aifusion/aio-parser-go)
