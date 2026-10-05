"""Discord bot for FreeBuff notifications.
Requires: DISCORD_BOT_TOKEN in settings.json

Usage:
    from integrations.discord_bot import DiscordBot
    bot = DiscordBot(token="...", channel_id=123456)
    bot.send_digest({"BTC": {...}, "ETH": {...}})
"""

import requests
import json
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger('freebuff.discord')


class DiscordBot:
    """Simple Discord webhook/bot client."""
    
    def __init__(self, token: Optional[str] = None, channel_id: Optional[int] = None,
                 webhook_url: Optional[str] = None):
        self.token = token
        self.channel_id = channel_id
        self.webhook_url = webhook_url
        self.base_url = "https://discord.com/api/v10"
        self._session = requests.Session()
        if token:
            self._session.headers.update({"Authorization": f"Bot {token}"})
    
    def _send_webhook(self, embed: Dict) -> bool:
        """Send via webhook (simpler, no bot token needed)."""
        if not self.webhook_url:
            return False
        try:
            payload = {"embeds": [embed]}
            resp = self._session.post(self.webhook_url, json=payload, timeout=10)
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Discord webhook failed: {e}")
            return False
    
    def _send_message(self, embed: Dict) -> bool:
        """Send via bot API."""
        if not self.token or not self.channel_id:
            return False
        try:
            url = f"{self.base_url}/channels/{self.channel_id}/messages"
            payload = {"embeds": [embed]}
            resp = self._session.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Discord API failed: {e}")
            return False
    
    def _send(self, embed: Dict) -> bool:
        """Try webhook first, fallback to bot API."""
        return self._send_webhook(embed) or self._send_message(embed)
    
    def send_digest(self, reports: Dict, articles_count: int = 0) -> bool:
        """Send market digest to Discord."""
        # Build embed
        fields = []
        for symbol, data in reports.items():
            if isinstance(data, dict) and not data.get('error'):
                sections = data.get('sections', [])
                # Get first section summary
                if sections and len(sections) > 0:
                    summary = sections[0][1].get('summary', '')[:100] if isinstance(sections[0], (list, tuple)) and len(sections[0]) > 1 else ''
                    trend = sections[0][1].get('trend', '') if isinstance(sections[0], (list, tuple)) and len(sections[0]) > 1 else ''
                    emoji = '🟢' if 'صعود' in str(trend) or 'bull' in str(trend).lower() else '🔴' if 'نزول' in str(trend) or 'bear' in str(trend).lower() else '➡️'
                    
                    fields.append({
                        "name": f"{emoji} {symbol}",
                        "value": summary[:100] if summary else "No data",
                        "inline": True
                    })
        
        if not fields:
            fields.append({"name": "No Data", "value": "Reports not yet generated", "inline": False})
        
        embed = {
            "title": "📊 FreeBuff Market Digest",
            "description": f"Updated {time.strftime('%Y-%m-%d %H:%M UTC')}\n{articles_count} articles analyzed",
            "color": 0xf59e0b,
            "fields": fields[:25],  # Discord limit: 25 fields
            "footer": {"text": "FreeBuff Dashboard"},
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        
        return self._send(embed)
    
    def send_alert(self, title: str, message: str, color: int = 0xf59e0b) -> bool:
        """Send a custom alert."""
        embed = {
            "title": f"⚠️ {title}",
            "description": message,
            "color": color,
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        return self._send(embed)
    
    def send_anomaly_alert(self, anomalies: list) -> bool:
        """Send news anomaly alert."""
        if not anomalies:
            return True
        
        desc_lines = [f"**{a['symbol']}**: {a['current_count']} articles (avg: {a['avg_count']}, ratio: {a['ratio']}x)" for a in anomalies]
        
        embed = {
            "title": "🚨 News Volume Anomaly Detected",
            "description": "\n".join(desc_lines),
            "color": 0xef4444,
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        return self._send(embed)
