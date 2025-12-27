/**
 * AIO Signing Middleware for Strapi v4
 * 
 * Installation:
 * 1. Copy to src/middlewares/aio-signing.js
 * 2. Register in config/middlewares.js
 * 3. Add keys to .env
 * 
 * This middleware automatically adds AIO data to API responses.
 */

'use strict';

const crypto = require('crypto');

// Try to load tweetnacl for Ed25519
let nacl;
try {
  nacl = require('tweetnacl');
} catch (e) {
  nacl = null;
}

/**
 * Generate markdown from Strapi entry
 */
function entryToMarkdown(entry, contentType) {
  const citations = new Set();
  let contentBody = '';
  
  // Content fields
  const contentFields = ['content', 'body', 'description', 'Content', 'Body', 'Description'];
  for (const field of contentFields) {
    if (entry[field]) {
      // Extract citations from content
      extractCitations(entry[field]).forEach(c => citations.add(c));
      contentBody = stripHtml(entry[field]);
      break;
    }
  }

  // Build Frontmatter
  let frontmatter = '---\n';
  
  // Title
  const title = entry.title || entry.name || entry.Title || entry.Name || 'Untitled';
  frontmatter += `title: "${title.replace(/"/g, '\\"')}"\n`;

  // Author
  if (entry.author?.data?.attributes?.name) {
    frontmatter += `author: "${entry.author.data.attributes.name.replace(/"/g, '\\"')}"\n`;
  }

  // Date
  if (entry.createdAt) {
    frontmatter += `date: "${entry.createdAt.split('T')[0]}"\n`;
  }
  
  // Citations
  if (citations.size > 0) {
    frontmatter += 'citations:\n';
    citations.forEach(url => {
      frontmatter += `  - ${url}\n`;
    });
  }
  
  frontmatter += '---\n\n';
  
  let md = frontmatter;
  
  // Append Content
  if (contentBody) {
    md += `## Content\n${contentBody}\n\n`;
  }
  
  // Categories/Tags
  if (entry.categories?.data?.length) {
    md += '## Categories\n';
    entry.categories.data.forEach(cat => {
      md += `- ${cat.attributes.name}\n`;
    });
  }
  
  if (entry.tags?.data?.length) {
    md += '\n## Tags\n';
    entry.tags.data.forEach(tag => {
      md += `- ${tag.attributes.name}\n`;
    });
  }
  
  return md.trim();
}

/**
 * Extract citations from text (Markdown or HTML)
 */
function extractCitations(text) {
  if (!text) return [];
  const citations = [];
  
  // HTML links
  const htmlRegex = /<a[^>]+href=["'](https?:\/\/[^"']+)["'][^>]*>/gi;
  let match;
  while ((match = htmlRegex.exec(text)) !== null) {
    citations.push(match[1]);
  }
  
  // Markdown links
  const mdRegex = /\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g;
  while ((match = mdRegex.exec(text)) !== null) {
    citations.push(match[2]);
  }
  
  return citations;
}

/**
 * Strip HTML tags
 */
function stripHtml(html) {
  if (!html) return '';
  return html
    .replace(/<[^>]*>/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Hash content
 */
function hashContent(content) {
  return crypto.createHash('sha256').update(content, 'utf8').digest('hex');
}

/**
 * Sign content
 */
function signContent(markdown, privateKey) {
  const timestamp = new Date().toISOString();
  const contentHash = hashContent(markdown);
  
  const payload = JSON.stringify({
    content_hash: contentHash,
    timestamp: timestamp,
    algorithm: nacl ? 'Ed25519' : 'HMAC-SHA256'
  });
  
  let signature;
  
  if (nacl && privateKey.length === 88) { // Base64 Ed25519 key
    try {
      const secretKey = Buffer.from(privateKey, 'base64');
      const sig = nacl.sign.detached(Buffer.from(payload), secretKey);
      signature = Buffer.from(sig).toString('base64');
    } catch (e) {
      // Fallback to HMAC
      signature = crypto.createHmac('sha256', privateKey).update(payload).digest('base64');
    }
  } else {
    signature = crypto.createHmac('sha256', privateKey).update(payload).digest('base64');
  }
  
  return { signature, contentHash, timestamp };
}

/**
 * Strapi middleware factory
 */
module.exports = (config, { strapi }) => {
  const privateKey = process.env.AIO_PRIVATE_KEY || config.privateKey;
  const publicKey = process.env.AIO_PUBLIC_KEY || config.publicKey;
  
  return async (ctx, next) => {
    await next();
    
    // Only process successful JSON responses
    if (ctx.status !== 200 || !ctx.body?.data) {
      return;
    }
    
    // Check if AIO is requested
    const wantAIO = ctx.query.aio === 'true' || ctx.query.aio === '1';
    if (!wantAIO && !config.alwaysInclude) {
      return;
    }
    
    try {
      const data = ctx.body.data;
      const entries = Array.isArray(data) ? data : [data];
      
      for (const entry of entries) {
        if (!entry.attributes) continue;
        
        const markdown = entryToMarkdown(entry.attributes, ctx.state.route?.info?.contentType);
        
        if (privateKey) {
          const signResult = signContent(markdown, privateKey);
          
          entry.attributes.aio = {
            markdown: markdown,
            signature: signResult.signature,
            contentHash: signResult.contentHash,
            timestamp: signResult.timestamp,
            publicKey: publicKey || null,
            algorithm: nacl ? 'Ed25519' : 'HMAC-SHA256'
          };
        } else {
          // No signing, just include markdown and hash
          entry.attributes.aio = {
            markdown: markdown,
            contentHash: hashContent(markdown),
            timestamp: new Date().toISOString()
          };
        }
      }
    } catch (error) {
      strapi.log.error('AIO signing error:', error);
    }
  };
};

/**
 * Config schema
 */
module.exports.config = {
  privateKey: {
    type: 'string',
    env: 'AIO_PRIVATE_KEY'
  },
  publicKey: {
    type: 'string', 
    env: 'AIO_PUBLIC_KEY'
  },
  alwaysInclude: {
    type: 'boolean',
    default: false
  }
};
