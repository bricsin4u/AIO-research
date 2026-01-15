const { parse } = require('./src/index');

async function test() {
    console.log("=== AIO Node.js Parser Test ===\n");

    const target = 'http://localhost:8000';

    // 1. Full Fetch
    console.log("Test 1: Full Fetch");
    const res1 = await parse(target);
    console.log(`Source Type: ${res1.source_type}`);
    console.log(`Tokens: ${res1.tokens}`);
    console.log(`Chunks: ${res1.chunks_count}`);
    console.log(`Preview: ${res1.narrative.substring(0, 100)}...`);
    console.log("\n-------------------\n");

    // 2. Targeted Fetch
    console.log("Test 2: Targeted Query ('pricing')");
    const res2 = await parse(target, "pricing plan cost");
    console.log(`Source Type: ${res2.source_type} (${res2.retrieval_method})`);
    console.log(`Tokens: ${res2.tokens}`);
    console.log(`Chunks: ${res2.chunks_count}`);
    console.log(`Preview: ${res2.narrative.substring(0, 100)}...`);
}

test();
