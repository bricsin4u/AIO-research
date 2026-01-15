const { discoverAIO } = require('./discovery');
const { fetchAIO, fetchScraped } = require('./fetcher');

class AIOParser {
    constructor(options = {}) {
        this.timeout = options.timeout || 10000;
        this.userAgent = options.userAgent || 'AIOParser/1.0 (Node.js)';
    }

    /**
     * Parse a URL, preferring AIO but falling back to scraping.
     * @param {string} url - The URL to parse
     * @param {string} [query] - Optional query to target specific chunks
     * @returns {Promise<Object>} ContentEnvelope
     */
    async parse(url, query = null) {
        console.log(`[AIOParser] Processing: ${url}`);

        // 1. Discovery
        const discovery = await discoverAIO(url, this.timeout);

        // 2. Fetching
        if (discovery.aioUrl) {
            console.log(`[AIOParser] AIO found via ${discovery.method}: ${discovery.aioUrl}`);
            try {
                return await fetchAIO(discovery.aioUrl, url, query, this.timeout);
            } catch (err) {
                console.warn(`[AIOParser] AIO fetch failed: ${err.message}. Falling back.`);
                // Fallthrough to fallback
            }
        } else {
            console.log(`[AIOParser] No AIO signals found.`);
        }

        // 3. Fallback
        return await fetchScraped(url, this.timeout);
    }
}

module.exports = {
    AIOParser,
    parse: async (url, query) => new AIOParser().parse(url, query)
};
