/**
 * AIO Signing for Contentful
 * 
 * Contentful is a headless CMS - content is delivered via API.
 * This module helps you sign content when rendering on your frontend.
 * 
 * Usage with Next.js + Contentful:
 *   import { signContentfulEntry } from './aio-contentful';
 *   
 *   export async function getStaticProps() {
 *     const entry = await contentfulClient.getEntry('xxx');
 *     const aio = signContentfulEntry(entry);
 *     return { props: { entry, aio } };
 *   }
 */

const crypto = require('crypto');

/**
 * Convert Contentful Rich Text to Markdown
 */
function richTextToMarkdown(richText, citations = null) {
  if (!richText || !richText.content) return '';
  
  let md = '';
  
  for (const node of richText.content) {
    switch (node.nodeType) {
      case 'heading-1':
        md += `# ${extractText(node, citations)}\n\n`;
        break;
      case 'heading-2':
        md += `## ${extractText(node, citations)}\n\n`;
        break;
      case 'heading-3':
        md += `### ${extractText(node, citations)}\n\n`;
        break;
      case 'paragraph':
        md += `${extractText(node, citations)}\n\n`;
        break;
      case 'unordered-list':
        for (const item of node.content) {
          md += `- ${extractText(item, citations)}\n`;
        }
        md += '\n';
        break;
      case 'ordered-list':
        let i = 1;
        for (const item of node.content) {
          md += `${i}. ${extractText(item, citations)}\n`;
          i++;
        }
        md += '\n';
        break;
      case 'blockquote':
        md += `> ${extractText(node, citations)}\n\n`;
        break;
      case 'hr':
        md += '---\n\n';
        break;
    }
  }
  
  return md.trim();
}

/**
 * Extract text from rich text node
 */
function extractText(node, citations = null) {
  if (!node.content) return '';
  
  return node.content.map(child => {
    if (child.nodeType === 'text') {
      let text = child.value;
      if (child.marks) {
        for (const mark of child.marks) {
          if (mark.type === 'bold') text = `**${text}**`;
          if (mark.type === 'italic') text = `*${text}*`;
          if (mark.type === 'code') text = `\`${text}\``;
        }
      }
      return text;
    }
    if (child.nodeType === 'hyperlink') {
      if (citations) citations.add(child.data.uri);
      return `[${extractText(child, citations)}](${child.data.uri})`;
    }
    return extractText(child, citations);
  }).join('');
}

/**
 * Convert Contentful entry to Markdown
 */
function entryToMarkdown(entry, options = {}) {
  const fields = entry.fields;
  const sys = entry.sys;
  const citations = new Set();
  
  let contentBody = '';
  
  // Body/Content (Rich Text)
  const bodyField = options.bodyField || 'body';
  if (fields[bodyField]) {
    if (typeof fields[bodyField] === 'string') {
      // If it's a string, try to extract links via regex
      const text = fields[bodyField];
      const mdLinkRegex = /\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g;
      let match;
      while ((match = mdLinkRegex.exec(text)) !== null) {
        citations.add(match[2]);
      }
      contentBody = text;
    } else {
      contentBody = richTextToMarkdown(fields[bodyField], citations);
    }
  }

  // Build Frontmatter
  let frontmatter = '---\n';
  
  // Title
  const titleField = options.titleField || 'title';
  if (fields[titleField]) {
    frontmatter += `title: "${fields[titleField].replace(/"/g, '\\"')}"\n`;
  }
  
  // Author
  if (fields.author?.fields?.name) {
    frontmatter += `author: "${fields.author.fields.name.replace(/"/g, '\\"')}"\n`;
  }
  
  // Date
  if (sys.createdAt) {
    frontmatter += `date: "${sys.createdAt.split('T')[0]}"\n`;
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
  
  // Description/Summary
  const descField = options.descriptionField || 'description';
  if (fields[descField]) {
    md += `## Summary\n${fields[descField]}\n\n`;
  }
  
  // Append Content
  if (contentBody) {
    md += `## Content\n${contentBody}\n\n`;
  }
  
  // Tags
  if (fields.tags?.length) {
    md += '## Tags\n';
    for (const tag of fields.tags) {
      const tagName = typeof tag === 'string' ? tag : tag.fields?.name || tag.sys?.id;
      md += `- ${tagName}\n`;
    }
  }
  
  return md.trim();
}

/**
 * Hash content
 */
function hashContent(content) {
  return crypto.createHash('sha256').update(content, 'utf8').digest('hex');
}

/**
 * Sign markdown content
 */
function signMarkdown(markdown, privateKey) {
  const timestamp = new Date().toISOString();
  const contentHash = hashContent(markdown);
  
  const payload = JSON.stringify({
    content_hash: contentHash,
    timestamp: timestamp,
    algorithm: 'HMAC-SHA256'
  });
  
  const signature = crypto
    .createHmac('sha256', privateKey)
    .update(payload)
    .digest('base64');
  
  return { signature, contentHash, timestamp };
}

/**
 * Sign a Contentful entry
 */
function signContentfulEntry(entry, options = {}) {
  const privateKey = options.privateKey || process.env.AIO_PRIVATE_KEY;
  const publicKey = options.publicKey || process.env.AIO_PUBLIC_KEY;
  
  const markdown = entryToMarkdown(entry, options);
  
  if (privateKey) {
    const signResult = signMarkdown(markdown, privateKey);
    return {
      markdown,
      signature: signResult.signature,
      contentHash: signResult.contentHash,
      timestamp: signResult.timestamp,
      publicKey: publicKey || null,
      algorithm: 'HMAC-SHA256'
    };
  }
  
  return {
    markdown,
    contentHash: hashContent(markdown),
    timestamp: new Date().toISOString()
  };
}

/**
 * Generate HTML meta tags
 */
function generateMetaTags(aio) {
  return `
<meta name="aio-truth-signature" content="${aio.signature || 'UNSIGNED'}">
<meta name="aio-content-hash" content="${aio.contentHash}">
<meta name="aio-public-key" content="${aio.publicKey || ''}">
<meta name="aio-last-verified" content="${aio.timestamp}">
<meta name="aio-signature-algorithm" content="${aio.algorithm || 'SHA256-HASH'}">
  `.trim();
}

/**
 * Generate markdown shadow HTML
 */
function generateShadow(markdown) {
  return `
<section class="ai-only" aria-hidden="true" style="display:none!important">
<script type="text/markdown" id="aio-narrative-content">
${markdown}
</script>
</section>
  `.trim();
}

module.exports = {
  richTextToMarkdown,
  entryToMarkdown,
  hashContent,
  signMarkdown,
  signContentfulEntry,
  generateMetaTags,
  generateShadow
};
