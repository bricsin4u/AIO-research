/**
 * AIO Universal Adapter (Cloudflare Worker)
 * 
 * Sits in front of ANY website (Wix, Squarespace, Webflow) and:
 * 1. Injects AIO discovery headers
 * 2. Auto-generates /ai-content.aio by scraping the origin on-the-fly
 * 
 * Usage:
 *   Deploy to Cloudflare Workers and route *your-domain.com/* to this worker.
 */

const ORIGIN = "https://your-main-site.com"; // Configure this
const MANIFEST = {
    site: { name: "My Site", domain: "your-domain.com" }
};

export default {
    async fetch(request, env, ctx) {
        const url = new URL(request.url);

        // 1. Serve Manifest
        if (url.pathname === '/ai-manifest.json') {
            return new Response(JSON.stringify({
                "$schema": "https://aio-standard.org/schema/v2.1/manifest.json",
                "aio_version": "2.1",
                "site": MANIFEST.site,
                "content": { "primary": "/ai-content.aio", "update_frequency": "realtime" }
            }), { headers: { 'Content-Type': 'application/json' } });
        }

        // 2. Serve AIO Content (Auto-Generated)
        if (url.pathname === '/ai-content.aio') {
            // In a real worker, we would use HTMLRewriter to scrape the home page
            // OR use KV storage to cache crawled pages. 
            // This is a simplified "crawl home page" example.

            const response = await fetch(ORIGIN);
            const html = await response.text();

            // Heuristic extraction (cheerio equivalent would be needed or regex)
            // Extract title
            const titleMatch = html.match(/<title>([^<]+)<\/title>/);
            const title = titleMatch ? titleMatch[1] : "Home";

            // Extract body text (very rough)
            const bodyText = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

            const content = {
                "$schema": "https://aio-standard.org/schema/v2.1/content.json",
                "aio_version": "2.1",
                "index": [{
                    id: "home",
                    path: "/",
                    title: title,
                    token_estimate: Math.ceil(bodyText.length / 4)
                }],
                "content": [{
                    id: "home",
                    format: "markdown",
                    content: `# ${title}\n\n${bodyText.substring(0, 5000)}... (truncated)`,
                    hash: "sha256:dynamic"
                }]
            };

            return new Response(JSON.stringify(content), {
                headers: { 'Content-Type': 'application/json' }
            });
        }

        // 3. Proxy everything else + Inject Headers
        const response = await fetch(request);
        const newResponse = new Response(response.body, response);

        // Inject Link Header for Discovery
        newResponse.headers.append('Link', '</ai-content.aio>; rel="alternate"; type="application/aio+json"');

        return newResponse;
    }
};
