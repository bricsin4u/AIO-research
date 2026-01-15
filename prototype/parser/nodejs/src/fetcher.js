const axios = require('axios');
const cheerio = require('cheerio');
const TurndownService = require('turndown');
const crypto = require('crypto');

const turndownService = new TurndownService();
turndownService.remove(['script', 'style', 'nav', 'footer', 'iframe', 'noscript']);

async function fetchAIO(aioUrl, sourceUrl, query, timeout) {
    const res = await axios.get(aioUrl, { timeout });
    const data = res.data;

    let selectedChunks = data.content;
    let method = "full";

    // Targeted Retrieval
    if (query && data.index) {
        const keywords = query.toLowerCase().split(' ').filter(w => w.length > 3);
        const matchedIds = new Set();

        data.index.forEach(item => {
            // Simple keyword match in title, id, or keywords
            const text = `${item.id} ${item.title} ${item.keywords.join(' ')}`.toLowerCase();
            if (keywords.some(k => text.includes(k))) {
                matchedIds.add(item.id);
            }
        });

        if (matchedIds.size > 0) {
            selectedChunks = data.content.filter(c => matchedIds.has(c.id));
            method = "targeted";
        }
    }

    const narrative = selectedChunks.map(c => c.content).join('\n\n');

    return {
        id: crypto.createHash('md5').update(sourceUrl).digest('hex'),
        source_url: sourceUrl,
        source_type: 'aio',
        narrative: narrative,
        tokens: Math.ceil(narrative.length / 4), // Rough estimate
        noise_score: 0.0,
        retrieval_method: method,
        chunks_count: selectedChunks.length
    };
}

async function fetchScraped(url, timeout) {
    const res = await axios.get(url, { timeout });
    const html = res.data;
    const $ = cheerio.load(html);

    // Noise removal
    $('nav, footer, script, style, header, aside, .cookie, .ad, .social').remove();

    // Main content selection
    let contentHtml = $('main').html() || $('body').html();

    const markdown = turndownService.turndown(contentHtml || "");
    const cleanMarkdown = markdown.replace(/\n\s*\n/g, '\n\n').trim();

    return {
        id: crypto.createHash('md5').update(url).digest('hex'),
        source_url: url,
        source_type: 'scraped',
        narrative: cleanMarkdown,
        tokens: Math.ceil(cleanMarkdown.length / 4),
        noise_score: 0.7, // High noise default
        retrieval_method: 'scrape'
    };
}

module.exports = { fetchAIO, fetchScraped };
