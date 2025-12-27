/**
 * Next.js Example - How to use AIO in a Next.js app
 * 
 * This shows the complete integration pattern.
 */

// ============================================
// 1. SETUP: next.config.js
// ============================================
/*
module.exports = {
  env: {
    AIO_PUBLIC_KEY: process.env.AIO_PUBLIC_KEY,
    // Never expose private key to client!
  }
}
*/

// ============================================
// 2. SETUP: .env.local
// ============================================
/*
AIO_PRIVATE_KEY=your_base64_private_key_here
AIO_PUBLIC_KEY=your_base64_public_key_here
*/

// ============================================
// 3. API Route for signing: pages/api/aio-sign.js
// ============================================
/*
import crypto from 'crypto';

export default function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  const { markdown } = req.body;
  const privateKey = process.env.AIO_PRIVATE_KEY;
  
  const timestamp = new Date().toISOString();
  const contentHash = crypto.createHash('sha256').update(markdown.trim()).digest('hex');
  
  const payload = JSON.stringify({
    content_hash: contentHash,
    timestamp,
    algorithm: 'HMAC-SHA256'
  });
  
  const signature = crypto
    .createHmac('sha256', privateKey)
    .update(payload)
    .digest('base64');
  
  res.json({ signature, contentHash, timestamp });
}
*/

// ============================================
// 4. Page Component: pages/blog/[slug].jsx
// ============================================

import Head from 'next/head';
import { AIOShadow } from '../lib/AIOProvider';

// This runs on the server
export async function getServerSideProps({ params }) {
    // Fetch your content
    const post = await fetchPost(params.slug);
    
    // Generate markdown version
    const markdown = `---
title: "${post.title}"
author: "${post.author}"
date: "${post.date}"
---

## Summary
${post.summary}

## Content
${post.content}
`;
    
    // Sign it server-side
    const crypto = require('crypto');
    const privateKey = process.env.AIO_PRIVATE_KEY;
    const publicKey = process.env.AIO_PUBLIC_KEY;
    
    const timestamp = new Date().toISOString();
    const contentHash = crypto.createHash('sha256').update(markdown.trim()).digest('hex');
    
    const payload = JSON.stringify({
        content_hash: contentHash,
        timestamp,
        algorithm: 'HMAC-SHA256'
    });
    
    const signature = crypto
        .createHmac('sha256', privateKey)
        .update(payload)
        .digest('base64');
    
    return {
        props: {
            post,
            markdown,
            aio: { signature, contentHash, timestamp, publicKey }
        }
    };
}

export default function BlogPost({ post, markdown, aio }) {
    return (
        <>
            <Head>
                <title>{post.title}</title>
                
                {/* AIO Meta Tags */}
                <meta name="aio-truth-signature" content={aio.signature} />
                <meta name="aio-content-hash" content={aio.contentHash} />
                <meta name="aio-public-key" content={aio.publicKey} />
                <meta name="aio-last-verified" content={aio.timestamp} />
                <meta name="aio-signature-algorithm" content="HMAC-SHA256" />
                
                {/* Standard SEO */}
                <meta name="description" content={post.summary} />
                
                {/* JSON-LD */}
                <script 
                    type="application/ld+json"
                    dangerouslySetInnerHTML={{
                        __html: JSON.stringify({
                            "@context": "https://schema.org",
                            "@type": "Article",
                            "headline": post.title,
                            "author": { "@type": "Person", "name": post.author },
                            "datePublished": post.date
                        })
                    }}
                />
            </Head>
            
            <main>
                <article>
                    <h1>{post.title}</h1>
                    <p>By {post.author} | {post.date}</p>
                    <div dangerouslySetInnerHTML={{ __html: post.htmlContent }} />
                </article>
            </main>
            
            {/* AIO Markdown Shadow */}
            <AIOShadow markdown={markdown} />
        </>
    );
}

// Dummy function - replace with your data fetching
async function fetchPost(slug) {
    return {
        title: "Example Post",
        author: "Author Name",
        date: "2025-12-22",
        summary: "This is an example post.",
        content: "Full content here...",
        htmlContent: "<p>Full content here...</p>"
    };
}
