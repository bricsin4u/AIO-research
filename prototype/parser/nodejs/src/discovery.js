const axios = require('axios');
const cheerio = require('cheerio');
const urllib = require('url');

/**
 * Discover AIO content for a URL.
 * Priority:
 * 1. HTTP Link Header
 * 2. HTML <link> Tag
 * 3. robots.txt
 * 4. Direct URL guess
 */
async function discoverAIO(url, timeout) {
    const client = axios.create({ timeout, validateStatus: () => true });

    try {
        // Step 1 & 2: Check Page (HEAD/GET)
        // We'll do a GET to get HTML for link tag
        const res = await client.get(url);

        // 1. HTTP Link Header
        const linkHeader = res.headers['link'];
        if (linkHeader) {
            const matches = linkHeader.match(/<([^>]+)>;\s*rel="alternate";\s*type="application\/aio\+json"/);
            if (matches) {
                return { aioUrl: urllib.resolve(url, matches[1]), method: 'link_header' };
            }
        }

        // 2. HTML Link Tag
        const $ = cheerio.load(res.data);
        const linkTag = $('link[rel="alternate"][type="application/aio+json"]').attr('href');
        if (linkTag) {
            return { aioUrl: urllib.resolve(url, linkTag), method: 'link_tag' };
        }

        // 3. robots.txt
        const rootUrl = new urllib.URL('/', url).href;
        const robotsRes = await client.get(rootUrl + 'robots.txt');
        if (robotsRes.status === 200) {
            const lines = robotsRes.data.split('\n');
            for (const line of lines) {
                if (line.trim().startsWith('AIO-Content:')) {
                    const path = line.split(':')[1].trim();
                    return { aioUrl: urllib.resolve(rootUrl, path), method: 'robots.txt' };
                }
            }
        }

        // 4. Direct Guess
        const directUrl = urllib.resolve(url, '/ai-content.aio');
        const directRes = await client.head(directUrl);
        if (directRes.status === 200) {
            return { aioUrl: directUrl, method: 'direct' };
        }

    } catch (err) {
        console.error("Discovery error:", err.message);
    }

    return { aioUrl: null, method: null };
}

module.exports = { discoverAIO };
