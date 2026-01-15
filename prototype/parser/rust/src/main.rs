use serde::{Deserialize, Serialize};
use std::error::Error;

#[derive(Debug, Serialize, Deserialize)]
struct AioContent {
    aio_version: String,
    content: Vec<Chunk>,
    index: Vec<IndexItem>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Chunk {
    id: String,
    content: String,
    hash: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct IndexItem {
    id: String,
    keywords: Option<Vec<String>>,
    token_estimate: Option<u32>,
}

fn main() -> Result<(), Box<dyn Error>> {
    println!("AIO Rust Parser Prototype");
    println!("-------------------------");

    let url = "http://localhost:8000/ai-content.aio";
    let body = reqwest::blocking::get(url)?.text()?;

    let aio: AioContent = serde_json::from_str(&body)?;

    println!("Version: {}", aio.aio_version);
    println!("Chunks: {}", aio.content.len());
    
    // Example targeted retrieval
    let query = "pricing";
    let mut relevant_tokens = 0;
    
    println!("\nSearching for '{}'...", query);
    
    for chunk in aio.content {
        // Simplified search logic
        if chunk.content.to_lowercase().contains(query) {
            println!("MATCH: {}", chunk.id);
            println!("Content: {:.100}...", chunk.content);
            relevant_tokens += chunk.content.len() / 4;
        }
    }
    
    println!("\nTotal Relevant Tokens: {}", relevant_tokens);

    Ok(())
}
