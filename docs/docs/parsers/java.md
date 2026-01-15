# Java AIO SDK Documentation

**Group**: `com.aifusion`  
**Artifact**: `aio-parser`  
**Version**: `1.0.0`  
**License**: MIT

The Java SDK is designed for Enterprise Backend environments (Spring Boot, Jakarta EE). It follows robust object-oriented patterns and integrates seamlessly with standard Java HTTP clients.

---

## Installation

**Maven**:
```xml
<dependency>
    <groupId>com.aifusion</groupId>
    <artifactId>aio-parser</artifactId>
    <version>1.0.0</version>
</dependency>
```

**Gradle**:
```groovy
implementation 'com.aifusion:aio-parser:1.0.0'
```

---

## Quick Start

```java
import com.aifusion.aio.AIOParser;
import com.aifusion.aio.model.ContentEnvelope;

public class Main {
    public static void main(String[] args) {
        // 1. Instantiate (Thread-Safe)
        AIOParser parser = new AIOParser();

        try {
            // 2. Fetch
            ContentEnvelope result = parser.parse("https://example.com");

            System.out.println("Status: " + result.getStatus());
            System.out.println("Narrative: " + result.getNarrative());

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

---

## API Reference

### `AIOParser` Class

#### `public ContentEnvelope parse(String url)`
Retrieves content using the default protocol discovery chain.

#### `public ContentEnvelope parse(String url, String query)`
Performs **Targeted Retrieval**. Only fetches chunks relevant to the `query`.

### `ContentEnvelope` POJO

Can be serialized easily to JSON (Jackson/Gson).

```java
public class ContentEnvelope {
    private String id;
    private String sourceUrl;
    private SourceType sourceType; // ENUM: AIO, SCRAPED
    private String narrative;
    private int tokenCount;
    private List<Chunk> chunks;
    
    // Getters and Setters...
}
```

---

## Enterprise Integration

### 1. Spring Boot Configuration
Define the parser as a Bean to inject it into services.

```java
@Configuration
public class AIOConfig {
    @Bean
    public AIOParser aioParser() {
        return new AIOParser.Builder()
            .connectTimeout(5000)
            .build();
    }
}
```

### 2. Integration with Search (Elasticsearch/Solr)
The `chunks` list is optimized for indexing.

```java
for (Chunk chunk : envelope.getChunks()) {
    IndexRequest request = new IndexRequest("aio_index")
        .id(chunk.getId())
        .source("content", chunk.getContent(), "vector", chunk.getVector());
    client.index(request);
}
```

---
[Javadoc](https://javadoc.io/doc/com.aifusion/aio-parser) | [Source Code](../aio-parser-java/)
