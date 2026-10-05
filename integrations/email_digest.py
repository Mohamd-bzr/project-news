"""Weekly email digest for FreeBuff.
Sends HTML email with market summary, sentiment, and top articles.

Requires: SMTP settings in settings.json
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import logging
from typing import Dict, List

logger = logging.getLogger('freebuff.email')


def build_digest_html(reports: Dict, articles: List[Dict], sentiment: Dict) -> str:
    """Build HTML email body."""
    # Sentiment summary
    sentiment_rows = ""
    for sym in ['BTC', 'ETH', 'SOL', 'GOLD']:
        s = sentiment.get(sym, {})
        score = s.get('avg_score', 0)
        color = '#22c55e' if score > 0.1 else '#ef4444' if score < -0.1 else '#6b7280'
        emoji = '🟢' if score > 0.1 else '🔴' if score < -0.1 else '⚪'
        sentiment_rows += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #333;">{sym}</td>
            <td style="padding: 8px; border-bottom: 1px solid #333; color: {color};">{emoji} {score:+.2f}</td>
            <td style="padding: 8px; border-bottom: 1px solid #333;">{s.get('total', 0)}</td>
        </tr>
        """
    
    # Top articles
    article_rows = ""
    sorted_articles = sorted(articles, key=lambda a: a.get('sentiment_score', 0), reverse=True)[:10]
    for a in sorted_articles:
        sent = a.get('sentiment_label', 'neutral')
        sent_color = '#22c55e' if sent == 'positive' else '#ef4444' if sent == 'negative' else '#6b7280'
        article_rows += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #333;">
                <a href="{a.get('link', '#')}" style="color: #f59e0b; text-decoration: none;">{a.get('title', 'No title')[:80]}</a>
            </td>
            <td style="padding: 8px; border-bottom: 1px solid #333; color: {sent_color};">{sent}</td>
            <td style="padding: 8px; border-bottom: 1px solid #333;">{a.get('source_name', '')}</td>
        </tr>
        """
    
    html = f"""
    <html>
    <body style="background: #0a0a1a; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto;">
            <h1 style="color: #f59e0b; border-bottom: 2px solid #f59e0b; padding-bottom: 10px;">
                📊 FreeBuff Weekly Digest
            </h1>
            <p style="color: #888;">{time.strftime('%B %d, %Y')} — {len(articles)} articles analyzed</p>
            
            <h2 style="color: #e0e0e0; font-size: 16px;">Sentiment Overview</h2>
            <table style="width: 100%; border-collapse: collapse; background: #1a1a2e; border-radius: 8px; overflow: hidden;">
                <tr style="background: #252540;">
                    <th style="padding: 8px; text-align: left;">Asset</th>
                    <th style="padding: 8px; text-align: left;">Sentiment</th>
                    <th style="padding: 8px; text-align: left;">Articles</th>
                </tr>
                {sentiment_rows}
            </table>
            
            <h2 style="color: #e0e0e0; font-size: 16px; margin-top: 20px;">Top Stories</h2>
            <table style="width: 100%; border-collapse: collapse; background: #1a1a2e; border-radius: 8px; overflow: hidden;">
                <tr style="background: #252540;">
                    <th style="padding: 8px; text-align: left;">Title</th>
                    <th style="padding: 8px; text-align: left;">Sentiment</th>
                    <th style="padding: 8px; text-align: left;">Source</th>
                </tr>
                {article_rows}
            </table>
            
            <p style="color: #555; font-size: 12px; margin-top: 30px; text-align: center;">
                FreeBuff — Real-time Financial News Dashboard<br>
                <a href="#" style="color: #f59e0b;">Unsubscribe</a>
            </p>
        </div>
    </body>
    </html>
    """
    return html


def send_digest_email(config: Dict, reports: Dict, articles: List[Dict], sentiment: Dict) -> bool:
    """Send digest email via SMTP.
    
    config = {
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_user': '...',
        'smtp_pass': '...',
        'from_addr': '...',
        'to_addrs': ['...'],
        'use_tls': True,
    }
    """
    try:
        html = build_digest_html(reports, articles, sentiment)
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"FreeBuff Weekly Digest — {time.strftime('%B %d')}"
        msg['From'] = config['from_addr']
        msg['To'] = ', '.join(config['to_addrs'])
        
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        
        context = ssl.create_default_context()
        with smtplib.SMTP(config['smtp_host'], config['smtp_port']) as server:
            if config.get('use_tls', True):
                server.starttls(context=context)
            server.login(config['smtp_user'], config['smtp_pass'])
            server.sendmail(config['from_addr'], config['to_addrs'], msg.as_string())
        
        logger.info("Email digest sent successfully")
        return True
    except Exception as e:
        logger.error(f"Email digest failed: {e}")
        return False
