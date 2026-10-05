#!/usr/bin/env python3
"""
Market Context — economic calendar, Fear & Greed, macro index quotes
====================================================================
All free and key-less:
  - ForexFactory weekly calendar (nfs.faireconomy.media)   -> /api/econ
  - Fear & Greed index          (alternative.me)          -> /api/econ
  - DXY / S&P500 / VIX / WTI    (Yahoo v8 chart API)      -> /api/econ
  - market sessions (weekday UTC windows)                 -> /api/econ
Every source fails independently and degrades to {"error": ...} — never raises.
"""

import re
import time
import json
from datetime import datetime, timezone, timedelta

import requests

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/128.0.0.0 Safari/537.36"),
}

CACHE = {"ts": 0.0, "data": None}
TTL = 900.0  # 15 minutes


# ---------------------------------------------------------------------------
# Market sessions (market24hclock-style, computed locally — no API needed)
# ---------------------------------------------------------------------------
SESSIONS = [
    # key, label(EN), icon, open-hour-UTC, close-hour-UTC, weekdays-open (Mon=0)
    {"key": "sydney", "label": "Sydney", "icon": "🇦🇺", "open": 21, "close": 6, "days": {6, 0, 1, 2, 3, 4}},
    {"key": "tokyo",  "label": "Tokyo",  "icon": "🇯🇵", "open": 0,  "close": 9, "days": {0, 1, 2, 3, 4}},
    {"key": "london", "label": "London", "icon": "🇬🇧", "open": 7,  "close": 16, "days": {0, 1, 2, 3, 4}},
    {"key": "newyork","label": "New York","icon": "🇺🇸", "open": 12, "close": 21, "days": {0, 1, 2, 3, 4}},
]


def market_sessions():
    """Which exchanges are open right now + minutes to next open/close.
    Static weekly schedule in UTC (winter hours — close enough for a glance).
    """
    from datetime import datetime
    now = datetime.now(timezone.utc)
    out = []
    for s in SESSIONS:
        o, c = s["open"], s["close"]
        wrap = c <= o
        is_open = (s["days"].__contains__(now.weekday()) and
                   ((o <= now.hour < c) if not wrap else (now.hour >= o or now.hour < c)))
        # minutes to next boundary (open if closed, close if open)
        nowm = now.hour * 60 + now.minute
        boundary = (c if is_open else o) * 60
        if wrap and is_open and now.hour < c:
            mins = boundary - nowm
        elif boundary > nowm:
            mins = boundary - nowm
        else:
            mins = 1440 - nowm + boundary
        out.append({"key": s["key"], "label": s["label"], "icon": s["icon"],
                    "open": is_open, "mins_to_change": mins,
                    "hours": f"{o:02d}:00-{c:02d}:00 UTC"})
    return out

IMPACT_FA = {"High": "بالا", "Medium": "متوسط", "Low": "کم", "Holiday": "تعطیلی"}
COUNTRY_FLAG = {
    "USD": "\U0001F1FA\U0001F1F8", "EUR": "\U0001F1EA\U0001F1FA",
    "GBP": "\U0001F1EC\U0001F1E7", "JPY": "\U0001F1EF\U0001F1F5",
    "CNY": "\U0001F1E8\U0001F1F3", "CAD": "\U0001F1E8\U0001F1E6",
    "AUD": "\U0001F1E6\U0001F1FA", "NZD": "\U0001F1F3\U0001F1FF",
    "CHF": "\U0001F1E8\U0001F1ED", "All": "\U0001F30D",
}
FNG_FA = {"Extreme Fear": "ترس شدید", "Fear": "ترس", "Neutral": "خنثی",
          "Greed": "طمع", "Extreme Greed": "طمع شدید"}

# ---------------------------------------------------------------------------
# "What is this event?" — a plain-English note per calendar row
# ---------------------------------------------------------------------------
# The calendar is English-only and every row explains itself in one or two
# lines: the glossary below covers the releases traders actually watch, and
# _event_doc() builds a readable note for everything else from the title
# itself (period, unit, "Core", "Flash", speeches, auctions, documents).
# Deterministic, offline, no model and no API key — same spirit as the rest of
# this pipeline.

IMPACT_NOTE = {
    "High": "Typically moves its currency and the assets priced in it.",
    "Medium": "Can move price when it surprises the forecast.",
    "Low": "Rarely moves price on its own — read it as context.",
    "Holiday": "Market holiday: banks and exchanges closed, liquidity thins out.",
}

PERIOD_NOTE = {
    "m/m": "month-over-month change",
    "y/y": "year-over-year change",
    "q/q": "quarter-over-quarter change",
    "w/w": "week-over-week change",
    "y": "annual figure",
}

COUNTRY_NAME = {
    "USD": "United States", "EUR": "Euro Area", "GBP": "United Kingdom",
    "JPY": "Japan", "CNY": "China", "AUD": "Australia", "CAD": "Canada",
    "CHF": "Switzerland", "NZD": "New Zealand",
}

EVENT_DOCS = {
    "non-farm employment change": "The monthly change in US jobs excluding farm workers — 120K+ new jobs means a strong labour market and usually rate-hike pressure.",
    "adp employment change": "Payroll processor ADP's own estimate of private-sector job growth — lands two days before the official NFP.",
    "unemployment rate": "Share of the labour force actively looking for work and jobless.",
    "average hourly earnings m/m": "Wage growth for the month — the inflation channel the Fed watches in the employment report.",
    "unemployment claims": "First-time US applications for jobless benefits in the past week — the fastest read on layoffs (lower is stronger).",
    "cpi m/m": "The month's change in the consumer price basket — the headline inflation number.",
    "core cpi m/m": "Consumer inflation with food and energy stripped out — the trend the central bank reacts to.",
    "cpi y/y": "Yearly consumer inflation rate — headline inflation against target.",
    "core cpi y/y": "Yearly core inflation, excluding food and energy.",
    "ppi m/m": "Change in prices paid to producers — pipeline inflation that later reaches consumers.",
    "core ppi m/m": "Producer prices excluding food and energy.",
    "retail sales m/m": "Growth in household spending at retailers — the main gauge of consumer demand.",
    "core retail sales m/m": "Retail sales excluding autos and fuel — the most stable consumer figure.",
    "gdp q/q": "Quarter-over-quarter economic growth; the first print is an estimate and is revised twice (Prelim, Final).",
    "prelim gdp q/q": "First revision of the quarterly GDP estimate.",
    "final gdp q/q": "Second and final revision of quarterly growth.",
    "interest rate decision": "The central bank's benchmark interest rate vote — the single biggest driver of that currency.",
    "federal funds rate": "The US Federal Reserve's target rate for overnight lending between banks.",
    "official bank rate": "The Bank of England's policy rate.",
    "cash rate": "The Reserve Bank of Australia's policy rate.",
    "policy rate": "A central bank's benchmark rate; unchanged reads as neutral, a hike/cut moves the currency hard.",
    "fomc statement": "The Fed's policy statement: rate decision, language and the balance-sheet stance in one document.",
    "fomc meeting minutes": "Detailed minutes of the Fed meeting — markets mine them for hawkish or dovish clues.",
    "fomc press conference": "The Fed Chair's Q&A after the rate decision; off-script answers can move any risk asset.",
    "monetary policy statement": "A central bank's written policy decision and outlook for the coming months.",
    "monetary policy assessment": "The Swiss National Bank's quarterly policy review and rate decision.",
    "rate statement": "A central bank's decision statement; forward guidance moves price more than the rate itself.",
    "press conference": "Central-bank leadership takes questions — guidance and tone drive the reaction.",
    "ecb press conference": "The ECB President explains the latest policy decision and answers questions.",
    "ism manufacturing pmi": "Survey of US purchasing managers in manufacturing; above 50 = expansion, below 50 = contraction.",
    "ism services pmi": "The services-sector version of the ISM survey — the larger slice of the US economy.",
    "flash manufacturing pmi": "First, partial read of the month's manufacturing PMI; revised later.",
    "flash services pmi": "First, partial read of the month's services PMI.",
    "cb consumer confidence": "Conference Board survey of how US households feel about jobs and spending.",
    "prelim uom consumer sentiment": "Preliminary University of Michigan household survey; inflation expectations are the market's focus.",
    "jolts job openings": "Number of unfilled US job vacancies — labour-demand pressure that feeds wages.",
    "building permits": "Permits issued for new construction — a forward signal for housing activity.",
    "housing starts": "New residential construction actually begun this month.",
    "existing home sales": "Sales of previously owned US homes, a volume read on the housing market.",
    "new home sales": "Contracts signed on newly built homes.",
    "durable goods orders m/m": "New orders for goods built to last three years or more — a capex signal.",
    "core durable goods orders m/m": "Durable-goods orders excluding volatile transport equipment.",
    "trade balance": "Exports minus imports — a surplus supports the currency, a widening deficit weighs on it.",
    "current account": "Broadest measure of cross-border trade, income and transfers for the period.",
    "industrial production m/m": "Change in factory, mine and utility output.",
    "manufacturing production m/m": "The factory-only slice of industrial production.",
    "factory orders m/m": "New orders to manufacturers for both durables and non-durables.",
    "crude oil inventories": "Weekly US commercial crude stocks (EIA); a build points to softer demand and pressures crude.",
    "natural gas storage": "Weekly change in US underground gas stocks — a weather-driven heating/cooling demand read.",
    "bank holiday": "Banks closed: some markets shut, liquidity thin, spreads wider.",
    "boc rate statement": "Bank of Canada policy decision and its guidance for the CAD.",
    "boe official bank rate": "Bank of England policy vote; the split among MPC members matters as much as the level.",
    "boj policy rate": "Bank of Japan policy rate and yield-curve stance — the driver of the yen and carry trades.",
    "ecb main refinancing rate": "The ECB's main policy rate for the euro area.",
    "snb policy rate": "Swiss National Bank policy rate; the CHF is highly sensitive to surprises here.",
    "rba rate statement": "Reserve Bank of Australia decision statement and outlook.",
    "boj core cpi y/y": "Japanese core inflation — the Bank of Japan's policy trigger.",
    "german ifo business climate": "Ifo survey of German business sentiment — the euro area's growth bellwether.",
}
EVENT_DOCS.update({
    "german gfk consumer climate": "Forward-looking German household confidence for the coming month.",
    "gfk consumer confidence": "UK consumer confidence survey — a spending-early signal for the pound.",
    "german flash manufacturing pmi": "First read of German factory activity, the euro area's industrial backbone.",
    "german flash services pmi": "First read of German services activity.",
    "french flash manufacturing pmi": "Preliminary French manufacturing survey.",
    "french flash services pmi": "Preliminary French services survey.",
    "zew economic sentiment": "German analyst-investor expectations for the next six months.",
    "employment change": "Net change in employed people for the period — the labour market's headline.",
    "nab quarterly business confidence": "Australian business-confidence survey, an early read on capex and hiring.",
    "rightmove hpi m/m": "Asking prices in the UK housing market, published by Rightmove.",
    "credit card spending y/y": "Household card spending, a nowcast for retail demand.",
    "public sector net borrowing": "UK government borrowing for the month; fiscal slippage can lift gilt yields.",
    "cbi industrial order expectations": "UK manufacturers' order books for the coming months.",
    "cbi realized sales": "UK retailers' reported sales volumes versus a year ago.",
    "richmond manufacturing index": "Regional US manufacturing diffusion index; 0 is the growth/contraction line.",
    "api weekly statistical bulletin": "American Petroleum Institute's weekly oil data — a preview of the EIA inventories.",
    "ecb economic bulletin": "The ECB's detailed economic analysis behind its latest policy decision.",
    "m3 money supply y/y": "Broad money growth, tracked by the ECB as a liquidity gauge.",
    "private loans y/y": "Yearly growth in bank lending to the private sector.",
    "cb leading index m/m": "Composite of leading indicators meant to anticipate the business cycle.",
    "belgian nbb business climate": "Belgian business survey, a small but early euro-area read.",
    "german buba monthly report": "The Bundesbank's monthly assessment of the German economy.",
    "tokyo core cpi y/y": "Tokyo inflation excluding fresh food — the earliest national CPI signal for Japan.",
    "tankan manufacturing index": "Bank of Japan survey of large manufacturers' sentiment.",
    "challenger job cuts": "Announced layoffs by US employers, a leading indicator for claims.",
    "treasury budget": "Monthly US federal budget balance.",
    "participation rate": "Share of the working-age population in the labour force.",
    "uom inflation expectations": "One-year household inflation expectations from the Michigan survey.",
})
# TradingView names the same releases differently — same glossary, other keys.
EVENT_DOCS.update({
    "non farm payrolls": "The monthly change in US jobs excluding farm workers. 120K+ new jobs means a firm labour market and usually rate-hike pressure; a negative print is rare and hits risk assets hard.",
    "adp nonfarm employment change": "Payroll processor ADP's own estimate of private-sector job growth, published two days before the official payrolls report.",
    "initial jobless claims": "First-time US applications for jobless benefits in the past week — the fastest read on layoffs, and lower is stronger.",
    "average hourly earnings mom": "Wage growth for the month, the inflation channel inside the employment report.",
    "employment cost index qoq": "Total compensation growth including benefits — the wage measure the Fed calls sticky.",
    "core pce price index mom": "The Fed's preferred inflation gauge: consumer prices excluding food and energy, month over month. A print at or below 0.2% keeps the easing bias alive.",
    "core pce price index yoy": "Yearly core inflation on the PCE measure, the Fed's stated policy target.",
    "pce price index mom": "Headline consumer inflation on the PCE measure, month over month.",
    "personal spending mom": "Growth in household outlays for the month — consumer demand is roughly two thirds of US GDP.",
    "personal income mom": "Growth in household income before tax, published with the PCE inflation data.",
    "inflation rate mom": "The month's change in the consumer price basket — headline inflation.",
    "inflation rate yoy": "Yearly consumer inflation against the central bank's target.",
    "inflation rate yoy flash": "The first, partial estimate of yearly inflation, revised in the final reading.",
    "core inflation rate yoy": "Yearly inflation excluding food and energy — the trend central banks react to.",
    "producer price index mom": "Change in prices paid to producers — pipeline inflation that reaches consumers later.",
    "gdp growth rate qoq": "Quarter-over-quarter economic growth; the first print is an estimate and is revised twice.",
    "gdp growth rate yoy": "Year-over-year economic growth, which smooths out the seasonal path.",
    "balance of trade": "Exports minus imports. A surplus supports the currency; a wider deficit weighs on it.",
    "s&p global manufacturing pmi": "Survey of manufacturers (Markit/S&P Global). Above 50 means output is expanding, below 50 means it is shrinking.",
    "s&p global services pmi": "The services-side PMI — the larger share of a developed economy.",
    "s&p global composite pmi": "Manufacturing and services combined into one activity index.",
    "nbs manufacturing pmi": "China's official factory survey from the National Bureau of Statistics; 50 is the growth line.",
    "nbs services pmi": "China's official non-manufacturing activity survey.",
    "caixin manufacturing pmi": "Private survey of smaller, export-leaning Chinese factories.",
    "ifo business climate": "Ifo survey of German business sentiment — the euro area's growth bellwether.",
    "tankan large manufacturers index": "Bank of Japan quarterly survey of large manufacturers' sentiment; the capex and wage signal.",
    "rba interest rate decision": "Reserve Bank of Australia policy vote — the main driver of the AUD.",
    "fed interest rate decision": "The Federal Reserve's target rate for overnight lending; the single biggest driver of the dollar.",
    "fomc minutes": "Detailed minutes of the Fed meeting. Markets mine them for hawkish or dovish clues and for the size of any dissent.",
    "fed press conference": "The Fed Chair takes questions after the decision; off-script answers can move any risk asset.",
    "empire state manufacturing index": "Regional US factory survey for New York state — the first manufacturing read each month.",
    "philly fed manufacturing index": "Regional US factory survey for the Philadelphia area.",
    "michigan consumer sentiment": "University of Michigan household survey; inflation expectations inside it are the market's real focus.",
    "eia crude oil stocks change": "Weekly US commercial crude stockpiles; a build points to softer demand and pressures crude.",
    "eia natural gas storage change": "Weekly change in US underground gas stocks — a weather-driven demand read.",
    "treasury budget statement": "Monthly US federal budget balance.",
    "manufacturing pmi": "Survey of purchasing managers in industry: above 50 means expansion, below 50 contraction.",
    "services pmi": "Survey of purchasing managers in services, the biggest slice of a developed economy.",
    "consumer confidence": "Survey of how households feel about jobs, income and spending.",
    "monetary policy meeting accounts": "The detailed account of the ECB's last policy meeting — who argued for what, and how close the vote was.",
    "monetary policy meeting minutes": "The detailed account of a central bank's last policy meeting, mined for hawkish or dovish clues.",
    "industrial profits yoy": "Profits earned by China's large industrial firms, year over year — the earliest read on the country's corporate health.",
    "richmond manufacturing index": "Regional US manufacturing diffusion index for the Richmond Fed district; zero is the growth/contraction line.",
    "treasury gilt auction": "The UK Debt Management Office selling government gilts; weak demand lifts yields and pressures the pound.",
    "bill auction": "A short-dated government bill sale. The market reads the demand and the accepted yield as a live read on where cash can be parked.",
    "note auction": "A government note sale. Coverage and the high yield are the market's own pricing of the curve at that maturity.",
    "bond auction": "A government bond sale. The bid-to-cover ratio and the accepted yield show how much real demand there is at that maturity.",
})

SPEAKER_HINT = {
    "fomc": "Federal Reserve", "ecb": "European Central Bank", "boe": "Bank of England",
    "mpc": "Bank of England's Monetary Policy Committee", "boj": "Bank of Japan",
    "rba": "Reserve Bank of Australia", "boc": "Bank of Canada", "snb": "Swiss National Bank",
    "buba": "Bundesbank", "fed": "Federal Reserve",
}


# Country codes as ForexFactory writes them (the page's own `country` field)
# — the JSON mirror uses currency codes instead, so both are mapped here.
GEO_NAME = {
    "US": "United States", "EZ": "Euro Area", "UK": "United Kingdom",
    "JN": "Japan", "CN": "China", "AU": "Australia", "CA": "Canada",
    "CH": "Switzerland", "SZ": "Switzerland", "NZ": "New Zealand",
    "GE": "Germany", "FR": "France", "IT": "Italy", "SP": "Spain",
    "BE": "Belgium", "NL": "Netherlands", "SE": "Sweden", "NO": "Norway",
    "DK": "Denmark", "IE": "Ireland", "PT": "Portugal", "AT": "Austria",
    "FI": "Finland", "PL": "Poland", "TR": "Turkey", "IN": "India",
    "BR": "Brazil", "MX": "Mexico", "ZA": "South Africa", "KR": "South Korea",
    "SG": "Singapore", "HK": "Hong Kong", "TW": "Taiwan", "RU": "Russia",
    "SA": "Saudi Arabia", "ID": "Indonesia", "MY": "Malaysia", "TH": "Thailand",
}
GEO_FLAG = {
    "US": "\U0001F1FA\U0001F1F8", "EZ": "\U0001F1EA\U0001F1FA", "UK": "\U0001F1EC\U0001F1E7",
    "JN": "\U0001F1EF\U0001F1F5", "CN": "\U0001F1E8\U0001F1F3", "AU": "\U0001F1E6\U0001F1FA",
    "CA": "\U0001F1E8\U0001F1E6", "CH": "\U0001F1E8\U0001F1ED", "SZ": "\U0001F1E8\U0001F1ED",
    "NZ": "\U0001F1F3\U0001F1FF", "GE": "\U0001F1E9\U0001F1EA", "FR": "\U0001F1EB\U0001F1F7",
    "IT": "\U0001F1EE\U0001F1F9", "SP": "\U0001F1EA\U0001F1F8", "BE": "\U0001F1E7\U0001F1EA",
    "NL": "\U0001F1F3\U0001F1F1", "SE": "\U0001F1F8\U0001F1EA", "NO": "\U0001F1F3\U0001F1F4",
    "DK": "\U0001F1E9\U0001F1F0", "IE": "\U0001F1EE\U0001F1EA", "PT": "\U0001F1F5\U0001F1F9",
    "AT": "\U0001F1E6\U0001F1F9", "FI": "\U0001F1EB\U0001F1EE", "PL": "\U0001F1F5\U0001F1F1",
    "TR": "\U0001F1F9\U0001F1F7", "IN": "\U0001F1EE\U0001F1F3", "BR": "\U0001F1E7\U0001F1F7",
    "MX": "\U0001F1F2\U0001F1FD", "ZA": "\U0001F1FF\U0001F1E6", "KR": "\U0001F1F0\U0001F1F7",
    "SG": "\U0001F1F8\U0001F1EC", "HK": "\U0001F1ED\U0001F1F0", "TW": "\U0001F1F9\U0001F1FC",
    "RU": "\U0001F1F7\U0001F1FA", "SA": "\U0001F1F8\U0001F1E6",
}
CURRENCY_NAME = {
    "USD": "the US dollar", "EUR": "the euro", "GBP": "the British pound",
    "JPY": "the Japanese yen", "CHF": "the Swiss franc", "CAD": "the Canadian dollar",
    "AUD": "the Australian dollar", "NZD": "the New Zealand dollar",
    "CNY": "the Chinese yuan", "SEK": "the Swedish krona", "NOK": "the Norwegian krone",
    "TRY": "the Turkish lira", "INR": "the Indian rupee", "BRL": "the Brazilian real",
    "MXN": "the Mexican peso", "ZAR": "the South African rand", "KRW": "the Korean won",
}

# Category → how the number is actually produced (used by the explain card).
CATEGORY_RULES = [
    ("holiday", r"holiday|bank closed|market closed|non-economic"),
    ("speech", r"\bspeaks?\b|\bspeech\b|\bremarks\b|\baddress\b|press conference|\bconference\b|\bpost-meeting\b|\bbriefing\b"),
    ("auction", r"auction|bond sale|\bsale\b.*\bbond\b"),
    ("inventory", r"inventor|storage|\bstocks\b|\bsupply\b"),
    ("rate", r"\brate\b|policy rate|cash rate|funds rate|interest rate|refinancing|discount rate|yield curve"),
    ("document", r"statement|minutes|assessment|summary|outlook|\breport\b|bulletin|decision|tankan"),
    ("survey", r"confidence|sentiment|climate|expectations|\bmood\b|\bpmi\b|ifo|zew|economic optimism|business activity"),
    ("jobs", r"employment|unemployment|payroll|\bjobs?\b|jolts|job cuts|claims|participation rate|hiring|vacancies"),
    ("inflation", r"\bcpi\b|\bppi\b|inflation|price index|import prices|export prices|sppi|\bhpi\b|deflator"),
    ("housing", r"housing|home sales|building permits|construction|mortgage"),
    ("growth", r"\bgdp\b|industrial production|manufacturing production|factory orders|durable goods|retail sales|leading index|gross domestic|business climate"),
    ("trade", r"trade balance|current account|exports|imports|borrowing|\bbudget\b|\bm3\b|money supply|loans|net lending"),
]
CADENCE_RULES = [
    ("weekly", r"inventor|storage|claims|\bapi weekly\b|money supply|\bm3\b|mortgage applications|\bweekly\b"),
    ("quarterly", r"q/q|qoq|quarterly|tankan|\bgdp\b|gross domestic|refinancing"),
    ("annual", r"y/y|yoy|annual"),
    ("daily", r"\bdaily\b"),
]
MEASURE = {
    "holiday": "Nothing is measured and no figure is published. {who} simply keeps its banks and exchanges shut, so turnover collapses, pricing gaps widen and volatility becomes unreliable.",
    "speech": "There is no questionnaire, no number and no embargo: the content is whatever the official decides to say, live. The market compares the tone with the committee's last statement and prices the odds of the next policy move accordingly.",
    "auction": "The debt office sells a pre-announced amount of government paper to primary dealers. The market reads two numbers out of it: the bid-to-cover ratio, which shows how many bids arrived per unit sold, and the high yield that was accepted. A weak auction lifts yields and can drag the currency with it.",
    "inventory": "Commercial stockpiles are counted and compared with the previous reading. A build means supply is running ahead of demand, a draw means the opposite — and it moves the front-month futures contract before it moves anything else.",
    "rate": "The members of the policy committee vote on the level of the benchmark rate, and the decision is published with a statement. The vote split, the guidance and any change to asset purchases matter as much as the rate itself.",
    "document": "A written document is released at a fixed time instead of a single figure. The market reads the language, the projections and the change in guidance, then re-prices the odds of the next move.",
    "survey": "Firms or households answer a fixed questionnaire and the answers are squeezed into a diffusion index: a reading above 50, or above zero, means the majority expects expansion, below means contraction. It measures sentiment rather than money.",
    "jobs": "Payroll and household surveys are combined, so a single release carries several numbers at once: the net change in jobs, the unemployment rate, the participation rate and wage growth. The first print is an estimate and is revised over each of the following two months.",
    "inflation": "A fixed basket of goods and services is priced, then weighted by what households actually buy. Food and energy swing the headline, which is why the core figure — with both stripped out — is the trend a central bank reacts to.",
    "housing": "The construction pipeline is measured stage by stage: permits first, then starts, then sales of new and existing homes. Permits are the earliest signal, completed sales the latest.",
    "growth": "Output is measured from both the production and the expenditure side of the economy, then deflated back into real terms. The first release is an advance estimate that gets revised twice, and a revision can move price more than the original print.",
    "trade": "Customs data for goods and services crossing the border are totalled. The balance feeds straight into GDP and into demand for the currency, because importers have to buy it while exporters sell it.",
    "other": "It is compiled by {who}'s statistical agency or central bank and released on a fixed schedule, normally with a written release that explains the methodology and any revisions to earlier periods.",
}
WHY_MATTERS = {
    "High": "High impact. A surprise against the consensus forecast re-prices {cur} within seconds, and because rates, equities, gold and crypto are all wired to the same dollar and yield complex, the reaction normally spreads across asset classes. A stronger-than-expected print lifts {cur}; a weak one pushes it down.",
    "Medium": "Medium impact. It usually moves {cur} only when the number lands clearly away from the forecast — inside the consensus range the reaction is small and fades quickly.",
    "Low": "Low impact. It rarely moves {cur} on its own. Its real use is context: the trend it describes often hints at which way the next high-impact release will lean.",
    "Holiday": "Non-economic. With {who}'s banks and exchanges closed there is no figure to trade; the only consequence is thinner liquidity, which can exaggerate moves caused somewhere else.",
}
HOW_TRADED = "Trade the surprise, not the level. The consensus forecast is already in the price, so the move comes from the gap between the actual and the forecast — and from any revision to the previous print. Positions are built before the release and liquidity often dries up in the first minute after it, so spreads widen and the first tick is unreliable. A print above forecast is normally positive for {cur}, below is negative; when the actual matches the forecast exactly, the reaction comes from the details inside the release, or fades entirely."
CADENCE_WORD = {"weekly": "once a week", "monthly": "once a month", "quarterly": "once a quarter",
                "annual": "once a year", "daily": "every business day"}


# The two calendars name their periods differently: ForexFactory writes "m/m",
# "y/y", "q/q" and TradingView writes "MoM", "YoY", "QoQ". One glossary serves
# both once the suffix is normalised.
PERIOD_ALIAS = {"mom": "m/m", "yoy": "y/y", "qoq": "q/q", "wow": "w/w"}

# Releases each calendar names differently, plus political events (summits,
# testimony, hearings) that behave exactly like a speech: no printed number,
# the market moves on the words.
CATEGORY_EXTRA = [
    ("speech", r"summit|testimony|hearing|assembly|forum|press briefing|panel discussion"),
    ("trade", r"balance of trade"),
    ("inflation", r"\bpce\b"),
    ("growth", r"personal income|personal spending"),
]


def _category(key: str) -> str:
    for cat, pat in CATEGORY_RULES:
        if re.search(pat, key):
            return cat
    for cat, pat in CATEGORY_EXTRA:
        if re.search(pat, key):
            return cat
    return "other"


def _gloss(key: str):
    """Glossary lookup across both naming styles.

    'Durable Goods Orders MoM' and 'Durable Goods Orders m/m' are the same
    release, 'Inflation Rate YoY Flash' is 'Inflation Rate y/y', and 'Richmond
    Fed Manufacturing Index' is the glossary's 'Richmond Manufacturing Index' —
    so the period suffix is normalised, reporting qualifiers and the publishing
    body are peeled off, and only then does the generator take over.
    """
    if key in EVENT_DOCS:
        return EVENT_DOCS[key]
    parts = key.split()
    flat = " ".join(PERIOD_ALIAS.get(w, w) for w in parts)
    if flat in EVENT_DOCS:
        return EVENT_DOCS[flat]
    for drop in ("flash", "prel", "prelim", "final", "adv", "advanced", "revised",
                 "provisional", "sa", "nsa", "fed", "boe", "ecb", "fomc", "rba",
                 "boj", "snb", "mpc", "buba", "nbs", "caixin"):
        trimmed = [w for w in parts if w != drop]
        if len(trimmed) == len(parts):
            continue
        for cand in (" ".join(trimmed),
                     " ".join(PERIOD_ALIAS.get(w, w) for w in trimmed)):
            if cand in EVENT_DOCS:
                return EVENT_DOCS[cand]
    return None


_doc_cache = {}


def event_doc(title: str, country: str = "", impact: str = "Low", geo: str = "", rev: str = "") -> dict:
    """A short line plus full multi-paragraph English explanation of a row.

    Twelve categories are recognised from the title itself (speeches, bond
    auctions, inventories, rate decisions, documents, surveys, jobs,
    inflation, housing, growth, trade, holidays). Curated glossary first, then
    a generated explanation, so an event nobody has seen before still explains
    itself: what it is, how the number is measured, why it matters and how the
    market trades it. Deterministic and offline — no model, no API key.
    """
    t = re.sub(r"\s+", " ", (title or "").strip())
    if not t:
        return {"short": "", "sections": []}
    cache_key = (t.lower(), country, impact, geo)
    hit = _doc_cache.get(cache_key)
    if hit:
        return hit
    key = t.lower()
    who = COUNTRY_NAME.get(country) or GEO_NAME.get(geo) or geo or "the issuing country"
    cur = CURRENCY_NAME.get(country, "the local currency")
    cat = _category(key)
    cadence = _cadence(key)

    # A Holiday is a holiday whatever the title says ("Autumnal Equinox Day"
    # carries no such word — the impact field is the only signal).
    if impact == "Holiday":
        cat = "holiday"
    one = _gloss(key)
    if not one:
        speaker = re.sub(r"\b(speech|speaks?|remarks|address|press conference|conference|"
                         r"summit|hearing|testimony|forum|assembly|briefing)\b", "", t,
                         flags=re.IGNORECASE).strip(" -–\u2013,:")
        org = next((v for k, v in SPEAKER_HINT.items() if k in key), "")
        if cat == "holiday":
            one = (f"{t} in {who}: banks and exchanges are closed — no release is published, so "
                   "liquidity thins out and volatility becomes unreliable.")
        elif cat == "speech":
            # Two very different things live in this bucket: a central banker whose
            # words hint at policy, and a political appearance where the driver is
            # fiscal or diplomatic news. They get different copy — and the check is
            # "no central bank named" first, so 'ECB President Lagarde Speaks' is a
            # central-bank speech while 'President Trump and President Xi Summit' is
            # not merely because it says president.
            political = (not org) and re.search(
                r"president|prime minister|minister|chancellor|trump|summit|"
                r"assembly|hearing|testimony|congress|parliament|secretary", key)
            if political:
                one = (f"{t}: a political event rather than a data release. There is no figure to "
                       "beat — price reacts to policy news, tariffs, fiscal plans or a line dropped live.")
            elif speaker and org:
                # 'Fed Barkin Speech' → 'Barkin': the bank is named in the same
                # sentence, so repeating the token in the name reads as a stutter.
                name = re.sub(r"\b(fed|boe|ecb|fomc|rba|boj|snb|mpc|buba|bank of england|"
                              r"federal reserve)\b", "", speaker, flags=re.IGNORECASE).strip(" -–,")
                one = (f"{name or speaker} of {org} speaks publicly. No figure is printed, so the "
                       "reaction comes from policy signals and off-script answers rather than from a number.")
            elif org:
                one = (f"{org} speaks publicly — a scheduled appearance with no data attached, so only "
                       "a policy signal moves price.")
            else:
                one = (f"{t}: a public appearance rather than a data release — nothing is printed, "
                       "so the reaction comes from what is actually said.")
        elif cat == "auction":
            one = f"{t}: {who} sells government bonds to primary dealers and the result shows up in the demand and the yield accepted."
        elif cat == "rate":
            one = f"{t}: the benchmark policy rate of {who} — the single biggest driver of {cur}."
        elif cat == "jobs":
            one = f"{t}: a labour-market reading for {who}, the data block central banks watch before deciding on rates."
        elif cat == "inflation":
            one = f"{t}: a price reading for {who} — how fast the cost of goods and services is rising."
        elif cat == "survey":
            one = f"{t}: a survey of firms or households in {who}, published as a diffusion index."
        elif cat == "inventory":
            one = f"{t}: the change in {who} commercial stockpiles, the fastest read on physical supply and demand."
        elif cat == "housing":
            one = f"{t}: a housing-market indicator for {who}, tracking the construction pipeline and transactions."
        elif cat == "growth":
            one = f"{t}: an output or demand indicator for {who}."
        elif cat == "trade":
            one = f"{t}: a cross-border flow indicator for {who}."
        elif cat == "document":
            one = f"{t}: an official publication from {who} — a document to read rather than a single number to beat."
        else:
            one = f"{t}: an official statistic published by {who}."

    tail = ""
    for suf, word in PERIOD_NOTE.items():
        if key.endswith(" " + suf):
            tail = f" This release is reported as a {word}."
            break
    cad = CADENCE_WORD.get(cadence, "once a month")
    measure = MEASURE.get(cat, MEASURE["other"]).format(who=who)
    rev_note = f" A revision of the previous reading ({rev}) is published alongside it and is part of the story." if rev else ""
    sections = [
        {"h": "What it is", "p": one},
        {"h": "How it is measured", "p": f"{measure} It is published {cad}." + tail + rev_note},
        {"h": "Why it matters", "p": WHY_MATTERS.get(impact, WHY_MATTERS["Low"]).format(cur=cur, who=who)},
        {"h": "How the market trades it", "p": HOW_TRADED.format(cur=cur)},
    ]
    doc = {"short": one, "sections": sections}
    _doc_cache[cache_key] = doc
    return doc


def _cadence(key: str) -> str:
    for name, pat in CADENCE_RULES:
        if re.search(pat, key):
            return name
    return "monthly"


# ---------------------------------------------------------------------------
# Persian explainer — two short paragraphs, no model, no API
# ---------------------------------------------------------------------------
# The English doc above is four sections and reads like a primer. The dashboard
# shows it in Persian, and a trader scanning a calendar wants two lines: what
# the release is, and what it does to the tape. Same offline, rule-based
# generation — title + impact + category are all the input it needs.
COUNTRY_FA = {
    "USD": "آمریکا", "EUR": "منطقهٔ یورو", "GBP": "بریتانیا", "JPY": "ژاپن",
    "CNY": "چین", "AUD": "استرالیا", "CAD": "کانادا", "CHF": "سوئیس",
    "NZD": "نیوزیلند", "IRR": "ایران", "TRY": "ترکیه", "INR": "هند",
    "BRL": "برزیل", "MXN": "مکزیک", "ZAR": "آفریقای جنوبی", "KRW": "کرهٔ جنوبی",
    "SEK": "سوئد", "NOK": "نروژ", "SGD": "سنگاپور", "HKD": "هنگ‌کنگ",
}
GEO_FA = {
    "US": "آمریکا", "EU": "منطقهٔ یورو", "GB": "بریتانیا", "JP": "ژاپن",
    "CN": "چین", "AU": "استرالیا", "CA": "کانادا", "CH": "سوئیس",
    "NZ": "نیوزیلند", "DE": "آلمان", "FR": "فرانسه", "IT": "ایتالیا",
    "ES": "اسپانیا", "IN": "هند", "BR": "برزیل", "TR": "ترکیه", "IR": "ایران",
}
CATEGORY_FA = {
    "rate": "تصمیم نرخ بهره", "inflation": "شاخص تورم", "jobs": "آمار اشتغال",
    "growth": "شاخص رشد", "housing": "شاخص مسکن", "survey": "نظرسنجی بخشی",
    "inventory": "موجودی انبارها", "trade": "تجارت خارجی", "auction": "حراج اوراق",
    "speech": "سخنرانی", "document": "سند رسمی", "holiday": "تعطیلی بازار",
    "other": "آمار رسمی",
}
WHAT_FA = {
    "rate": "{title} — جلسهٔ سیاست پولی {who}: نرخ بهرهٔ مرجع تعیین می‌شود و لحن بیانیه جهت بازار را تا جلسهٔ بعد می‌سازد.",
    "inflation": "{title} — سنجش گرانی مصرف‌کننده در {who}؛ عدد اصلی‌ای که بانک مرکزی به آن واکنش می‌دهد.",
    "jobs": "{title} — آمار بازار کار {who}: تعداد شغل‌های ایجادشده و فشار دستمزدها.",
    "growth": "{title} — سنجش تولید و تقاضا در {who}: آیا اقتصاد در حال شتاب گرفتن است یا سرد شدن.",
    "housing": "{title} — وضعیت ساخت‌وساز و معاملات مسکن {who}؛ زودتر از بقیه چرخهٔ نرخ را نشان می‌دهد.",
    "survey": "{title} — نظرسنجی از بنگاه‌ها یا خانوارهای {who}، به شکل یک شاخص تفاضلی (بالای ۵۰ = انبساط).",
    "inventory": "{title} — تغییر موجودی انبارهای {who}: سریع‌ترین خوانش عرضه و تقاضای فیزیکی.",
    "trade": "{title} — ورود و خروج کالا در {who}؛ تراز تجاری و اثرش بر جریان ارز.",
    "auction": "{title} — حراج اوراق {who}: تقاضا و نرخ برش، سنجهٔ اشتها به ریسک دولتی است.",
    "speech": "{title} — اظهارنظر سیاست‌گذار؛ عددی منتشر نمی‌شود و بازار روی کلمات حرکت می‌کند.",
    "document": "{title} — انتشار سند رسمی؛ خواندنی است تا اینکه یک عدد را رد کند.",
    "holiday": "{title} — {who} تعطیل است: داده‌ای منتشر نمی‌شود و نقدینگی بازار کم می‌شود.",
    "other": "{title} — یک آمار رسمی از {who}.",
}
TRADED_FA = {
    "High": "واقعاً پراثر: بهتر از پیش‌بینی معمولاً {cur} را تقویت می‌کند و به طلا و کریپتو فشار می‌آورد؛ بدتر از آن برعکس.",
    "Medium": "اثر متوسط: فقط اگر عدد از پیش‌بینی فاصلهٔ واضحی بگیرد روی {cur} و دارایی‌های ریسکی دیده می‌شود.",
    "Low": "اثر کم: بیشتر زمینه‌ساز است تا محرک؛ تا وقتی اختلاف چشمگیری نباشد بازار از آن رد می‌شود.",
    "Holiday": "با تعطیلی بازار، نقدینگی افت می‌کند و نوسان بی‌قاعده می‌شود.",
}
CADENCE_FA = {"weekly": "هفتگی", "monthly": "ماهانه", "quarterly": "فصلی",
              "annual": "سالانه", "daily": "هر روز کاری"}
_doc_fa_cache = {}


def event_doc_fa(title: str, country: str = "", impact: str = "Low", geo: str = "",
                 unit: str = "") -> list:
    """Two short Persian sections: what the release is, and how it trades."""
    t = re.sub(r"\s+", " ", (title or "").strip())
    if not t:
        return []
    key = (t.lower(), country, impact, geo, unit)
    hit = _doc_fa_cache.get(key)
    if hit is not None:
        return hit
    cur = (country or geo or "").upper()
    who = COUNTRY_FA.get(cur) or GEO_FA.get(geo) or GEO_FA.get(country) or cur or "این کشور"
    cat = "holiday" if impact == "Holiday" else _category(t.lower())
    cad = CADENCE_FA.get(_cadence(t.lower()), "ماهانه")
    what = WHAT_FA.get(cat, WHAT_FA["other"]).format(title=t, who=who, cur=cur or "ارز")
    traded = TRADED_FA.get(impact, TRADED_FA["Low"]).format(cur=cur or "ارز", who=who)
    unit_note = f" واحد گزارش: {unit}." if unit else ""
    out = [
        {"h": "این رویداد چیست", "p": what},
        {"h": "بازار چطور معامله‌اش می‌کند", "p": traded + f" دورهٔ انتشار: {cad}.{unit_note}"},
    ]
    _doc_fa_cache[key] = out
    return out


MACRO_QUOTES = [  # (sym, yahoo_symbol, fa_name, icon)
    ("DXY", "DX-Y.NYB", "دلار (DXY)", "\U0001F4B5"),
    ("SPX", "^GSPC",    "اس‌اند‌پی ۵۰۰", "\U0001F3DB"),
    ("VIX", "^VIX",     "شاخص ترس VIX", "\U0001F630"),
    ("WTI", "CL=F",     "نفت وست تگزاس", "\U0001F6E2"),
]


def _fetch(url, **kw):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, **kw)
        if r.status_code == 200:
            return r
    except Exception:
        pass
    return None


IMP_MAP = {"high": "High", "medium": "Medium", "low": "Low", "holiday": "Holiday"}

# TradingView importance: 1 = high, 0 = medium, -1 = low. Holidays arrive with
# -1 and indicator "Holidays", which is its own bucket on the dashboard.
TV_IMPACT = {1: "High", 0: "Medium", -1: "Low"}
TV_CALENDAR_URL = "https://www.tradingview.com/economic-calendar/"

# Lower is better for these — used only for the green/red tint on the released
# value, so a falling unemployment print shows green rather than red.
# Inflation is deliberately NOT in this list: a hot CPI print is hawkish and
# strengthens the currency, which is what the surrounding prose says. Listing
# it here tinted a below-forecast CPI green while the text next to it called
# the stronger number currency-positive.
LOWER_IS_BETTER = re.compile(
    r"unemployment|jobless|claims|deficit|borrowing|inventor|storage|\bdebt\b")


def _num(v):
    """TradingView prints thousands with a comma and units separately."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").replace("%", "").strip())
    except Exception:
        return None


def _fmt_num(n, unit):
    """1.5 % stays '1.5%'; 1620000 becomes '1.62M'; keep it short for a table.

    The sign is carried through every branch: a negative index reading printed
    as a positive one (Richmond Fed -2 shown as 2) makes the row, and the
    surprise computed from it, read backwards.
    """
    if n is None or n == "":
        return ""
    a = abs(n)
    if a >= 1e9:
        s = f"{n / 1e9:.2f}B"
    elif a >= 1e6:
        s = f"{n / 1e6:.2f}M"
    elif a >= 1e4:
        s = f"{n / 1e3:.0f}K"
    elif float(n) == int(n):
        s = f"{int(n)}"
    else:
        s = f"{n:g}"
    if unit == "%":
        s += "%"
    return s


def _entry(title, cur, geo, imp, ts, forecast, previous, actual, rev, impact_title,
           url, unit="", period="", indicator="", category="", all_day=False):
    """One calendar row in the shape the dashboard consumes.

    Timestamps are the only source of truth (`ts`, epoch UTC); `day`/`time_str`
    are the UTC rendering and the UI re-formats both for the timezone the
    reader picks. Numbers keep both the printed string and a parsed value, so
    the row can show the actual against the forecast and colour the surprise.
    Nothing here is Persian: the calendar is English-only.
    """
    dt = datetime.fromtimestamp(ts, timezone.utc)
    doc = event_doc(title, cur, imp, geo, rev)
    doc_fa = event_doc_fa(title, cur, imp, geo, unit)
    a_n, f_n, p_n = _num(actual), _num(forecast), _num(previous)
    surprise = round(a_n - f_n, 4) if (a_n is not None and f_n is not None) else None
    better = None
    if surprise is not None and surprise != 0:
        good = surprise < 0 if LOWER_IS_BETTER.search(title.lower()) else surprise > 0
        better = 1 if good else -1
    return {
        "title": title,
        "country": cur or geo,
        "geo": geo,
        "geo_name": GEO_NAME.get(geo, geo),
        "flag": COUNTRY_FLAG.get(cur) or GEO_FLAG.get(geo, "\U0001F30D"),
        "impact": imp,
        "impact_title": (impact_title or "").strip(),
        "impact_fa": IMPACT_FA.get(imp, imp),
        "indicator": (indicator or "").strip(),
        "category": (category or "").strip(),
        "period": (period or "").strip(),
        "unit": (unit or "").strip(),
        "all_day": bool(all_day),
        "forecast": (forecast or "").strip() or "—",
        "forecast_n": f_n,
        "forecast_fmt": _fmt_num(f_n, (unit or "").strip()) or ((forecast or "").strip() or "—"),
        "previous": (previous or "").strip() or "—",
        "previous_n": p_n,
        "previous_fmt": _fmt_num(p_n, (unit or "").strip()) or ((previous or "").strip() or "—"),
        "revision": (rev or "").strip(),
        "actual": (actual or "").strip(),
        "actual_n": a_n,
        "actual_fmt": _fmt_num(a_n, (unit or "").strip()) or (actual or "").strip(),
        "surprise": surprise,
        "surprise_fmt": (("+" if surprise > 0 else "") + _fmt_num(surprise, (unit or "").strip())
                         ) if surprise is not None else "",
        "better": better,
        "ts": ts,
        "iso": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "day": dt.strftime("%Y-%m-%d"),
        "time_str": dt.strftime("%H:%M"),
        "past": dt < datetime.now(timezone.utc),
        # "released" means a number is out, nothing else. It used to be
        # `has a number OR the slot is in the past`, so every speech, holiday
        # and bond auction that simply has no figure was announced as
        # "منتشر شد" the moment its time passed.
        "released": bool((actual or "").strip()),
        "url": url or TV_CALENDAR_URL,
        "doc": doc["short"],
        "doc_sections": doc["sections"],
        "doc_fa": (doc_fa[0]["p"] if doc_fa else ""),
        "doc_fa_sections": doc_fa,
    }


# The majors a dollar-centric desk actually watches (same coverage the old
# ForexFactory feed had). TradingView returns every country by default; without
# this filter the week is 400+ rows of mostly irrelevant releases.
TV_COUNTRIES = "US,EU,GB,JP,CN,CA,AU,NZ,CH,DE,FR,IT,ES"
TV_EPOCH = "%Y-%m-%dT%H:%M:%S.000Z"


def _str_num(v):
    """TradingView hands back numbers (or null); _entry re-parses and formats."""
    if v is None or v == "":
        return ""
    return str(v)


def _tv_events(start: datetime, end: datetime):
    """TradingView's economic calendar for one date range.

    Every row carries an exact UTC `date`, the printed actual / forecast /
    previous (plus parsed numbers and a unit) and a 1/0/-1 importance, so
    nothing has to be inferred from a scraped table. This replaced the
    ForexFactory page scrape, where the wall-clock times sat in the page's own
    timezone and every next-week row landed at the wrong hour — and whose page
    now answers a plain request with a Cloudflare 403 anyway.
    """
    if not start or not end:
        return None
    url = ("https://economic-calendar.tradingview.com/events?from=" + start.strftime(TV_EPOCH) +
           "&to=" + end.strftime(TV_EPOCH) + "&countries=" + TV_COUNTRIES)
    try:
        r = requests.get(url, headers={**HEADERS, "Accept": "application/json",
                                       "Origin": "https://www.tradingview.com",
                                       "Referer": "https://www.tradingview.com/"}, timeout=25)
        if r.status_code != 200:
            return None
        return (r.json() or {}).get("result")
    except Exception:
        return None


def _calendar_week(week_offset: int = 0):
    """One Monday-to-Sunday week (UTC), offset 0 = the current week."""
    now = datetime.now(timezone.utc)
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    start = monday + timedelta(days=7 * week_offset)
    end = start + timedelta(days=7)
    rows = _tv_events(start, end)
    rng = {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d")}
    if rows is None:
        return {"error": "unavailable", "range": rng}
    out, seen = [], set()
    for it in rows:
        try:
            dt = datetime.strptime(it["date"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        ts = int(dt.timestamp())
        title = (it.get("title") or "").strip()
        if not title:
            continue
        cur = (it.get("currency") or "").strip()
        geo = (it.get("country") or "").strip()
        ind = (it.get("indicator") or "").strip()
        key = (ts, title, cur)
        if key in seen:
            continue
        seen.add(key)
        holiday = ind.lower() in ("holidays", "holiday")
        imp = "Holiday" if holiday else TV_IMPACT.get(it.get("importance"), "Low")
        unit = (it.get("unit") or "").strip()
        out.append(_entry(title, cur, geo, imp, ts,
                          _str_num(it.get("forecastRaw")) or _str_num(it.get("forecast")),
                          _str_num(it.get("previousRaw")) or _str_num(it.get("previous")),
                          _str_num(it.get("actualRaw")) or _str_num(it.get("actual")),
                          "", "", "",
                          unit=unit, period=it.get("period") or "", indicator=ind,
                          category=it.get("category") or "", all_day=holiday))
    out.sort(key=lambda x: x["ts"])
    return {"events": out, "source": "TradingView Economic Calendar",
            "range": rng, "week": week_offset}


def _calendar_json_mirror():
    """Fallback when the page cannot be parsed: the faireconomy weekly JSON
    (this week only — there is no nextweek file — and without revisions)."""
    r = _fetch("https://nfs.faireconomy.media/ff_calendar_thisweek.json")
    if not r:
        return []
    try:
        items = r.json()
    except Exception:
        return []
    out = []
    for it in items:
        try:
            naive = datetime.fromisoformat(it["date"])
            dt = naive.replace(tzinfo=timezone.utc) if naive.tzinfo is None else naive.astimezone(timezone.utc)
        except Exception:
            continue
        cur = it.get("country", "")
        out.append(_entry(it.get("title", ""), cur, cur, it.get("impact", "Low"),
                          int(dt.timestamp()), it.get("forecast"), it.get("previous"),
                          it.get("actual"), "", "", ""))
    out.sort(key=lambda x: x["ts"])
    return out


def _calendar(week_offset: int = 0):
    got = _calendar_week(week_offset)
    if "error" not in got:
        return got
    if week_offset == 0:                       # last resort: the JSON mirror (this week only)
        ev = _calendar_json_mirror()
        if ev:
            return {"events": ev, "source": "faireconomy.media (json mirror)"}
    return got


def _fng():
    r = _fetch("https://api.alternative.me/fng/?limit=8")
    if not r:
        return {"error": "unavailable"}
    try:
        d = r.json()["data"]
        return {"now": int(d[0]["value"]),
                "label": d[0]["value_classification"],
                "label_fa": FNG_FA.get(d[0]["value_classification"], ""),
                "history": [{"v": int(x["value"]), "ts": int(x["timestamp"])}
                            for x in reversed(d)]}
    except Exception:
        return {"error": "bad_json"}


# NOTE: the spot-BTC ETF net-flow table (Farside) used to be scraped here.
# It was removed with the ETF-flow panel — the ETF tab is a live rate board
# now, so the scrape, its parser and the report citation are all gone.


def _macro_quotes():
    out = []
    for sym, yh, fa, icon in MACRO_QUOTES:
        r = _fetch("https://query1.finance.yahoo.com/v8/finance/chart/" + yh,
                   params={"range": "2d", "interval": "1d"})
        price = chg = None
        if r:
            try:
                meta = r.json()["chart"]["result"][0]["meta"]
                price = meta.get("regularMarketPrice")
                chg = meta.get("regularMarketChangePercent")
            except Exception:
                pass
        out.append({"sym": sym, "fa": fa, "icon": icon, "price": price,
                    "change": round(chg, 2) if chg is not None else None})
    return out


def market_context(force: bool = False):
    """Cached bundle for /api/econ — this week + next week calendars.

    `force=False` (the default) serves the cache. The server's release scanner
    reads it that way on purpose: a background job that wakes up every minute
    must never turn a cache into a poll of the calendar page.
    """
    now = time.time()
    if not force and CACHE["data"] is not None and now - CACHE["ts"] < TTL:
        return CACHE["data"]
    data = {
        "calendar": _calendar(),
        "calendar_next": _calendar(week_offset=1),
        "fng": _fng(),
        "macro": _macro_quotes(),
        "sessions": market_sessions(),
        "fng_fa": FNG_FA,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    CACHE["ts"] = time.time()
    CACHE["data"] = data
    return data


if __name__ == "__main__":
    d = market_context()
    cal = d.get("calendar", {})
    ev = cal.get("events", [])
    print("calendar:", ("ERR " + str(cal.get("error"))) if "error" in cal else f"{len(ev)} events")
    for e in [x for x in ev if not x["past"] and x["impact"] == "High"][:3]:
        print("  ", e["flag"], e["title"], "|", e["impact_fa"])
    print("fng:", d["fng"])
    print("macro:", [(m["sym"], m["price"], m["change"]) for m in d["macro"]])
