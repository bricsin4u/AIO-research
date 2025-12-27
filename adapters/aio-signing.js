/**
 * AIO Signing Library for Node.js
 * 
 * Works with Express, Next.js, Nuxt, Remix, etc.
 * 
 * Usage:
 *   npm install tweetnacl tweetnacl-util
 * 
 *   const aio = require('./aio-signing');
 *   
 *   // Generate keys (once)
 *   const keys = aio.generateKeys();
 *   
 *   // Sign content
 *   const signed = aio.signMarkdown(markdownContent, keys.privateKey);
 *   
 *   // Inject into HTML
 *   const html = aio.injectAIOLayer(htmlContent, markdownContent, keys);
 */

const crypto = require('crypto');

// Try to use tweetnacl for Ed25519, fallback to HMAC if not available
let nacl, naclUtil;
try {
    nacl = require('tweetnacl');
    naclUtil = require('tweetnacl-util');
} catch (e) {
    nacl = null;
}

/**
 * Generate a new keypair for signing
 */
function generateKeys() {
    if (nacl) {
        // Ed25519 (preferred)
        const keyPair = nacl.sign.keyPair();
        return {
            publicKey: Buffer.from(keyPair.publicKey).toString('base64'),
            privateKey: Buffer.from(keyPair.secretKey).toString('base64'),
            algorithm: 'Ed25519'
        };
    } else {
        // Fallback: HMAC with random secret
        const secret = crypto.randomBytes(32).toString('base64');
        return {
            publicKey: null, // HMAC doesn't have public key
            privateKey: secret,
            algorithm: 'HMAC-SHA256'
        };
    }
}

/**
 * Hash content using SHA-256
 */
function hashContent(content) {
    return crypto.createHash('sha256').update(content, 'utf8').digest('hex');
}

/**
 * Sign markdown content
 */
function signMarkdown(markdown, privateKey, algorithm = 'Ed25519') {
    const timestamp = new Date().toISOString();
    const contentHash = hashContent(markdown.trim());
    
    const payload = JSON.stringify({
        content_hash: contentHash,
        timestamp: timestamp,
        algorithm: algorithm
    });
    
    let signature;
    
    if (algorithm === 'Ed25519' && nacl) {
        const secretKey = Buffer.from(privateKey, 'base64');
        const messageBytes = Buffer.from(payload, 'utf8');
        const sig = nacl.sign.detached(messageBytes, secretKey);
        signature = Buffer.from(sig).toString('base64');
    } else {
        // HMAC fallback
        signature = crypto
            .createHmac('sha256', privateKey)
            .update(payload)
            .digest('base64');
    }
    
    return {
        signature,
        contentHash,
        timestamp,
        algorithm
    };
}

/**
 * Verify a signature
 */
function verifySignature(markdown, signature, timestamp, publicKey, algorithm = 'Ed25519') {
    const contentHash = hashContent(markdown.trim());
    
    const payload = JSON.stringify({
        content_hash: contentHash,
        timestamp: timestamp,
        algorithm: algorithm
    });
    
    if (algorithm === 'Ed25519' && nacl) {
        try {
            const pubKey = Buffer.from(publicKey, 'base64');
            const sig = Buffer.from(signature, 'base64');
            const message = Buffer.from(payload, 'utf8');
            return nacl.sign.detached.verify(message, sig, pubKey);
        } catch (e) {
            return false;
        }
    }
    
    return false; // HMAC can't be verified without secret
}

/**
 * Generate the AIO meta tags HTML
 */
function generateMetaTags(signResult, publicKey = '') {
    return `
    <meta name="aio-truth-signature" content="${signResult.signature}">
    <meta name="aio-content-hash" content="${signResult.contentHash}">
    <meta name="aio-public-key" content="${publicKey}">
    <meta name="aio-last-verified" content="${signResult.timestamp}">
    <meta name="aio-signature-algorithm" content="${signResult.algorithm}">`;
}

/**
 * Helper: Convert HTML to Markdown with AIO improvements
 * Note: This is a regex-based implementation for zero-dependencies.
 * For production, use 'turndown' or similar with 'cheerio'.
 */
function htmlToMarkdown(html) {
    // 1. Extract Metadata & Citations
    const metadata = {};
    const citations = [];
    
    // Helper regex
    const getMatch = (regex, text, index = 1) => {
        const match = text.match(regex);
        return match ? match[index] : null;
    };
    
    metadata.title = getMatch(/<title[^>]*>(.*?)<\/title>/i, html) || '';
    
    // Site Name
    metadata.site_name = getMatch(/<meta[^>]*property=["']og:site_name["'][^>]*content=["']([^"']*)["']/i, html) || 
                         getMatch(/<h1[^>]*>(.*?)<\/h1>/i, html)?.replace(/<[^>]+>/g, '') || '';

    // Author
    metadata.author = getMatch(/<meta[^>]*name=["']author["'][^>]*content=["']([^"']*)["']/i, html) || 
                      getMatch(/By\s+([^|<]+)/i, html) || '';
                      
    // Date
    metadata.date = getMatch(/<meta[^>]*property=["']article:published_time["'][^>]*content=["']([^"']*)["']/i, html) || '';
    
    // URL
    metadata.url = getMatch(/<link[^>]*rel=["']canonical["'][^>]*href=["']([^"']*)["']/i, html) || 
                   getMatch(/<meta[^>]*property=["']og:url["'][^>]*content=["']([^"']*)["']/i, html) || '';
                   
    // Citations (External Links)
    const linkRegex = /<a[^>]*href=["'](http[^"']*)["'][^>]*>/gi;
    let match;
    while ((match = linkRegex.exec(html)) !== null) {
        const href = match[1];
        if (!href.includes('localhost') && !href.includes('127.0.0.1')) {
            if (!citations.includes(href)) {
                citations.push(href);
            }
        }
    }
    
    if (citations.length > 0) {
        metadata.citations = citations;
    }

    // 2. Build Frontmatter
    let frontmatter = "---\n";
    for (const [key, value] of Object.entries(metadata)) {
        if (!value) continue;
        
        if (key === 'citations') {
            frontmatter += "citations:\n";
            value.forEach(cite => {
                frontmatter += `  - ${cite}\n`;
            });
        } else {
            const safeValue = String(value).replace(/"/g, '\\"').trim();
            frontmatter += `${key}: "${safeValue}"\n`;
        }
    }
    frontmatter += "---\n\n";

    // 3. Clean Noise
    let cleanHtml = html
        .replace(/<(script|style|nav|footer)[^>]*>[\s\S]*?<\/\1>/gi, '')
        .replace(/<div[^>]*class=["'][^"']*(ad-|banner|promo|sidebar)[^"']*["'][^>]*>[\s\S]*?<\/div>/gi, '');

    // 4. Convert Body (Basic Regex)
    let md = cleanHtml
        // Keep only semantic tags for processing
        .replace(/<(?!\/?(h[1-6]|p|ul|ol|li|strong|b|em|i|a|blockquote|pre|code|img))[^>]+>/gi, '') 
        // Headers
        .replace(/<h1[^>]*>(.*?)<\/h1>/gi, '\n# $1\n\n')
        .replace(/<h2[^>]*>(.*?)<\/h2>/gi, '\n## $1\n\n')
        .replace(/<h3[^>]*>(.*?)<\/h3>/gi, '\n### $1\n\n')
        // Paragraphs
        .replace(/<p[^>]*>(.*?)<\/p>/gi, '\n$1\n\n')
        // Bold
        .replace(/<(strong|b)[^>]*>(.*?)<\/\1>/gi, '**$2**')
        // Italic
        .replace(/<(em|i)[^>]*>(.*?)<\/\1>/gi, '*$2*')
        // Links
        .replace(/<a[^>]*href=["']([^"']*)["'][^>]*>(.*?)<\/a>/gi, '[$2]($1)')
        // Lists
        .replace(/<li[^>]*>(.*?)<\/li>/gi, '- $1\n')
        .replace(/<\/?(ul|ol)[^>]*>/gi, '\n')
        // Blockquotes
        .replace(/<blockquote[^>]*>(.*?)<\/blockquote>/gi, '\n> $1\n')
        // Images
        .replace(/<img[^>]*alt=["']([^"']*)["'][^>]*src=["']([^"']*)["'][^>]*>/gi, '![$1]($2)')
        // Cleanup multiple newlines
        .replace(/\n{3,}/g, '\n\n')
        .trim();

    return frontmatter + md;
}

/**
 * Generate the markdown shadow block HTML
 */
function generateMarkdownShadow(markdown) {
    return `
    <section class="ai-only" aria-hidden="true" style="display:none!important">
        <script type="text/markdown" id="aio-narrative-content">
${markdown}
        </script>
    </section>`;
}

/**
 * Inject AIO layer into existing HTML
 */
function injectAIOLayer(html, markdown, keys) {
    const signResult = signMarkdown(markdown, keys.privateKey, keys.algorithm);
    const metaTags = generateMetaTags(signResult, keys.publicKey);
    const shadow = generateMarkdownShadow(markdown);
    
    // Inject meta tags before </head>
    html = html.replace('</head>', `${metaTags}\n</head>`);
    
    // Inject shadow before </body>
    html = html.replace('</body>', `${shadow}\n</body>`);
    
    return html;
}

/**
 * Express/Connect middleware
 */
function middleware(options = {}) {
    const { privateKey, publicKey, algorithm = 'Ed25519', getMarkdown } = options;
    
    return (req, res, next) => {
        const originalSend = res.send.bind(res);
        
        res.send = function(body) {
            if (typeof body === 'string' && body.includes('</html>')) {
                // It's HTML, try to sign it
                const markdown = getMarkdown ? getMarkdown(req, res) : null;
                
                if (markdown) {
                    const keys = { privateKey, publicKey, algorithm };
                    body = injectAIOLayer(body, markdown, keys);
                }
            }
            return originalSend(body);
        };
        
        next();
    };
}

module.exports = {
    generateKeys,
    hashContent,
    signMarkdown,
    verifySignature,
    generateMetaTags,
    generateMarkdownShadow,
    injectAIOLayer,
    middleware,
    htmlToMarkdown
};
