/**
 * AIO Signing for Ghost CMS
 * 
 * Ghost uses Handlebars templates. This helper adds AIO support.
 * 
 * Installation:
 * 1. Copy to your theme's assets/js/ folder
 * 2. For full integration, create a custom Ghost theme or use Ghost's code injection
 * 
 * Option A: Code Injection (Ghost Admin > Settings > Code Injection)
 * Option B: Custom theme with partials
 */

// ============================================
// OPTION A: Code Injection (simplest)
// ============================================

// Add to Ghost Admin > Settings > Code Injection > Site Header:
const ghostAIOHead = `
<script>
(function() {
  // Wait for page load
  document.addEventListener('DOMContentLoaded', function() {
    // Get article content
    var article = document.querySelector('.post-content, .page-content, article');
    if (!article) return;
    
    var title = document.querySelector('.post-title, .page-title, h1');
    var author = document.querySelector('.author-name, [rel="author"]');
    var date = document.querySelector('time[datetime]');
    
    // Extract citations
    var citations = [];
    var links = article.querySelectorAll('a[href^="http"]');
    links.forEach(function(link) {
        if (link.hostname !== window.location.hostname) {
            citations.push(link.href);
        }
    });
    // Unique citations
    citations = citations.filter((v, i, a) => a.indexOf(v) === i);

    // Build Frontmatter
    var frontmatter = '---\\n';
    frontmatter += 'title: "' + (title ? title.textContent.trim().replace(/"/g, '\\\\"') : document.title) + '"\\n';
    if (author) frontmatter += 'author: "' + author.textContent.trim().replace(/"/g, '\\\\"') + '"\\n';
    if (date) frontmatter += 'date: "' + date.getAttribute('datetime').split('T')[0] + '"\\n';
    
    if (citations.length > 0) {
        frontmatter += 'citations:\\n';
        citations.forEach(function(c) {
            frontmatter += '  - ' + c + '\\n';
        });
    }
    frontmatter += '---\\n\\n';
    
    // Build markdown
    var markdown = frontmatter;
    markdown += '## Content\\n' + article.textContent.trim().substring(0, 5000);
    
    // Generate hash (client-side, for demo - use server for production)
    crypto.subtle.digest('SHA-256', new TextEncoder().encode(markdown))
      .then(function(hash) {
        var hashHex = Array.from(new Uint8Array(hash))
          .map(b => b.toString(16).padStart(2, '0'))
          .join('');
        
        // Add meta tags
        var meta = document.createElement('meta');
        meta.name = 'aio-content-hash';
        meta.content = hashHex;
        document.head.appendChild(meta);
        
        var metaTime = document.createElement('meta');
        metaTime.name = 'aio-last-verified';
        metaTime.content = new Date().toISOString();
        document.head.appendChild(metaTime);
        
        // Add shadow
        var shadow = document.createElement('section');
        shadow.className = 'ai-only';
        shadow.setAttribute('aria-hidden', 'true');
        shadow.style.display = 'none';
        shadow.innerHTML = '<script type="text/markdown" id="aio-narrative-content">' + markdown + '<\\/script>';
        document.body.appendChild(shadow);
      });
  });
})();
</script>
`;

// ============================================
// OPTION B: Theme Partial (for custom themes)
// ============================================

// Create partials/aio-head.hbs:
const ghostAIOHeadPartial = `
{{!-- AIO Meta Tags --}}
<meta name="aio-content-hash" content="{{aio_hash}}">
<meta name="aio-public-key" content="{{@site.aio_public_key}}">
<meta name="aio-last-verified" content="{{date format="YYYY-MM-DDTHH:mm:ss[Z]"}}">
<meta name="aio-signature-algorithm" content="SHA256-HASH">
`;

// Create partials/aio-shadow.hbs:
const ghostAIOShadowPartial = `
{{!-- AIO Markdown Shadow --}}
<section class="ai-only" aria-hidden="true" style="display:none!important">
<script type="text/markdown" id="aio-narrative-content">
---
title: "{{title}}"
site_name: "{{@site.title}}"
author: "{{primary_author.name}}"
date: "{{date format="YYYY-MM-DD"}}"
url: "{{url absolute="true"}}"
---

{{#if custom_excerpt}}
## Summary
{{custom_excerpt}}
{{/if}}

## Content
{{content}}

{{#if tags}}
## Tags
{{#foreach tags}}
- {{name}}
{{/foreach}}
{{/if}}
</script>
</section>
`;

// ============================================
// OPTION C: Ghost API + Serverless Function
// ============================================

/**
 * For production signing, use a serverless function that:
 * 1. Fetches content from Ghost Content API
 * 2. Generates markdown
 * 3. Signs with Ed25519
 * 4. Returns signed HTML or injects via proxy
 */

// Example Cloudflare Worker / Vercel Edge Function:
const ghostServerlessExample = `
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    
    // Fetch from Ghost
    const ghostResponse = await fetch(
      \`https://your-ghost-site.com\${url.pathname}\`
    );
    
    let html = await ghostResponse.text();
    
    // Extract content and sign
    // Use aio-signing.js logic to generate Markdown with Frontmatter and citations
    // const { htmlToMarkdown } = require('./aio-signing');
    // const markdown = htmlToMarkdown(html, { url: url.toString() });
    
    return new Response(html, {
      headers: { 'Content-Type': 'text/html' }
    });
  }
};
`;

// Export for use in build tools
if (typeof module !== 'undefined') {
  module.exports = {
    ghostAIOHead,
    ghostAIOHeadPartial,
    ghostAIOShadowPartial,
    ghostServerlessExample
  };
}
