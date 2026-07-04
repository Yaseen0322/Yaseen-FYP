const PRODUCTIVE_APP_KEYWORDS = [
    'code', 'studio', 'ide', 'terminal', 'git', 'docker', 'office', 'word',
    'excel', 'powerpoint', 'outlook', 'slack', 'teams', 'zoom', 'figma',
    'sketch', 'photoshop', 'illustrator', 'xcode', 'android', 'postman',
    'insomnia'
];

const UNPRODUCTIVE_APP_KEYWORDS = [
    'game', 'steam', 'epic', 'spotify', 'music', 'video', 'vlc', 'netflix',
    'discord', 'telegram'
];

const DOMAIN_PATTERNS = [
    {
        label: 'productive',
        category: 'Development/Work',
        keywords: [
            'github', 'gitlab', 'bitbucket', 'stackoverflow', 'docs',
            'documentation', 'api', 'dev', 'developer', 'cloud', 'aws',
            'azure', 'gcp', 'jira', 'confluence', 'notion', 'figma',
            'linear', 'asana', 'trello', 'monday', 'slack', 'teams',
            'zoom', 'meet', 'calendar'
        ],
        domains: [
            'github.com', 'gitlab.com', 'stackoverflow.com', 'docs.google.com',
            'notion.so', 'figma.com', 'linear.app', 'asana.com', 'trello.com',
            'slack.com', 'teams.microsoft.com', 'zoom.us'
        ]
    },
    {
        label: 'productive',
        category: 'Learning',
        keywords: [
            'learn', 'course', 'tutorial', 'education', 'training', 'academy',
            'university', 'school', 'study', 'lecture'
        ],
        domains: [
            'coursera.org', 'udemy.com', 'edx.org', 'pluralsight.com',
            'skillshare.com', 'khan.academy'
        ]
    },
    {
        label: 'unproductive',
        category: 'Social/Entertainment',
        keywords: [
            'facebook', 'twitter', 'instagram', 'tiktok', 'snapchat',
            'youtube', 'netflix', 'hulu', 'disney', 'twitch', 'reddit',
            'game', 'gaming', 'play', 'bet', 'casino'
        ],
        domains: [
            'facebook.com', 'twitter.com', 'instagram.com', 'tiktok.com',
            'youtube.com', 'netflix.com', 'reddit.com', 'twitch.tv'
        ]
    }
];

function getLocalDateString(date = new Date()) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function getDayBounds(dateString) {
    const [year, month, day] = String(dateString || getLocalDateString()).split('-').map(Number);
    const start = new Date(year, month - 1, day, 0, 0, 0, 0);
    const end = new Date(year, month - 1, day + 1, 0, 0, 0, 0);
    return { start, end };
}

function parseDate(value) {
    const date = value instanceof Date ? value : new Date(value);
    return Number.isFinite(date.getTime()) ? date : null;
}

function clipInterval(startValue, endValue, rangeStart, rangeEnd) {
    const start = parseDate(startValue);
    const end = parseDate(endValue);
    if (!start || !end) return null;

    const clippedStart = new Date(Math.max(start.getTime(), rangeStart.getTime()));
    const clippedEnd = new Date(Math.min(end.getTime(), rangeEnd.getTime()));
    if (clippedEnd <= clippedStart) return null;
    return [clippedStart, clippedEnd];
}

function durationSec([start, end]) {
    return Math.max(0, Math.floor((end - start) / 1000));
}

function mergeIntervals(intervals) {
    const ordered = intervals
        .filter(Boolean)
        .sort((a, b) => a[0] - b[0]);
    if (!ordered.length) return [];

    const merged = [ordered[0]];
    for (const [start, end] of ordered.slice(1)) {
        const last = merged[merged.length - 1];
        if (start <= last[1]) {
            last[1] = new Date(Math.max(last[1].getTime(), end.getTime()));
        } else {
            merged.push([start, end]);
        }
    }
    return merged;
}

function subtractIntervals(baseIntervals, subtractIntervalsInput) {
    const subtracts = mergeIntervals(subtractIntervalsInput);
    const result = [];

    for (const [baseStart, baseEnd] of baseIntervals) {
        let cursor = baseStart;
        for (const [subtractStart, subtractEnd] of subtracts) {
            if (subtractEnd <= cursor) continue;
            if (subtractStart >= baseEnd) break;
            if (subtractStart > cursor) {
                result.push([cursor, new Date(Math.min(subtractStart.getTime(), baseEnd.getTime()))]);
            }
            cursor = new Date(Math.max(cursor.getTime(), subtractEnd.getTime()));
            if (cursor >= baseEnd) break;
        }
        if (cursor < baseEnd) result.push([cursor, baseEnd]);
    }

    return result;
}

function sumIntervals(intervals) {
    return intervals.reduce((total, interval) => total + durationSec(interval), 0);
}

function classifyApp(appName) {
    const value = String(appName || '').toLowerCase();
    if (PRODUCTIVE_APP_KEYWORDS.some((keyword) => value.includes(keyword))) {
        return { category: 'Development/Work', label: 'productive' };
    }
    if (UNPRODUCTIVE_APP_KEYWORDS.some((keyword) => value.includes(keyword))) {
        return { category: 'Entertainment', label: 'unproductive' };
    }
    return { category: 'Other', label: 'neutral' };
}

function classifyDomain(domain) {
    const value = normalizeDomain(domain);
    for (const pattern of DOMAIN_PATTERNS) {
        if (pattern.domains.some((candidate) => value.includes(candidate))) {
            return { category: pattern.category, label: pattern.label };
        }
    }
    for (const pattern of DOMAIN_PATTERNS) {
        if (pattern.keywords.some((keyword) => value.includes(keyword))) {
            return { category: pattern.category, label: pattern.label };
        }
    }
    return { category: 'Other', label: 'neutral' };
}

function normalizeDomain(domain) {
    return String(domain || '')
        .trim()
        .toLowerCase()
        .replace(/^\.+|\.+$/g, '')
        .replace(/^www\./, '');
}

function currentRecordFromTracker(stats) {
    if (!stats?.isRunning || stats?.isPaused || !stats.currentApp || !stats.trackingSince) {
        return null;
    }
    const end = new Date();
    const start = parseDate(stats.trackingSince);
    if (!start || end <= start) return null;
    return {
        app_name: stats.currentApp,
        window_title: stats.currentWindowTitle || null,
        start_ts: start.toISOString(),
        end_ts: end.toISOString(),
        duration_sec: Math.floor((end - start) / 1000)
    };
}

function currentIdleFromStats(stats) {
    if (!stats?.isRunning || stats?.isPaused || !stats.isIdle || !stats.idleSince) return null;
    const end = new Date();
    const start = parseDate(stats.idleSince);
    if (!start || end <= start) return null;
    return {
        start_ts: start.toISOString(),
        end_ts: end.toISOString(),
        duration_sec: Math.floor((end - start) / 1000)
    };
}

function currentPresenceFromStats(stats) {
    if (!stats?.isRunning || stats?.isPaused || !stats.currentState || !stats.stateSince) return null;
    const end = new Date();
    const start = parseDate(stats.stateSince);
    if (!start || end <= start) return null;
    return {
        state: stats.currentState,
        start_ts: start.toISOString(),
        end_ts: end.toISOString(),
        duration_sec: Math.floor((end - start) / 1000)
    };
}

function getReportRecords(localStorage, liveState = {}) {
    if (!localStorage) {
        return { appUsage: [], idleIntervals: [], presenceIntervals: [], browserUsage: [] };
    }

    const appUsage = [...localStorage.getUnsyncdAppUsage()];
    const idleIntervals = [...localStorage.getUnsyncdIdleIntervals()];
    const presenceIntervals = [...localStorage.getUnsyncdPresenceIntervals()];
    const browserUsage = [...localStorage.getUnsyncdBrowserUsage()];

    const liveApp = currentRecordFromTracker(liveState.activity);
    const liveIdle = currentIdleFromStats(liveState.idle);
    const livePresence = currentPresenceFromStats(liveState.presence);

    if (liveApp) appUsage.push(liveApp);
    if (liveIdle) idleIntervals.push(liveIdle);
    if (livePresence) presenceIntervals.push(livePresence);

    return { appUsage, idleIntervals, presenceIntervals, browserUsage };
}

function buildLocalDailySummary(localStorage, dateString, liveState = {}) {
    const { start: rangeStart, end: rangeEnd } = getDayBounds(dateString);
    const records = getReportRecords(localStorage, liveState);

    const appIntervals = [];
    const idleIntervals = [];
    const presenceByState = new Map();
    const productivityByLabel = new Map();
    const topApps = new Map();
    const topDomains = new Map();

    for (const record of records.idleIntervals) {
        const interval = clipInterval(record.start_ts, record.end_ts, rangeStart, rangeEnd);
        if (interval) idleIntervals.push(interval);
    }
    const mergedIdle = mergeIntervals(idleIntervals);

    for (const record of records.appUsage) {
        const interval = clipInterval(record.start_ts, record.end_ts, rangeStart, rangeEnd);
        if (!interval) continue;

        const activeIntervals = subtractIntervals([interval], mergedIdle);
        const activeDuration = sumIntervals(activeIntervals);
        if (activeDuration <= 0) continue;

        appIntervals.push(...activeIntervals);
        topApps.set(record.app_name, (topApps.get(record.app_name) || 0) + activeDuration);

        const { label } = classifyApp(record.app_name);
        if (!productivityByLabel.has(label)) productivityByLabel.set(label, []);
        productivityByLabel.get(label).push(...activeIntervals);
    }

    for (const record of records.presenceIntervals) {
        const interval = clipInterval(record.start_ts, record.end_ts, rangeStart, rangeEnd);
        if (!interval) continue;
        if (!presenceByState.has(record.state)) presenceByState.set(record.state, []);
        presenceByState.get(record.state).push(interval);
    }

    for (const record of records.browserUsage) {
        const interval = clipInterval(record.start_ts, record.end_ts, rangeStart, rangeEnd);
        if (!interval) continue;

        const domain = normalizeDomain(record.domain);
        const classification = classifyDomain(domain);
        const key = `${domain}|${classification.category}|${classification.label}`;
        topDomains.set(key, (topDomains.get(key) || 0) + durationSec(interval));

        if (!productivityByLabel.has(classification.label)) productivityByLabel.set(classification.label, []);
        productivityByLabel.get(classification.label).push(interval);
    }

    const top_apps = [...topApps.entries()]
        .map(([app_name, duration_sec]) => ({ app_name, duration_sec }))
        .sort((a, b) => b.duration_sec - a.duration_sec)
        .slice(0, 10);

    const top_domains = [...topDomains.entries()]
        .map(([key, duration_sec]) => {
            const [domain, category, label] = key.split('|');
            return { domain, category, label, duration_sec };
        })
        .sort((a, b) => b.duration_sec - a.duration_sec)
        .slice(0, 10);

    return {
        user_id: null,
        date: dateString,
        focus_sec: sumIntervals(mergeIntervals(appIntervals)),
        idle_sec: sumIntervals(mergedIdle),
        present_sec: sumIntervals(mergeIntervals(presenceByState.get('present') || [])),
        absent_sec: sumIntervals(mergeIntervals(presenceByState.get('absent') || [])),
        camera_off_sec: sumIntervals(mergeIntervals(presenceByState.get('camera_off') || [])),
        productive_sec: sumIntervals(mergeIntervals(productivityByLabel.get('productive') || [])),
        unproductive_sec: sumIntervals(mergeIntervals(productivityByLabel.get('unproductive') || [])),
        neutral_sec: sumIntervals(mergeIntervals(productivityByLabel.get('neutral') || [])),
        top_apps,
        top_domains
    };
}

function buildLocalTimeline(localStorage, dateString, liveState = {}) {
    const { start: rangeStart, end: rangeEnd } = getDayBounds(dateString);
    const records = getReportRecords(localStorage, liveState);
    const blocks = [];

    const pushBlock = (type, record, details = null) => {
        const interval = clipInterval(record.start_ts, record.end_ts, rangeStart, rangeEnd);
        if (!interval) return;
        blocks.push({
            type,
            start_ts: interval[0].toISOString(),
            end_ts: interval[1].toISOString(),
            duration_sec: durationSec(interval),
            details
        });
    };

    for (const record of records.presenceIntervals) {
        pushBlock(record.state, record);
    }
    for (const record of records.idleIntervals) {
        pushBlock('idle', record);
    }
    for (const record of records.appUsage) {
        pushBlock('app_usage', record, { app_name: record.app_name });
    }
    for (const record of records.browserUsage) {
        const domain = normalizeDomain(record.domain);
        const classification = classifyDomain(domain);
        pushBlock('browser_usage', record, {
            domain,
            category: classification.category,
            label: classification.label
        });
    }

    return {
        date: dateString,
        blocks: coalesceTimelineBlocks(blocks).sort((a, b) => new Date(b.start_ts) - new Date(a.start_ts))
    };
}

function mergeSummaries(serverSummary, localSummary) {
    const base = serverSummary || {
        user_id: null,
        date: localSummary?.date || getLocalDateString(),
        focus_sec: 0,
        idle_sec: 0,
        present_sec: 0,
        absent_sec: 0,
        camera_off_sec: 0,
        productive_sec: 0,
        unproductive_sec: 0,
        neutral_sec: 0,
        top_apps: [],
        top_domains: []
    };
    if (!localSummary) return base;

    const merged = { ...base };
    for (const key of [
        'focus_sec', 'idle_sec', 'present_sec', 'absent_sec', 'camera_off_sec',
        'productive_sec', 'unproductive_sec', 'neutral_sec'
    ]) {
        merged[key] = (base[key] || 0) + (localSummary[key] || 0);
    }

    const apps = new Map();
    for (const item of [...(base.top_apps || []), ...(localSummary.top_apps || [])]) {
        apps.set(item.app_name, (apps.get(item.app_name) || 0) + (item.duration_sec || 0));
    }
    merged.top_apps = [...apps.entries()]
        .map(([app_name, duration_sec]) => ({ app_name, duration_sec }))
        .sort((a, b) => b.duration_sec - a.duration_sec)
        .slice(0, 10);

    const domains = new Map();
    for (const item of [...(base.top_domains || []), ...(localSummary.top_domains || [])]) {
        const key = `${item.domain}|${item.category || 'Other'}|${item.label || 'neutral'}`;
        domains.set(key, (domains.get(key) || 0) + (item.duration_sec || 0));
    }
    merged.top_domains = [...domains.entries()]
        .map(([key, duration_sec]) => {
            const [domain, category, label] = key.split('|');
            return { domain, category, label, duration_sec };
        })
        .sort((a, b) => b.duration_sec - a.duration_sec)
        .slice(0, 10);

    return merged;
}

function mergeTimelines(serverTimeline, localTimeline) {
    const blocks = coalesceTimelineBlocks(dedupeTimelineBlocks([
        ...((serverTimeline && serverTimeline.blocks) || []),
        ...((localTimeline && localTimeline.blocks) || [])
    ])).sort((a, b) => new Date(b.start_ts) - new Date(a.start_ts));

    return {
        date: localTimeline?.date || serverTimeline?.date || getLocalDateString(),
        blocks
    };
}

function dedupeTimelineBlocks(blocks) {
    const seen = new Set();
    const deduped = [];

    for (const block of blocks) {
        const details = block.details ? JSON.stringify(block.details, Object.keys(block.details).sort()) : '';
        const key = [
            block.type,
            new Date(block.start_ts).getTime(),
            new Date(block.end_ts).getTime(),
            block.duration_sec,
            details
        ].join('|');

        if (seen.has(key)) continue;
        seen.add(key);
        deduped.push(block);
    }

    return deduped;
}

function detailsKey(block) {
    if (!block.details) return '';
    return JSON.stringify(block.details, Object.keys(block.details).sort());
}

function coalesceTimelineBlocks(blocks, maxGapMs = 3000) {
    const ordered = [...blocks]
        .filter((block) => block && block.start_ts && block.end_ts)
        .sort((a, b) => new Date(a.start_ts) - new Date(b.start_ts));
    const buckets = new Map();

    for (const block of ordered) {
        const normalized = { ...block };
        const bucketKey = `${normalized.type}|${detailsKey(normalized)}`;
        if (!buckets.has(bucketKey)) buckets.set(bucketKey, []);
        const bucket = buckets.get(bucketKey);
        const last = bucket[bucket.length - 1];

        if (!last) {
            bucket.push(normalized);
            continue;
        }

        const gapMs = new Date(normalized.start_ts).getTime() - new Date(last.end_ts).getTime();
        if (gapMs <= maxGapMs) {
            if (new Date(normalized.end_ts) > new Date(last.end_ts)) {
                last.end_ts = normalized.end_ts;
            }
            last.duration_sec = Math.max(1, Math.floor(
                (new Date(last.end_ts).getTime() - new Date(last.start_ts).getTime()) / 1000
            ));
        } else {
            bucket.push(normalized);
        }
    }

    return [...buckets.values()].flat();
}

module.exports = {
    buildLocalDailySummary,
    buildLocalTimeline,
    classifyApp,
    classifyDomain,
    coalesceTimelineBlocks,
    getLocalDateString,
    mergeSummaries,
    mergeTimelines
};
