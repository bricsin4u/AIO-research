# Rust AIO SDK Documentation

**Crate**: `aio_parser`  
**Version**: `0.8.0`  
**License**: MIT

The Rust SDK provides a memory-safe, zero-copy parsing implementation for systems where performance and reliability are critical (e.g., embedded devices, high-frequency trading context injection).

---

## Installation

Add to `Cargo.toml`:

```toml
[dependencies]
aio-parser = "0.8"
tokio = { version = "1", features = ["full"] }
```

---

## Quick Start

```rust
use aio_parser::{Parser, Result};

#[tokio::main]
async fn main() -> Result<()> {
    // 1. Initialize
    let parser = Parser::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()?;

    // 2. Parse (Async)
    let envelope = parser.parse("https://example.com").await?;

    println!("Detected Source: {:?}", envelope.source_type);
    println!("Content: {}", envelope.narrative);

    Ok(())
}
```

---

## API Reference

### `Parser` Struct

The main entry point. Implement `Clone` and is cheap to copy.

#### `parse(&self, url: &str) -> impl Future<Output = Result<ContentEnvelope>>`
Fetches content. Automatically handles discovery fallbacks.

#### `parse_targeted(&self, url: &str, query: &str) -> impl Future`
Optimized fetch that requests filtered content from the server.

### `ContentEnvelope` Struct

```rust
#[derive(Debug, Serialize, Deserialize)]
pub struct ContentEnvelope {
    pub id: String,
    pub source_url: Url,
    pub source_type: SourceType,
    pub narrative: String,
    pub tokens: usize,
    pub chunks: Vec<Chunk>,
    pub metadata: HashMap<String, String>,
}
```

### `SourceType` Enum

```rust
pub enum SourceType {
    AIO,      // Verified AIO content
    Scraped,  // Fallback HTML extraction
    Cached,   // From local/edge cache
}
```

---

## Advanced Usage

### 1. Zero-Copy Deserialization
For maximum performance, the SDK uses `Cow<'a, str>` internally to avoid unnecessary string cloning during JSON parsing.

### 2. Custom Transport
You can inject your own `reqwest::Client` for authentication or proxy settings.

```rust
let client = reqwest::Client::builder()
    .proxy(reqwest::Proxy::all("http://secure-proxy:8080")?)
    .build()?;

let parser = Parser::builder()
    .client(client)
    .build()?;
```

---
[Crate.io](https://crates.io/crates/aio-parser) | [Docs.rs](https://docs.rs/aio-parser)
