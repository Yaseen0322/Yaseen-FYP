import React from 'react';

function Privacy() {
  return (
    <div className="space-y-8 animate-fade-in max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold text-white">Privacy Information</h1>
        <p className="text-white/40 mt-1">Understanding what we track and how we protect your privacy</p>
      </div>

      {/* What We Track */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="text-emerald-400">✓</span>
          What We Track
        </h3>
        <div className="space-y-4">
          <TrackingItem
            icon="⏱️"
            title="Application Usage Time"
            description="We track which applications you use and for how long. Only app names are stored, not the content of what you're working on."
          />
          <TrackingItem
            icon="💤"
            title="Idle Time"
            description="We detect when you're away from your computer by monitoring keyboard and mouse inactivity. No keystrokes or movements are logged."
          />
          <TrackingItem
            icon="👤"
            title="Presence Detection"
            description="Using your webcam, we detect if someone is at the desk. Only 'present' or 'absent' status is stored - no images or video are captured."
          />
          <TrackingItem
            icon="🌐"
            title="Website Domains"
            description="We track which websites you visit and categorize them as productive or unproductive. Only domain names are stored, not page content or URLs."
          />
        </div>
      </div>

      {/* What We DO NOT Track */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="text-rose-400">✗</span>
          What We DO NOT Track
        </h3>
        <div className="space-y-4">
          <PrivacyItem
            icon="📸"
            title="No Screenshots"
            description="We never take screenshots of your screen. Your work content remains private."
          />
          <PrivacyItem
            icon="📷"
            title="No Camera Images or Video"
            description="We only detect presence (face visible or not). No photos or videos are ever captured or stored."
          />
          <PrivacyItem
            icon="⌨️"
            title="No Keystroke Logging"
            description="We never record what you type. Only idle detection uses keyboard activity."
          />
          <PrivacyItem
            icon="🎤"
            title="No Audio Recording"
            description="We do not access your microphone or record any audio."
          />
          <PrivacyItem
            icon="📄"
            title="No Document Content"
            description="We never access or read the content of your files, documents, or messages."
          />
        </div>
      </div>

      {/* Data Security */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="text-blue-400">🔒</span>
          How We Protect Your Data
        </h3>
        <ul className="space-y-3 text-white/70">
          <li className="flex items-start gap-3">
            <span className="text-primary-400">•</span>
            <span>All data is encrypted in transit using TLS/HTTPS</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-primary-400">•</span>
            <span>Data is stored securely with access controls</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-primary-400">•</span>
            <span>Only authorized managers can view your reports</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-primary-400">•</span>
            <span>Data retention policies ensure old data is automatically deleted</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-primary-400">•</span>
            <span>You can view exactly what data is collected about you</span>
          </li>
        </ul>
      </div>

      {/* Your Rights */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="text-purple-400">⚖️</span>
          Your Rights
        </h3>
        <ul className="space-y-3 text-white/70">
          <li className="flex items-start gap-3">
            <span className="text-primary-400">•</span>
            <span>Right to view all data collected about you</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-primary-400">•</span>
            <span>Right to request correction of inaccurate data</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-primary-400">•</span>
            <span>Right to know how your data is used</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-primary-400">•</span>
            <span>Contact your organization's administrator for any privacy concerns</span>
          </li>
        </ul>
      </div>

      {/* Tracking Status */}
      <div className="card p-6 bg-gradient-to-r from-primary-500/10 to-accent-500/10">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">Tracking Status</h3>
            <p className="text-white/40 text-sm mt-1">
              You can see tracking is active via the system tray icon
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="status-online"></span>
            <span className="text-emerald-400 font-medium">Tracking ON</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function TrackingItem({ icon, title, description }) {
  return (
    <div className="flex gap-4 p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20">
      <span className="text-2xl">{icon}</span>
      <div>
        <p className="text-white font-medium">{title}</p>
        <p className="text-white/60 text-sm mt-1">{description}</p>
      </div>
    </div>
  );
}

function PrivacyItem({ icon, title, description }) {
  return (
    <div className="flex gap-4 p-4 rounded-xl bg-rose-500/5 border border-rose-500/20">
      <span className="text-2xl">{icon}</span>
      <div>
        <p className="text-white font-medium">{title}</p>
        <p className="text-white/60 text-sm mt-1">{description}</p>
      </div>
    </div>
  );
}

export default Privacy;
