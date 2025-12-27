/**
 * AIO React Components
 * 
 * For Next.js, Remix, Gatsby, Create React App, etc.
 * 
 * Usage:
 *   import { AIOHead, AIOShadow } from './AIOProvider';
 *   
 *   export default function Page() {
 *     const markdown = `# My Article\n\nContent here...`;
 *     
 *     return (
 *       <>
 *         <AIOHead markdown={markdown} />
 *         <main>
 *           <h1>My Article</h1>
 *           <p>Content here...</p>
 *         </main>
 *         <AIOShadow markdown={markdown} />
 *       </>
 *     );
 *   }
 */

import React, { createContext, useContext, useMemo } from 'react';
import crypto from 'crypto';

// Context for sharing keys across components
const AIOContext = createContext(null);

/**
 * Hash content (client-safe version)
 */
function hashContent(content) {
    if (typeof window === 'undefined') {
        // Server-side: use Node crypto
        return crypto.createHash('sha256').update(content, 'utf8').digest('hex');
    } else {
        // Client-side: use Web Crypto API
        // Note: This is async, so for SSR we compute on server
        return null;
    }
}

/**
 * Sign content (server-side only)
 */
function signMarkdown(markdown, privateKey) {
    if (typeof window !== 'undefined') {
        console.warn('AIO signing should happen server-side');
        return null;
    }
    
    const timestamp = new Date().toISOString();
    const contentHash = hashContent(markdown.trim());
    
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
 * Provider component - wrap your app with this
 */
export function AIOProvider({ children, privateKey, publicKey }) {
    const value = useMemo(() => ({
        privateKey,
        publicKey,
        sign: (markdown) => signMarkdown(markdown, privateKey)
    }), [privateKey, publicKey]);
    
    return (
        <AIOContext.Provider value={value}>
            {children}
        </AIOContext.Provider>
    );
}

/**
 * Hook to access AIO context
 */
export function useAIO() {
    return useContext(AIOContext);
}

/**
 * AIO Meta Tags Component (goes in <Head>)
 */
export function AIOHead({ markdown, signature, contentHash, timestamp, publicKey }) {
    // If signature not provided, compute it (server-side)
    const computed = useMemo(() => {
        if (signature) {
            return { signature, contentHash, timestamp };
        }
        
        const ctx = useContext(AIOContext);
        if (ctx && markdown) {
            return ctx.sign(markdown);
        }
        
        // Fallback: just hash
        return {
            signature: 'UNSIGNED',
            contentHash: hashContent(markdown?.trim() || ''),
            timestamp: new Date().toISOString()
        };
    }, [markdown, signature, contentHash, timestamp]);
    
    if (!computed) return null;
    
    return (
        <>
            <meta name="aio-truth-signature" content={computed.signature} />
            <meta name="aio-content-hash" content={computed.contentHash} />
            <meta name="aio-public-key" content={publicKey || ''} />
            <meta name="aio-last-verified" content={computed.timestamp} />
            <meta name="aio-signature-algorithm" content="HMAC-SHA256" />
        </>
    );
}

/**
 * AIO Shadow Component (goes before </body>)
 */
export function AIOShadow({ markdown, children }) {
    const content = markdown || children;
    
    if (!content) return null;
    
    return (
        <section 
            className="ai-only" 
            aria-hidden="true" 
            style={{ display: 'none' }}
        >
            <script 
                type="text/markdown" 
                id="aio-narrative-content"
                dangerouslySetInnerHTML={{ __html: content }}
            />
        </section>
    );
}

/**
 * Combined component for simple use cases
 */
export function AIOLayer({ markdown, publicKey }) {
    const hash = useMemo(() => hashContent(markdown?.trim() || ''), [markdown]);
    const timestamp = useMemo(() => new Date().toISOString(), []);
    
    return (
        <>
            {/* Meta tags - in Next.js, wrap with <Head> */}
            <meta name="aio-content-hash" content={hash} />
            <meta name="aio-public-key" content={publicKey || ''} />
            <meta name="aio-last-verified" content={timestamp} />
            
            {/* Shadow content */}
            <AIOShadow markdown={markdown} />
        </>
    );
}

export default { AIOProvider, AIOHead, AIOShadow, AIOLayer, useAIO };
