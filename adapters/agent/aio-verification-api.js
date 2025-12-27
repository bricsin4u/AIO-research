/**
 * AIO Verification API Service
 * 
 * A simple REST API that AI agents can call to verify AIO content
 * without implementing cryptographic verification themselves.
 * 
 * Endpoints:
 *   POST /verify     - Verify HTML content
 *   POST /verify-url - Fetch and verify URL
 *   GET  /extract    - Extract AIO content from URL
 * 
 * Run:
 *   npm install express cheerio tweetnacl
 *   node aio-verification-api.js
 * 
 * Or deploy to Vercel/Cloudflare Workers/AWS Lambda
 */

const express = require('express');
const verifier = require('./aio-verifier');

const app = express();
app.use(express.json({ limit: '5mb' }));

// CORS for API access
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  next();
});

/**
 * Health check
 */
app.get('/', (req, res) => {
  res.json({
    service: 'AIO Verification API',
    version: '1.0.0',
    endpoints: {
      'POST /verify': 'Verify HTML content',
      'POST /verify-url': 'Fetch and verify URL',
      'GET /extract?url=': 'Extract AIO content from URL'
    }
  });
});

/**
 * Verify HTML content directly
 * 
 * POST /verify
 * Body: { "html": "<html>...</html>" }
 */
app.post('/verify', (req, res) => {
  const { html } = req.body;
  
  if (!html) {
    return res.status(400).json({ error: 'Missing html in request body' });
  }
  
  try {
    const result = verifier.extract(html);
    res.json(formatResponse(result));
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * Fetch URL and verify
 * 
 * POST /verify-url
 * Body: { "url": "https://example.com/article" }
 */
app.post('/verify-url', async (req, res) => {
  const { url, maxAgeHours } = req.body;
  
  if (!url) {
    return res.status(400).json({ error: 'Missing url in request body' });
  }
  
  try {
    const result = await verifier.fetchAndExtract(url, {
      maxAge: maxAgeHours ? maxAgeHours * 3600000 : undefined
    });
    res.json(formatResponse(result));
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * Extract AIO content from URL (GET for simplicity)
 * 
 * GET /extract?url=https://example.com/article
 */
app.get('/extract', async (req, res) => {
  const { url } = req.query;
  
  if (!url) {
    return res.status(400).json({ error: 'Missing url query parameter' });
  }
  
  try {
    const result = await verifier.fetchAndExtract(url);
    res.json(formatResponse(result));
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * Batch verify multiple URLs
 * 
 * POST /verify-batch
 * Body: { "urls": ["https://...", "https://..."] }
 */
app.post('/verify-batch', async (req, res) => {
  const { urls } = req.body;
  
  if (!urls || !Array.isArray(urls)) {
    return res.status(400).json({ error: 'Missing urls array in request body' });
  }
  
  if (urls.length > 10) {
    return res.status(400).json({ error: 'Maximum 10 URLs per batch' });
  }
  
  try {
    const results = await Promise.all(
      urls.map(async (url) => {
        try {
          const result = await verifier.fetchAndExtract(url);
          return { url, ...formatResponse(result) };
        } catch (error) {
          return { url, error: error.message };
        }
      })
    );
    
    res.json({ results });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * Format response for API
 */
function formatResponse(result) {
  return {
    hasAIO: result.hasAIO,
    isVerified: result.isVerified,
    isTrusted: result.isTrusted,
    
    verification: {
      status: result.trust.status,
      message: result.trust.message,
      hashValid: result.trust.hashValid,
      signatureValid: result.trust.signatureValid,
      algorithm: result.trust.algorithm,
      timestamp: result.trust.timestamp
    },
    
    content: {
      markdown: result.markdown,
      markdownLength: result.markdown?.length || 0,
      jsonld: result.jsonld
    },
    
    meta: result.meta,
    
    hashes: {
      computed: result.trust.contentHash,
      provided: result.trust.providedHash,
      match: result.trust.hashValid
    }
  };
}

// Start server
const PORT = process.env.PORT || 3000;

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`AIO Verification API running on port ${PORT}`);
    console.log(`Try: curl http://localhost:${PORT}/`);
  });
}

module.exports = app;
