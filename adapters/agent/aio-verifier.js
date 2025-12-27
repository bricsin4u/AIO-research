/**
 * AIO Verifier for AI Agents
 * 
 * This library is designed for AI agent developers to:
 * 1. Detect AIO content in web pages
 * 2. Extract the Markdown Shadow
 * 3. Verify cryptographic signatures
 * 4. Return clean, trusted content
 * 
 * Usage:
 *   const verifier = require('aio-verifier');
 *   
 *   // From HTML string
 *   const result = verifier.extract(htmlContent);
 *   
 *   // From URL (with fetch)
 *   const result = await verifier.fetchAndExtract('https://example.com/article');
 *   
 *   // Check verification status
 *   if (result.trust.status === 'VERIFIED') {
 *     // Content is authentic
 *   }
 */

const crypto = require('crypto');

// Try to load optional dependencies
let nacl, cheerio;
try { nacl = require('tweetnacl'); } catch (e) { nacl = null; }
try { cheerio = require('cheerio'); } catch (e) { cheerio = null; }

/**
 * Verification status codes
 */
const VerificationStatus = {
  VERIFIED: 'VERIFIED',           // Signature valid, content matches
  HASH_VALID: 'HASH_VALID',       // No signature, but hash matches
  HASH_MISMATCH: 'HASH_MISMATCH', // Content modified
  SIGNATURE_INVALID: 'SIGNATURE_INVALID', // Signature check failed
  EXPIRED: 'EXPIRED',             // Timestamp too old
  NO_TRUST_LAYER: 'NO_TRUST_LAYER', // No verification data
  NO_AIO_CONTENT: 'NO_AIO_CONTENT', // No markdown shadow found
  ERROR: 'ERROR'                  // Processing error
};

/**
 * Parse HTML and extract AIO components
 */
function parseHTML(html) {
  if (cheerio) {
    return parseWithCheerio(html);
  }
  return parseWithRegex(html);
}

/**
 * Parse with Cheerio (preferred)
 */
function parseWithCheerio(html) {
  const $ = cheerio.load(html);
  
  // Extract Markdown Shadow
  const markdownScript = $('script[type="text/markdown"]');
  const markdown = markdownScript.length ? markdownScript.html()?.trim() : null;
  
  // Extract JSON-LD
  const jsonldScripts = $('script[type="application/ld+json"]');
  const jsonld = [];
  jsonldScripts.each((i, el) => {
    try {
      jsonld.push(JSON.parse($(el).html()));
    } catch (e) {}
  });
  
  // Extract Trust Layer meta tags
  const trust = {
    signature: $('meta[name="aio-truth-signature"]').attr('content'),
    contentHash: $('meta[name="aio-content-hash"]').attr('content'),
    publicKey: $('meta[name="aio-public-key"]').attr('content'),
    timestamp: $('meta[name="aio-last-verified"]').attr('content'),
    algorithm: $('meta[name="aio-signature-algorithm"]').attr('content')
  };
  
  // Extract page metadata
  const meta = {
    title: $('title').text(),
    description: $('meta[name="description"]').attr('content'),
    canonical: $('link[rel="canonical"]').attr('href')
  };
  
  return { markdown, jsonld, trust, meta };
}

/**
 * Parse with regex (fallback)
 */
function parseWithRegex(html) {
  // Extract Markdown Shadow
  const mdMatch = html.match(/<script[^>]*type=["']text\/markdown["'][^>]*>([\s\S]*?)<\/script>/i);
  const markdown = mdMatch ? mdMatch[1].trim() : null;
  
  // Extract JSON-LD
  const jsonld = [];
  const jsonldRegex = /<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let match;
  while ((match = jsonldRegex.exec(html)) !== null) {
    try {
      jsonld.push(JSON.parse(match[1]));
    } catch (e) {}
  }
  
  // Extract Trust Layer
  const trust = {
    signature: extractMeta(html, 'aio-truth-signature'),
    contentHash: extractMeta(html, 'aio-content-hash'),
    publicKey: extractMeta(html, 'aio-public-key'),
    timestamp: extractMeta(html, 'aio-last-verified'),
    algorithm: extractMeta(html, 'aio-signature-algorithm')
  };
  
  // Extract page metadata
  const meta = {
    title: html.match(/<title[^>]*>([^<]*)<\/title>/i)?.[1],
    description: extractMeta(html, 'description'),
    canonical: html.match(/<link[^>]*rel=["']canonical["'][^>]*href=["']([^"']+)["']/i)?.[1]
  };
  
  return { markdown, jsonld, trust, meta };
}

/**
 * Extract meta tag content
 */
function extractMeta(html, name) {
  const regex = new RegExp(`<meta[^>]*name=["']${name}["'][^>]*content=["']([^"']+)["']`, 'i');
  const match = html.match(regex);
  if (match) return match[1];
  
  // Try reverse order (content before name)
  const regex2 = new RegExp(`<meta[^>]*content=["']([^"']+)["'][^>]*name=["']${name}["']`, 'i');
  return html.match(regex2)?.[1] || null;
}

/**
 * Compute SHA-256 hash
 */
function sha256(content) {
  return crypto.createHash('sha256').update(content, 'utf8').digest('hex');
}

/**
 * Verify content hash
 */
function verifyHash(markdown, expectedHash) {
  if (!markdown || !expectedHash) return false;
  const actualHash = sha256(markdown.trim());
  return actualHash === expectedHash;
}

/**
 * Verify Ed25519 signature
 */
function verifyEd25519(payload, signature, publicKey) {
  if (!nacl) {
    console.warn('tweetnacl not available, cannot verify Ed25519 signatures');
    return null;
  }
  
  try {
    const sig = Buffer.from(signature, 'base64');
    const pubKey = Buffer.from(publicKey, 'base64');
    const message = Buffer.from(payload, 'utf8');
    return nacl.sign.detached.verify(message, sig, pubKey);
  } catch (e) {
    return false;
  }
}

/**
 * Verify HMAC signature (requires shared secret - usually not possible for agents)
 */
function verifyHMAC(payload, signature, secret) {
  try {
    const expected = crypto.createHmac('sha256', secret).update(payload).digest('base64');
    return signature === expected;
  } catch (e) {
    return false;
  }
}

/**
 * Build canonical payload for signature verification
 */
function buildPayload(contentHash, timestamp, algorithm) {
  return JSON.stringify({
    algorithm: algorithm,
    content_hash: contentHash,
    timestamp: timestamp
  });
}

/**
 * Verify the Trust Layer
 */
function verifyTrust(markdown, trust, options = {}) {
  const result = {
    status: VerificationStatus.NO_TRUST_LAYER,
    hashValid: false,
    signatureValid: null,
    contentHash: null,
    message: ''
  };
  
  if (!markdown) {
    result.status = VerificationStatus.NO_AIO_CONTENT;
    result.message = 'No markdown shadow found';
    return result;
  }
  
  // Compute actual hash
  result.contentHash = sha256(markdown.trim());
  
  // Check if any trust data exists
  if (!trust.contentHash && !trust.signature) {
    result.message = 'No trust layer metadata found';
    return result;
  }
  
  // Verify hash
  if (trust.contentHash) {
    result.hashValid = result.contentHash === trust.contentHash;
    
    if (!result.hashValid) {
      result.status = VerificationStatus.HASH_MISMATCH;
      result.message = 'Content hash does not match - content may have been modified';
      return result;
    }
  }
  
  // Check timestamp if provided
  if (trust.timestamp && options.maxAge) {
    const timestamp = new Date(trust.timestamp);
    const age = Date.now() - timestamp.getTime();
    if (age > options.maxAge) {
      result.status = VerificationStatus.EXPIRED;
      result.message = `Content timestamp is ${Math.round(age / 3600000)} hours old`;
      return result;
    }
  }
  
  // Verify signature if present
  if (trust.signature && trust.signature !== 'UNSIGNED') {
    const algorithm = trust.algorithm || 'Ed25519';
    const payload = buildPayload(result.contentHash, trust.timestamp, algorithm);
    
    if (algorithm === 'Ed25519' && trust.publicKey) {
      result.signatureValid = verifyEd25519(payload, trust.signature, trust.publicKey);
      
      if (result.signatureValid === true) {
        result.status = VerificationStatus.VERIFIED;
        result.message = 'Content verified - signature valid';
      } else if (result.signatureValid === false) {
        result.status = VerificationStatus.SIGNATURE_INVALID;
        result.message = 'Signature verification failed';
      } else {
        // null = couldn't verify (missing library)
        result.status = result.hashValid ? VerificationStatus.HASH_VALID : VerificationStatus.NO_TRUST_LAYER;
        result.message = 'Could not verify signature (Ed25519 library not available)';
      }
    } else if (algorithm === 'SHA256-HASH') {
      // Hash-only mode
      result.status = result.hashValid ? VerificationStatus.HASH_VALID : VerificationStatus.HASH_MISMATCH;
      result.message = result.hashValid ? 'Content hash verified' : 'Hash mismatch';
    } else {
      result.status = result.hashValid ? VerificationStatus.HASH_VALID : VerificationStatus.NO_TRUST_LAYER;
      result.message = `Unknown algorithm: ${algorithm}`;
    }
  } else if (result.hashValid) {
    result.status = VerificationStatus.HASH_VALID;
    result.message = 'Content hash verified (no signature)';
  }
  
  return result;
}

/**
 * Main extraction function
 */
function extract(html, options = {}) {
  try {
    const parsed = parseHTML(html);
    const verification = verifyTrust(parsed.markdown, parsed.trust, options);
    
    return {
      // Core content
      markdown: parsed.markdown,
      jsonld: parsed.jsonld,
      
      // Trust information
      trust: {
        status: verification.status,
        hashValid: verification.hashValid,
        signatureValid: verification.signatureValid,
        contentHash: verification.contentHash,
        providedHash: parsed.trust.contentHash,
        timestamp: parsed.trust.timestamp,
        algorithm: parsed.trust.algorithm,
        publicKey: parsed.trust.publicKey,
        message: verification.message
      },
      
      // Page metadata
      meta: parsed.meta,
      
      // Convenience flags
      hasAIO: !!parsed.markdown,
      isVerified: verification.status === VerificationStatus.VERIFIED,
      isTrusted: [VerificationStatus.VERIFIED, VerificationStatus.HASH_VALID].includes(verification.status)
    };
  } catch (error) {
    return {
      markdown: null,
      jsonld: [],
      trust: {
        status: VerificationStatus.ERROR,
        message: error.message
      },
      meta: {},
      hasAIO: false,
      isVerified: false,
      isTrusted: false,
      error: error.message
    };
  }
}

/**
 * Fetch URL and extract AIO content
 */
async function fetchAndExtract(url, options = {}) {
  const fetchFn = options.fetch || globalThis.fetch;
  
  if (!fetchFn) {
    throw new Error('fetch not available - provide options.fetch or use Node 18+');
  }
  
  const response = await fetchFn(url, {
    headers: {
      'User-Agent': options.userAgent || 'AIO-Verifier/1.0',
      'Accept': 'text/html',
      ...options.headers
    }
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  
  const html = await response.text();
  const result = extract(html, options);
  result.url = url;
  result.fetchedAt = new Date().toISOString();
  
  return result;
}

/**
 * Check if URL has AIO content (lightweight check)
 */
async function hasAIOContent(url, options = {}) {
  const result = await fetchAndExtract(url, options);
  return result.hasAIO;
}

/**
 * Fetch AI instructions from well-known location
 */
async function fetchAIInstructions(baseUrl, options = {}) {
  const fetchFn = options.fetch || globalThis.fetch;
  const url = new URL('/.well-known/ai-instructions.json', baseUrl);
  
  try {
    const response = await fetchFn(url.toString(), {
      headers: {
        'User-Agent': options.userAgent || 'AIO-Verifier/1.0',
        'Accept': 'application/json'
      }
    });
    
    if (!response.ok) return null;
    return await response.json();
  } catch (e) {
    return null;
  }
}

// Export
module.exports = {
  extract,
  fetchAndExtract,
  hasAIOContent,
  fetchAIInstructions,
  verifyTrust,
  parseHTML,
  sha256,
  VerificationStatus
};
