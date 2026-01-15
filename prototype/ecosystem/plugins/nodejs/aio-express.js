const axios = require('axios');
const cheerio = require('cheerio');
const TurndownService = require('turndown');
const crypto = require('crypto');

/**
 * AIO Auto-Middleware (Self-Updating)
 * 
 * Automatically generates AIO content by scraping your own app's HTML routes.
 * Keeps AIO in sync with HTML changes automatically.
 * 
 * Usage:
 *   app.use(aioAuto({
 *     baseUrl: 'http://localhost:3000', // Your app's internal URL
 *     routes: ['/', '/about', '/pricing', '/features'], // Routes to index
 *     manifest: { site: { name: "My App" } }
 *   }));
 */

const turndownService = new TurndownService();
// Remove scripts, styles, nav, footer before converting
turndownService.remove(['script', 'style', 'nav', 'footer', 'header', '.cookie-banner']);

function generateHash(content) {
    return 'sha256:' + crypto.createHash('sha256').update(content).digest('hex');
}

module.exports = function aioAuto(options) {
    const { baseUrl, routes, manifest } = options;

    return async function (req, res, next) {
        // 1. Serve Manifest
        if (req.path === '/ai-manifest.json') {
            return res.json({
                "$schema": "https://aio-standard.org/schema/v2.1/manifest.json",
                "aio_version": "2.1",
                "site": manifest.site || {},
                "content": {
                    "primary": "/ai-content.aio",
                    "chunks_count": routes.length,
                    "update_frequency": "always" // It's dynamic!
                }
            });
        }

        // 2. Serve AIO Content (Dynamic Generation)
        if (req.path === '/ai-content.aio') {
            try {
                const chunks = [];

                // Parallel fetch of all routes
                const promises = routes.map(async (route) => {
                    try {
                        // Fetch the HTML from ourself
                        const response = await axios.get(`${baseUrl}${route}`);
                        const html = response.data;

                        // Parse and Clean
                        const $ = cheerio.load(html);
                        const title = $('title').text() || route;

                        // Select main content only (heuristics)
                        const mainHtml = $('main').html() || $('body').html();

                        // Convert to Markdown
                        const markdown = turndownService.turndown(mainHtml);
                        const cleanContent = `# ${title}\n\n${markdown}`;

                        return {
                            id: route === '/' ? 'home' : route.replace(/\//g, '-'),
                            path: route,
                            title: title,
                            content: cleanContent
                        };
                    } catch (e) {
                        console.error(`Failed to scrape route ${route}:`, e.message);
                        return null;
                    }
                });

                const results = (await Promise.all(promises)).filter(c => c !== null);

                // Format response
                const aioResponse = {
                    "$schema": "https://aio-standard.org/schema/v2.1/content.json",
                    "aio_version": "2.1",
                    "generated": new Date().toISOString(),
                    "index": results.map(c => ({
                        id: c.id,
                        path: c.path,
                        title: c.title,
                        keywords: [], // Could extract tf-idf keywords here automatically
                        token_estimate: Math.ceil(c.content.length / 4)
                    })),
                    "content": results.map(c => ({
                        id: c.id,
                        format: "markdown",
                        content: c.content,
                        hash: generateHash(c.content)
                    }))
                };

                return res.json(aioResponse);

            } catch (err) {
                console.error("AIO Generation Error:", err);
                return res.status(500).json({ error: "Failed to generate AIO content" });
            }
        }

        next();
    };
};
