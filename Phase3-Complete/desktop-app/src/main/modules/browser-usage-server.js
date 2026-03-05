/**
 * Browser Usage Server
 * Receives usage events from browser extension and stores locally.
 */
const http = require('http');

class BrowserUsageServer {
    constructor(localStorage, options = {}) {
        this.localStorage = localStorage;
        this.port = options.port || 8080;
        this.host = options.host || '127.0.0.1';
        this.server = null;
    }

    start() {
        if (this.server) return;

        this.server = http.createServer((req, res) => {
            // Minimal CORS handling for extension calls.
            res.setHeader('Access-Control-Allow-Origin', '*');
            res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
            res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

            if (req.method === 'OPTIONS') {
                res.writeHead(204);
                res.end();
                return;
            }

            if (req.method !== 'POST' || req.url !== '/browser-usage') {
                res.writeHead(404, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Not found' }));
                return;
            }

            let raw = '';
            req.on('data', (chunk) => {
                raw += chunk.toString();
                if (raw.length > 5 * 1024 * 1024) {
                    req.destroy();
                }
            });

            req.on('end', () => {
                try {
                    const payload = JSON.parse(raw || '{}');
                    const items = Array.isArray(payload.items) ? payload.items : [];

                    let accepted = 0;
                    for (const item of items) {
                        if (!item?.domain || !item?.start_ts || !item?.end_ts || !item?.duration_sec) {
                            continue;
                        }

                        this.localStorage.saveBrowserUsage({
                            browser: item.browser || 'Unknown',
                            domain: item.domain,
                            start_ts: item.start_ts,
                            end_ts: item.end_ts,
                            duration_sec: Number(item.duration_sec) || 0
                        });
                        accepted += 1;
                    }

                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ message: 'ok', accepted }));
                } catch (error) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Invalid JSON' }));
                }
            });
        });

        this.server.listen(this.port, this.host, () => {
            console.log(`[BrowserUsageServer] Listening on http://${this.host}:${this.port}/browser-usage`);
        });

        this.server.on('error', (error) => {
            console.error('[BrowserUsageServer] Error:', error.message);
        });
    }

    stop() {
        if (!this.server) return;
        this.server.close();
        this.server = null;
        console.log('[BrowserUsageServer] Stopped');
    }
}

module.exports = { BrowserUsageServer };
