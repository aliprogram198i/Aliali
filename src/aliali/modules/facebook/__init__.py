from aliali.core.models import ModuleInfo

FACEBOOK_MODULES = [
    ModuleInfo("facebook.account_intel", "👤 Account Intelligence", "Analyze authorized/public account data.", "facebook"),
    ModuleInfo("facebook.post_analysis", "📝 Post Analysis", "Analyze authorized/public posts and media.", "facebook"),
    ModuleInfo("facebook.osint", "🔎 Public OSINT", "Correlate lawful public-source intelligence.", "facebook"),
    ModuleInfo("facebook.risk_scan", "🛡️ Risk Scan", "Assess phishing, scam, and exposure indicators.", "facebook"),
    ModuleInfo("facebook.evidence", "📁 Evidence", "Preserve evidence metadata and integrity records.", "facebook"),
]
