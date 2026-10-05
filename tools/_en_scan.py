"""Audit: which visible English strings are still authored into the markup?

Strips <style>/<script>, walks the remaining markup, and prints every text node
that carries a run of Latin letters after removing the allow-list of brands and
indicator abbreviations the brief says may stay. Used to close the §5 complaint
about leftover English in the Persian UI.
"""
import re, sys, html

SRC = open('dashboard_html.py', encoding='utf-8').read()

ALLOW = {
    'EMA', 'SMA', 'MACD', 'RSI', 'BB', 'ATR', 'TV', 'TradingView', 'CoinGecko', 'Yahoo',
    'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'NZD', 'CAD', 'CHF', 'CNY', 'IRR', 'BTC', 'ETH',
    'SOL', 'XRP', 'BNB', 'DOGE', 'ADA', 'LINK', 'XAU', 'XAG', 'WTI', 'DXY', 'SPX', 'VIX',
    'API', 'JSON', 'URL', 'ID', 'PE', 'EPS', 'UTC', 'OK', 'TB', 'GB', 'MB', 'KB', 'TV',
    'POST', 'GET', 'HTML', 'CSS', 'JS', 'ETF', 'USD', 'USDT', 'AM', 'PM', 'PERP',
    'BTCUSD', 'ETHUSD', 'SPY', 'QQQ', 'IBIT', 'FBTC', 'GBTC', 'ARKB', 'BITB', 'HODL',
    'NASDAQ', 'CME', 'FED', 'FOMC', 'CPI', 'PPI', 'GDP', 'NFP', 'JOLTS', 'PMI', 'PCE',
}

def strip_blocks(src):
    out = re.sub(r'<style>.*?</style>', '<style></style>', src, flags=re.S)
    out = re.sub(r'<script\b.*?</script>', '<script></script>', out, flags=re.S)
    return out

def main():
    body = SRC.split('<body>', 1)[1] if '<body>' in SRC else SRC
    body = strip_blocks(body)
    # text between tags
    hits = {}
    for m in re.finditer(r'>([^<>]{2,400})<', body):
        t = html.unescape(m.group(1)).strip()
        if not t:
            continue
        words = re.findall(r'[A-Za-z][A-Za-z\-\']{1,}', t)
        bad = [w for w in words if w.upper() not in ALLOW and w not in ALLOW]
        if bad:
            line = body[:m.start()].count('\n') + 1
            hits.setdefault(t[:120], (line, bad))
    for t, (line, bad) in hits.items():
        print(f'~{line}: {bad}  ::  {t}')
    print(f'--- {len(hits)} node(s) with non-allow-listed Latin text')

if __name__ == '__main__':
    main()
