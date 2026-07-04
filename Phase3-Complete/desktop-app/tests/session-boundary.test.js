const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const tempHome = fs.mkdtempSync(path.join(os.tmpdir(), 'desktop-session-tests-'));
process.env.HOME = tempHome;
process.env.XDG_CONFIG_HOME = path.join(tempHome, '.config');

const Store = require('electron-store');
const { LocalStorage } = require('../src/main/modules/local-storage');
const { DataSync } = require('../src/main/modules/data-sync');
const { normalizeDomain } = require('../src/main/modules/browser-usage-server');
const {
    buildLocalDailySummary,
    buildLocalTimeline,
    coalesceTimelineBlocks,
    getLocalDateString,
    mergeTimelines,
    mergeSummaries,
} = require('../src/main/modules/local-reports');

test('tracking data is isolated per user namespace', () => {
    const aliceStorage = new LocalStorage('user-101');
    const bobStorage = new LocalStorage('user-202');

    aliceStorage.clearAll();
    bobStorage.clearAll();

    aliceStorage.saveAppUsage({
        app_name: 'VS Code',
        window_title: 'main.py',
        start_ts: '2026-01-01T10:00:00.000Z',
        end_ts: '2026-01-01T10:05:00.000Z',
        duration_sec: 300
    });

    assert.equal(aliceStorage.getUnsyncdAppUsage().length, 1);
    assert.equal(bobStorage.getUnsyncdAppUsage().length, 0);

    aliceStorage.clearAll();
    bobStorage.clearAll();
});

test('data sync reads current device id from shared store at sync time', () => {
    const sharedStore = new Store();
    sharedStore.delete('deviceId');

    const sync = new DataSync(
        { getUnsyncedCounts: () => ({ appUsage: 0, idleIntervals: 0, presenceIntervals: 0, browserUsage: 0 }) },
        'token'
    );

    assert.equal(sync.getDeviceId(), null);

    sharedStore.set('deviceId', 77);
    assert.equal(sync.getDeviceId(), 77);

    sharedStore.delete('deviceId');
});

test('local reports include live app focus and classify productive apps', () => {
    const storage = new LocalStorage('user-live-report');
    storage.clearAll();

    const now = new Date();
    const started = new Date(now.getTime() - 125000);
    const date = getLocalDateString(now);

    const summary = buildLocalDailySummary(storage, date, {
        activity: {
            isRunning: true,
            isPaused: false,
            currentApp: 'Code',
            currentWindowTitle: null,
            trackingSince: started,
        },
        idle: {
            isRunning: true,
            isPaused: false,
            isIdle: false,
            idleSince: null,
        },
        presence: {
            isRunning: true,
            isPaused: false,
            currentState: 'present',
            stateSince: started,
        },
    });

    assert.ok(summary.focus_sec >= 120);
    assert.ok(summary.productive_sec >= 120);
    assert.ok(summary.present_sec >= 120);

    storage.clearAll();
});

test('local reports subtract live idle from active focus', () => {
    const storage = new LocalStorage('user-idle-report');
    storage.clearAll();

    const now = new Date();
    const appStarted = new Date(now.getTime() - 180000);
    const idleStarted = new Date(now.getTime() - 65000);
    const date = getLocalDateString(now);

    const summary = buildLocalDailySummary(storage, date, {
        activity: {
            isRunning: true,
            isPaused: false,
            currentApp: 'Code',
            currentWindowTitle: null,
            trackingSince: appStarted,
        },
        idle: {
            isRunning: true,
            isPaused: false,
            isIdle: true,
            idleSince: idleStarted,
        },
        presence: null,
    });

    assert.ok(summary.idle_sec >= 60);
    assert.ok(summary.focus_sec >= 110 && summary.focus_sec <= 120);
    assert.ok(summary.productive_sec >= 110 && summary.productive_sec <= 120);

    storage.clearAll();
});

test('local timeline exposes live app and browser usage blocks', () => {
    const storage = new LocalStorage('user-timeline-report');
    storage.clearAll();

    const now = new Date();
    const browserStart = new Date(now.getTime() - 30000);
    const appStart = new Date(now.getTime() - 60000);
    const date = getLocalDateString(now);

    storage.saveBrowserUsage({
        browser: 'Chrome',
        domain: 'github.com',
        start_ts: browserStart.toISOString(),
        end_ts: now.toISOString(),
        duration_sec: 30,
    });

    const timeline = buildLocalTimeline(storage, date, {
        activity: {
            isRunning: true,
            isPaused: false,
            currentApp: 'Code',
            currentWindowTitle: null,
            trackingSince: appStart,
        },
    });

    assert.ok(timeline.blocks.some((block) => block.type === 'app_usage'));
    assert.ok(timeline.blocks.some((block) => (
        block.type === 'browser_usage' &&
        block.details.domain === 'github.com' &&
        block.details.label === 'productive'
    )));

    storage.clearAll();
});

test('summary merge combines local unsynced totals with backend totals', () => {
    const merged = mergeSummaries(
        {
            user_id: 1,
            date: '2026-06-28',
            focus_sec: 60,
            idle_sec: 0,
            present_sec: 60,
            absent_sec: 0,
            camera_off_sec: 0,
            productive_sec: 0,
            unproductive_sec: 0,
            neutral_sec: 60,
            top_apps: [{ app_name: 'Code', duration_sec: 60 }],
            top_domains: [],
        },
        {
            date: '2026-06-28',
            focus_sec: 30,
            idle_sec: 0,
            present_sec: 30,
            absent_sec: 0,
            camera_off_sec: 0,
            productive_sec: 30,
            unproductive_sec: 0,
            neutral_sec: 0,
            top_apps: [{ app_name: 'Code', duration_sec: 30 }],
            top_domains: [],
        }
    );

    assert.equal(merged.focus_sec, 90);
    assert.equal(merged.productive_sec, 30);
    assert.equal(merged.top_apps[0].duration_sec, 90);
});

test('timeline merge returns newest entries first and removes exact duplicates', () => {
    const older = {
        type: 'idle',
        start_ts: '2026-06-28T07:00:00.000+05:00',
        end_ts: '2026-06-28T07:05:00.000+05:00',
        duration_sec: 300,
        details: null,
    };
    const newer = {
        type: 'app_usage',
        start_ts: '2026-06-28T11:00:00.000+05:00',
        end_ts: '2026-06-28T11:10:00.000+05:00',
        duration_sec: 600,
        details: { app_name: 'Code' },
    };

    const merged = mergeTimelines(
        { date: '2026-06-28', blocks: [older, newer] },
        { date: '2026-06-28', blocks: [older] }
    );

    assert.equal(merged.blocks.length, 2);
    assert.equal(merged.blocks[0].type, 'app_usage');
    assert.equal(merged.blocks[1].type, 'idle');
});

test('local storage suppresses exact duplicate idle and browser records', () => {
    const storage = new LocalStorage('user-dedupe-records');
    storage.clearAll();

    const idleRecord = {
        start_ts: '2026-06-28T07:00:00.000Z',
        end_ts: '2026-06-28T07:05:00.000Z',
        duration_sec: 300,
    };
    storage.saveIdleInterval(idleRecord);
    storage.saveIdleInterval(idleRecord);

    const browserRecord = {
        browser: 'Chrome',
        domain: 'youtube.com',
        start_ts: '2026-06-28T07:05:00.000Z',
        end_ts: '2026-06-28T07:08:00.000Z',
        duration_sec: 180,
    };
    storage.saveBrowserUsage(browserRecord);
    storage.saveBrowserUsage(browserRecord);

    assert.equal(storage.getUnsyncdIdleIntervals().length, 1);
    assert.equal(storage.getUnsyncdBrowserUsage().length, 1);

    storage.clearAll();
});

test('browser usage server normalizes website domains for top website reports', () => {
    assert.equal(normalizeDomain('https://www.youtube.com/watch?v=1'), 'youtube.com');
    assert.equal(normalizeDomain('www.github.com.'), 'github.com');
    assert.equal(normalizeDomain('docs.google.com'), 'docs.google.com');
    assert.equal(normalizeDomain('localhost'), null);
});

test('timeline coalesces contiguous chunks without merging camera state changes', () => {
    const blocks = coalesceTimelineBlocks([
        {
            type: 'idle',
            start_ts: '2026-06-28T07:00:00.000Z',
            end_ts: '2026-06-28T07:01:00.000Z',
            duration_sec: 60,
            details: null,
        },
        {
            type: 'idle',
            start_ts: '2026-06-28T07:01:00.000Z',
            end_ts: '2026-06-28T07:03:00.000Z',
            duration_sec: 120,
            details: null,
        },
        {
            type: 'camera_off',
            start_ts: '2026-06-28T07:03:00.000Z',
            end_ts: '2026-06-28T07:04:00.000Z',
            duration_sec: 60,
            details: null,
        },
        {
            type: 'present',
            start_ts: '2026-06-28T07:04:00.000Z',
            end_ts: '2026-06-28T07:05:00.000Z',
            duration_sec: 60,
            details: null,
        },
    ]);

    assert.equal(blocks.length, 3);
    assert.equal(blocks[0].type, 'idle');
    assert.equal(blocks[0].duration_sec, 180);
    assert.equal(blocks[1].type, 'camera_off');
    assert.equal(blocks[2].type, 'present');
});
