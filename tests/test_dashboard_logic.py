"""/Unit tests for the dashboard's pure client-side logic.

Everything in `dashboard_html.py` that is a *decision* — the narrative lexicon
that clusters the feed, the calendar reaction model — runs in the browser, where
`pytest` cannot see it. `check_dashboard_js.py` only proves the blocks parse.

This module pulls the individual `const`/`function` units out of the page and
runs them under node against hand-built inputs, so a change that loosens the
clustering gate or flips a reaction sign fails here instead of silently changing
what the dashboard shows.
"""
import re
import shutil
import subprocess

import pytest


def _page():
    """The page as served — assembled from web/fragments/.

    It used to be a raw string inside dashboard_html.py, which is a thin loader
    now, so the text has to come from the module rather than off the file.
    """
    from dashboard_html import APP_HTML
    return APP_HTML


def extract(page, name):
    """Return the source of one top-level `const name = …` / `function name(…)`.

    Scans with a quote-aware brace/bracket counter, so `{0,24}` inside a regex
    literal or a brace inside a string cannot end the unit early.
    """
    m = re.search(r"^(?:const|let|var)\s+%s\s*=" % re.escape(name), page, re.M)
    if m:
        start, is_function = m.start(), False
    else:
        m = re.search(r"^function\s+%s\s*\(" % re.escape(name), page, re.M)
        if not m:
            raise AssertionError(f"{name} not found in dashboard_html.py")
        start, is_function = m.start(), True

    def skip_quoted(j):
        quote = page[j]
        j += 1
        while j < len(page) and page[j] != quote:
            j += 2 if page[j] == "\\" else 1
        return j

    def skip_regex(j):
        """`/…/flags`, honouring character classes and escapes.

        Needed because a unit may open with a regex literal: `/[\\u0000-\\u001f]/`
        contains a `[` and a `]`, which a bracket counter reads as a complete
        bracket pair and ends the unit in the middle of the pattern.
        """
        j += 1
        in_class = False
        while j < len(page):
            ch = page[j]
            if ch == "\\":
                j += 2
                continue
            if ch in "\r\n":
                return j                  # not a regex after all; bail out
            if ch == "[":
                in_class = True
            elif ch == "]":
                in_class = False
            elif ch == "/" and not in_class:
                j += 1
                while j < len(page) and page[j].isalpha():
                    j += 1
                # the scanner adds one to whatever a skipper returns, so hand
                # back the last character consumed (the flags), not the one
                # after it — otherwise the character following a regex is
                # swallowed, and when that character is a `]` the unit never
                # closes
                return j - 1
            j += 1
        return j

    def regex_start(j):
        """A `/` after a value is division; after an operator it opens a regex."""
        k = j - 1
        while k >= 0 and page[k] in " \t":
            k -= 1
        if k < 0:
            return True
        return not (page[k].isalnum() or page[k] in "_$)]")

    def skip_comment(j):
        """`// …` and `/* … */`, including a brace inside the prose."""
        if page[j + 1:j + 2] == "/":
            end = page.find("\n", j)
            return len(page) if end < 0 else end
        end = page.find("*/", j + 2)
        return len(page) if end < 0 else end + 1

    def advance(j):
        """Step over whatever starts at j — string, regex or comment — or -1."""
        ch = page[j]
        if ch in "\"'`":
            return skip_quoted(j)
        if ch == "/":
            if page[j + 1:j + 2] in ("/", "*"):
                return skip_comment(j)
            if regex_start(j):
                return skip_regex(j)
        return -1

    i = m.end()
    if not is_function:
        # a const: end at the first `;` that sits outside any bracket, or when
        # the outermost `[…]` / `{…}` closes (a `;` is appended either way)
        depth = 0
        while i < len(page):
            ch = page[i]
            nxt = advance(i)
            if nxt >= 0:
                i = nxt
            elif ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
                if depth == 0:
                    return page[start:i + 1] + ";"
            elif ch == ";" and depth == 0:
                return page[start:i + 1]
            i += 1
        raise AssertionError(f"unterminated {name}")

    depth = 1
    while i < len(page):
        ch = page[i]
        nxt = advance(i)
        if nxt >= 0:
            i = nxt
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                # the parameter list closed: the body runs to its matching brace
                j = page.index("{", i)
                d = 1
                while j + 1 < len(page) and d:
                    j += 1
                    if page[j] == "{":
                        d += 1
                    elif page[j] == "}":
                        d -= 1
                return page[start:j + 1]
        i += 1
    raise AssertionError(f"unterminated {name}")


UNITS = [
    # calendar reaction model
    "CAL_REACT_RULES", "CAL_REACT_ROWS", "CAL_REACT_FRONT", "CAL_REACT_KIND",
    "calReactRule", "calReactHash", "calReactLiveRow", "calReactModelRows",
    "calReactRows", "calReactMove", "calReactFmt", "calReactSvg",
    "calReactStats", "calReactTable", "calReactInner", "calReactHTML",
    # smart alert rules
    "AR_KEY", "AR_LOG_MAX", "AR", "AR_OPS", "AR_OP_SYM", "AR_KINDS",
    "AR_IMPACTS", "AR_TPL_DEFAULT", "arOp", "arFmtVal", "arCondText",
    "arCondOk", "arRuleEval", "arValidate", "arLoad", "arStore", "arBuildCtx",
    "arRenderTpl", "arDispatch", "arEvaluate", "arTick", "arPush", "arAskNotify",
    "ic", "arHint", "arNotify", "arDismiss", "arSquawk", "arNewId",
    "arRenderList", "arRenderLog", "arSummary", "arBlankCond", "arFields",
    "arRenderConds", "arReadConds",
    # markup safety: the three escaping jobs, kept apart
    "SAN_CTRL", "SAN_NAMED", "sanDecode", "esc", "attr", "jsLit", "jsArg",
    "SAN_URL_ATTR", "SAN_TAG_ALLOW", "SAN_ATTR_ALLOW", "SAN_ATTR_DROP",
    "sanAllowedTag", "sanAllowedAttr", "safeUrl", "Sanitizer",
    # the single clock
    "clockFactory", "clockTick",
    # windowed-grid layout math
    "vsCols", "vsLayout", "vsWindow", "vsMedian",
    # اخبار منتخب carousel: which twenty, and which four of them are on screen
    "LEAD_POOL", "LEAD", "LEAD_REDUCE", "leadTs", "leadScore", "leadPick",
    "leadPages", "leadWindow", "leadHeadHTML", "leadCardHTML",
]

STUBS = """
function toFa(n){ return String(n==null?'':n).replace(/\\d/g,d=>'۰۱۲۳۴۵۶۷۸۹'[d]); }
function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
  .replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function faAssetName(s){ return {BTC:'بیت‌کوین',ETH:'اتریوم',XAU:'طلا',XAG:'نقره',
  WTI:'نفت WTI',DXY:'دلار DXY',SPX:'S&P 500',VIX:'شاخص ترس'}[s] || s; }
function tzDayFa(ts){ return new Date(ts*1000).toISOString().slice(0,10); }
function tzClock(ts){ return new Date(ts*1000).toISOString().slice(11,16); }
function calTz(){ return 'UTC'; }
function orderedAssets(){ return ['BTC','ETH','XAU','WTI','DXY']; }
/* the lead carousel renders through the same icon and label tables as the feed */
function assetIc(){ return ''; }
function topicIc(){ return ''; }
const FA_ASSET = {BTC:'بیت‌کوین', ETH:'اتریوم', XAU:'طلا', WTI:'نفت WTI'};
const FA_TOPIC = {macro:'اقتصاد', crypto:'کریپتو', energy:'انرژی'};
globalThis.window = {};
globalThis.ECON = {calendar:{events:[]}};
/* the clock and the merged 1 s tick read these; the page declares them, the
   harness only needs them to exist */
let UI = {view:'feed'}; let DATA = null;
/* the pump is never allowed to actually schedule anything here: every timing
   assertion steps the clock by hand through frameNow() */
globalThis.requestAnimationFrame = function(){ return 1; };
globalThis.cancelAnimationFrame = function(){};
/* the alert runner dispatches through the DOM (toast stack, rule list, log);
   stubs that answer "nothing here" are enough to observe what it decided */
globalThis.document = {
  getElementById(){ return null; },
  querySelectorAll(){ return []; },
  querySelector(){ return null; },
  createElement(){ return {classList:{add(){},toggle(){}}, setAttribute(){},
    querySelector(){ return {onclick:null}; }, style:{}, appendChild(){}}; },
  addEventListener(){}, removeEventListener(){}
};
let LS = {};
globalThis.localStorage = {
  getItem(k){ return k in LS ? LS[k] : null; },
  setItem(k,v){ LS[k]=String(v); }, removeItem(k){ delete LS[k]; }
};
let FAILED = 0;
function ok(cond, what){ if(!cond){ FAILED++; console.log('  [FAIL] '+what); }
  else console.log('  [ok]   '+what); }
"""

ASSERTS = r"""
const NOW = Math.floor(Date.UTC(2026, 8, 28, 12) / 1000);
const H = 3600;
let seq = 0;
function art(o){
  seq += 1;
  return Object.assign({id:'a'+seq, title:'', title_fa:'', summary:'', summary_fa:'',
    assets:[], credibility:0.7, published_ts:NOW-2*H}, o);
}


/* ── calendar reaction model ──────────────────────────────────────────── */
const cpi = {title:'US CPI YoY', indicator:'Inflation Rate', category:'inflation',
  geo:'US', unit:'%', forecast_n:0.3, ts:NOW, past:false};
const rCpi = calReactRule(cpi);
ok(rCpi && rCpi.id==='cpi', 'US CPI resolves to the cpi rule');
ok(!calReactRule({title:'ECB President Lagarde Speech', geo:'EU'}),
   'a central-bank speech is not a rate decision');
ok(calReactRule({title:'ECB Interest Rate Decision', geo:'EU'}).id==='ecb',
   'the ECB rate decision is matched');
ok(calReactRule({title:'German Factory Orders', geo:'DE'})===null,
   'an uncovered indicator returns no rule');
ok(calReactRule({title:'US CPI YoY', geo:'UK'})===null,
   'a US indicator map is not applied to another country');

const rows = calReactRows(rCpi, cpi);
ok(rows.length===CAL_REACT_ROWS, 'exactly four releases are kept');
ok(rows.every(r=>r.react && r.react.DXY && r.react.XAU && r.react.BTC),
   'every row carries a reaction for each correlated asset');
ok(rows.every(r=>r.ts < cpi.ts), 'reference rows all sit before the event date');
const hot = rows.filter(r=>r.kind==='pos')[0];
ok(!!hot, 'the sample contains an above-forecast print');
ok(hot.react.DXY.h1 > 0 && hot.react.XAU.h1 < 0 && hot.react.BTC.h1 < 0,
   'a hot CPI lifts the dollar and pressures gold and crypto');
ok(Math.abs(hot.react.XAU.m15) < Math.abs(hot.react.XAU.h1),
   'the 15-minute leg is smaller than the 60-minute leg');
const flat = rows.filter(r=>r.kind==='flat')[0];
ok(flat && flat.react.XAU.h1 === 0, 'an in-line print produces no directional move');
ok(hot.surp > 0 && rows.filter(r=>r.kind==='neg')[0].surp < 0,
   'the surprise sign follows the kind');
ok(rows.some(r=>r.src==='model'), 'uncovered releases fall back to the reference rows');
ok(calReactRows(rCpi, cpi).map(r=>r.ts).join()===
   rows.map(r=>r.ts).join(), 'the reference sample is stable across calls');

const live = calReactLiveRow({ts:NOW-86400, actual_n:0.5, forecast_n:0.3,
  surprise:0.2, unit:'%', title:'US CPI YoY'}, rCpi);
ok(live.src==='live' && live.actual===0.5 && live.kind==='pos',
   'a release the feed has numbers for is marked live');
ok(calReactFmt(220000, 0, '')==='۲۲۰K', 'large counts print compacted');
ok(calReactFmt(0.34, 2, '%')==='۰.۳۴%', 'percentages keep their decimals');
ok(calReactMove(-0.42).indexOf('−')===0, 'a falling move carries a real minus sign');

/* the SVG generator: one path per release, coloured by the 60-minute sign */
const svg = calReactSvg(rows, 'XAU', 520, 150);
ok((svg.match(/class="cr-path/g)||[]).length===CAL_REACT_ROWS,
   'the chart draws one path per release');
ok(svg.indexOf('cr-path is-pos')>=0 && svg.indexOf('cr-path is-neg')>=0,
   'up and down paths get different classes');
ok(svg.indexOf('cr-zero')>=0 && svg.indexOf('role="img"')>=0,
   'the baseline and the img role are present');
const st = calReactStats(rCpi, rows, 'XAU');
ok(st.rule_txt.indexOf('پایین')>=0, 'the rule sentence names the expected direction for gold');
ok(st.pos + st.neg + st.flat === rows.length, 'the sample split adds up');
ok(typeof st.avg60==='number' && st.avg60 < 0, 'gold averages a decline after a hot CPI');
const html = calReactHTML(cpi);
ok(html.indexOf('<details')>=0 && html.indexOf('cr-badge')>=0,
   'the block is collapsible and carries the reference badge');
ok(calReactHTML({title:'German Factory Orders', geo:'DE'}).indexOf('is-none')>=0,
   'uncovered events render the explicit no-reference note');
window.__calReact = {rule:rCpi, e:cpi, sym:'XAU'};
const inner = calReactInner(rCpi, rows);
ok(inner.indexOf('aria-pressed="true"')>=0,
   'the selected asset chip is exposed as pressed');
ok(inner.indexOf('data-react-asset="XAU"')>=0 && inner.indexOf('data-react-asset="DXY"')>=0,
   'every correlated asset gets a chip');

/* ── smart alert rule engine ─────────────────────────────────────────── */
ok(typeof arTick==='function', 'the alert tick exists');
ok(arOp(101, 'gt', 100) && !arOp(99, 'gt', 100), 'the > operator compares numbers');
ok(arOp(-3.5, 'lt', -3) && arOp(100, 'lte', 100), 'negative thresholds work');
ok(!arOp(null, 'gt', 1) && !arOp('x', 'gt', 1), 'a missing or non-numeric reading never matches');
ok(arOp('Emergency at the Strait of Hormuz', 'contains', 'hormuz'), 'contains is case-insensitive');
ok(arOp(100.0000001, 'eq', 100), 'equality tolerates float noise');

const priceCtx = {now:NOW, prices:{BTC:{price:82630, change_24h:-2.72}, WTI:{price:101.4, change_24h:4.1}},
  events:[{ts:NOW-3600, past:true, title:'US CPI YoY', actual_n:0.4, actual_fmt:'0.4%', impact:'High'}],
  news:[{id:'n1', title:'Tankers reroute as Hormuz risk rises', title_fa:'', summary:'Emergency',
         credibility:0.9, assets:['WTI'], published_ts:NOW-600},
        {id:'n2', title:'Rumour blog post', title_fa:'', summary:'', credibility:0.2,
         assets:['BTC'], published_ts:NOW-60}]};
ok(arCondOk({kind:'price', sym:'WTI', op:'gt', value:'100'}, priceCtx).sym==='WTI',
   'a price threshold matches on the live quote');
ok(arCondOk({kind:'change', sym:'BTC', op:'lt', value:'-3'}, priceCtx)===false,
   'a 24h change threshold stays false when the move is smaller');
ok(arCondOk({kind:'price', sym:'XAU', op:'gt', value:'1'}, priceCtx)===null,
   'a symbol with no quote reports "no data" rather than a match');
ok(arCondOk({kind:'event', impact:'High'}, priceCtx)!==false, 'a released high-impact event matches');
ok(arCondOk({kind:'event', impact:'Medium'}, priceCtx)===false, 'the impact filter is honoured');
ok(arCondOk({kind:'news', terms:['hormuz','emergency'], minCred:0.85, within:240}, priceCtx).art.id==='n1',
   'a news sentinel needs the keyword AND the credibility floor');
ok(arCondOk({kind:'news', terms:['hormuz'], minCred:0.95, within:240}, priceCtx)==null
   || arCondOk({kind:'news', terms:['hormuz'], minCred:0.95, within:240}, priceCtx)===false,
   'a credible-but-cheap match cannot pass a stricter floor');
ok(arCondOk({kind:'news', terms:['hormuz'], minCred:0.5, within:1}, priceCtx)===false,
   'the news window excludes older headlines');

const andRule={name:'x', logic:'and', when:[{kind:'price', sym:'WTI', op:'gt', value:'100'},
  {kind:'news', terms:['hormuz'], minCred:0.85, within:240}]};
ok(arRuleEval(andRule, priceCtx).ok===true, 'AND requires every condition');
const orRule={name:'x', logic:'or', when:[{kind:'price', sym:'WTI', op:'gt', value:'999'},
  {kind:'news', terms:['hormuz'], minCred:0.85, within:240}]};
ok(arRuleEval(orRule, priceCtx).ok===true && arRuleEval(orRule, priceCtx).hits.length===1,
   'OR needs one condition and reports only the ones that matched');
ok(arRuleEval({logic:'and', when:[]}, priceCtx).ok===false, 'an empty rule never fires');
ok(arRuleEval({logic:'and', when:[{kind:'bogus'}]}, priceCtx).ok===false,
   'an unknown condition kind is ignored');

ok(arValidate({name:'', when:[]})!=='', 'a nameless rule is rejected');
ok(arValidate({name:'r', when:[{kind:'price', sym:'', op:'gt', value:'1'}]})!=='',
   'a price condition without a symbol is rejected');
ok(arValidate({name:'r', when:[{kind:'news', terms:[], minCred:0}], actions:{toast:true}})!=='',
   'a news condition without keywords or a credibility floor is rejected');
ok(arValidate({name:'r', when:[{kind:'event', impact:'High'}], actions:{}}) !== '',
   'a rule with no action is rejected');
ok(arValidate({name:'r', when:[{kind:'event', impact:'High'}], actions:{push:true}})==='',
   'browser push counts as an action on its own');
ok(arPush('x','y')===false && arAskNotify()===undefined,
   'push degrades quietly when the Notification API is absent');
AR.log=[];
arDispatch({name:'p', actions:{push:true}},
  {hits:[{label:'قیمت WTI', sym:'WTI', value:1, unit:'price'}]});
ok(AR.log.length===1,
   'a push-only rule whose push was refused still lands in the execution log');
ok(arValidate({name:'r', when:[{kind:'event', impact:'High'}], actions:{toast:true}})==='',
   'a complete rule validates');
ok(arCondText({kind:'price', sym:'WTI', op:'gt', value:'100'}).indexOf('WTI')>=0 &&
   arCondText({kind:'price', sym:'WTI', op:'gt', value:'100'}).indexOf('>')>=0,
   'a condition renders as a readable Persian line');
ok(arFmtVal({value:-2.72, unit:'change', label:''}).indexOf('٪')>=0, 'a change formats as a percentage');
const tpl=arRenderTpl({name:'Oil <alert>', template:'{name}|{body}|{sym}|{value}'},
  {hits:[{label:'قیمت WTI', sym:'WTI', value:101.4, unit:'price'}]});
ok(tpl.indexOf('&lt;')>=0, 'the telegram template escapes HTML');
ok(tpl.indexOf('WTI')>=0 && tpl.indexOf('|')>=0, 'template placeholders are substituted');

/* the runner: dedupe per headline, cooldown for price rules, enable switch */
LS={};
AR.rules=[{id:'r1', name:'نفت داغ', logic:'and', enabled:true, cooldown:30,
  when:[{kind:'price', sym:'WTI', op:'gt', value:'100'}], actions:{toast:true}, template:'{name}'}];
AR.rt={}; AR.log=[];
ok(arEvaluate(priceCtx).length===1, 'a matching price rule fires once');
ok(arEvaluate(priceCtx).length===0, 'the same reading does not fire again inside the cooldown');
ok(AR.log.length===1, 'the execution log records the firing');
AR.rules[0].enabled=false;
ok(arEvaluate(priceCtx).length===0, 'a disabled rule never fires');
AR.rules[0].enabled=true;
const coolKeep=AR.rules[0].cooldown;
AR.rules[0].cooldown=0;
AR.rt.r1={sig:'p:WTI|101.4000', at:Date.now()-5*60000};
ok(arEvaluate(priceCtx).length===1, 'a price rule fires again once the cooldown has passed');
AR.rules[0].cooldown=coolKeep;

AR.rules=[{id:'r2', name:'هرمز', logic:'and', enabled:true, cooldown:0,
  when:[{kind:'news', terms:['hormuz'], minCred:0.85, within:240}], actions:{toast:true}}];
AR.rt={};
ok(arEvaluate(priceCtx).length===1, 'a news rule fires on a fresh headline');
ok(arEvaluate(priceCtx).length===0, 'the same headline never fires the same rule twice');
ok(arStore()===undefined && LS[AR_KEY].indexOf('r2')>0, 'rules persist to localStorage');
AR.rules=[]; AR.log=[]; AR.rt={};
ok(arLoad()===undefined, 'loading from an empty store is safe');

/* the builder must render every field shape without throwing — esc() is the
   page's `.replace()`-based escaper, so a bare number reaching it used to blow
   up the whole condition row */
ok(arFields({kind:'price', sym:'WTI', op:'gt', value:100}).indexOf('ar-val')>=0,
   'a numeric price threshold renders (no esc() on a raw number)');
ok(arFields({kind:'change', sym:'BTC', op:'lt', value:-3}).indexOf('درصد')>=0,
   'a change condition renders its percent unit');
ok(arFields({kind:'event', impact:'High'}).indexOf('ar-impact')>=0,
   'an event condition renders the impact selector');
const newsFields=arFields({kind:'news', terms:['Hormuz'], minCred:0.5, within:2880});
ok(newsFields.indexOf('ar-terms')>=0 && newsFields.indexOf('Hormuz')>=0 &&
   newsFields.indexOf('value="50"')>=0, 'a news condition renders terms, floor and window');
ok(arFields({kind:'news'}).indexOf('ar-terms')>=0,
   'a news condition with no defaults still renders');
ok(arCondText({kind:'news', terms:['Hormuz'], minCred:0.85, within:240}).indexOf('هرمز')>=0 ||
   arCondText({kind:'news', terms:['Hormuz'], minCred:0.85, within:240}).indexOf('Hormuz')>=0,
   'the news condition line names its keywords');
ok(arBlankCond().kind==='price' && !!arBlankCond().sym, 'a blank condition starts on a real asset');

const ctxBuilt=arBuildCtx();
ok(ctxBuilt && typeof ctxBuilt.prices==='object' && Array.isArray(ctxBuilt.events),
   'the snapshot builder returns prices, events and news');

/* ── markup safety ─────────────────────────────────────────────────────────
   The escape used to double as a JS-string escaper, which is the bug that
   matters: a value of `a\'` closed the string it was spliced into. These are
   the cases that decide whether an upstream feed can reach a handler. */
ok(esc('<img src=x onerror=alert(1)>').indexOf('<')<0, 'esc neutralises a tag');
ok(esc('a"b').indexOf('&quot;')>=0, 'esc neutralises a double quote');
ok(esc("a'b").indexOf("&#39;")>=0, 'esc neutralises a single quote');
ok(esc('a\u0000b')==='ab', 'esc drops control characters');
ok(attr('&')==='&amp;', 'attr() is the same promise, named for its position');

/* the round trip is the proof: what jsArg() emits, inside a double-quoted HTML
   attribute, has to decode to the original string — no quote in it can end the
   attribute, and no backslash in it can end the JS literal */
function attrDecode(s){ return String(s).replace(/&quot;/g,'"').replace(/&amp;/g,'&')
  .replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&#39;/g,"'"); }
const traps=["a'b", 'a"b', 'a\\\'b', 'a\\"b', 'x\'-alert(1)-\'x', '\\', 'a\nb',
  'img\" onerror=alert(1) x=\"', '</script><script>alert(1)</script>'];
let jsOk=true;
for(const t of traps){
  const arg=jsArg(t);
  /* what must not survive: a raw double quote (it would end the attribute) or
     a raw < (it could end the script block). A single quote is harmless here
     — the attribute is delimited by double quotes — so it is allowed. */
  if(arg.indexOf('"')>=0||arg.indexOf('<')>=0){ jsOk=false; }
  let back=null;
  try{ back=JSON.parse(attrDecode(arg)); }catch(e){ jsOk=false; }
  if(back!==t) jsOk=false;
}
ok(jsOk, 'jsArg round-trips every quote/backslash trap and emits no raw quote');
ok(jsArg('</script>').indexOf('<')<0, 'jsArg cannot terminate the script block');
ok(jsLit('a</script>')==='"a\\u003c/script>"', 'jsLit escapes < as a unicode escape');

ok(safeUrl('https://a.example/b?c=1')==='https://a.example/b?c=1', 'https passes');
ok(safeUrl('/api/article/1')==='/api/article/1', 'a relative URL passes');
ok(safeUrl('#frag')==='#frag' && safeUrl('?q=1')==='?q=1', 'fragment and query pass');
ok(safeUrl('javascript:alert(1)')==='', 'javascript: is refused');
ok(safeUrl('JaVaScRiPt:alert(1)')==='', 'the scheme test is case-insensitive');
ok(safeUrl('java\tscript:alert(1)')==='', 'a tab inside the scheme is refused');
ok(safeUrl('\u0001javascript:alert(1)')==='', 'a control character before the scheme is refused');
ok(safeUrl('&#106;avascript:alert(1)')==='', 'an entity-encoded scheme is refused');
ok(safeUrl('data:text/html,<script>alert(1)</script>')==='', 'data:text/html is refused');
ok(safeUrl('data:image/svg+xml;base64,PHN2Zz4=')==='', 'inline SVG is refused too');
ok(safeUrl('data:image/png;base64,iVBORw0KGgo=').length>0, 'a real inline bitmap image passes');
ok(safeUrl('vbscript:msgbox(1)')==='' && safeUrl('blob:http://x/1')==='', 'other schemes fall to the default deny');
ok(safeUrl('')==='' && safeUrl(null)==='', 'an empty URL produces nothing');

ok(!sanAllowedAttr('onclick') && !sanAllowedAttr('ONERROR'), 'inline handlers are never allowed');
ok(!sanAllowedAttr('style'), 'style attributes are not allowed (they exfiltrate)');
ok(sanAllowedAttr('data-id') && sanAllowedAttr('href'), 'data-* and href are allowed');
ok(!sanAllowedTag('script') && !sanAllowedTag('iframe'), 'script and iframe are not allowed tags');
ok(sanAllowedTag('b') && sanAllowedTag('a'), 'ordinary formatting tags are allowed');
/* node has no DOMParser, so the documented fallback is what runs here: the
   string is escaped rather than parsed, and the counter records that */
const san1=Sanitizer.sanitize('<b>hi</b><script>alert(1)</script>');
ok(san1.indexOf('<script')<0, 'without a DOM the sanitizer falls back to escaping');
ok(Sanitizer.stats.noParser>=1, 'the fallback is counted, not silent');
ok(Sanitizer.text('<p>a  <b>b</b> c</p>')==='a b c', 'text() keeps the words and drops the markup');
ok(sanDecode('&#106;avascript:')==='javascript:', 'entities decode before the scheme is judged');

/* ── the single clock ────────────────────────────────────────────────────
   One pump drives everything. What has to hold: a slot fires on its period, a
   long gap costs one run (not thirty), one frame fires at most two slots so a
   restored tab cannot stampede, a throwing job is isolated, and off() works. */
let ck=clockFactory();
ck.setNow(0);
let a=0, b=0;
const sa=ck.every(1000, function(){ a++; }, {label:'a'});
const sb=ck.every(5000, function(){ b++; }, {label:'b'});
ok(ck.list().length===2, 'two slots are registered');
ck.frameNow(999);
ok(a===0, 'a slot does not fire before its period');
ck.frameNow(1000);
ok(a===1, 'it fires on its period');
ck.frameNow(1000);
ok(a===1, 'and not twice in the same millisecond');
ck.frameNow(2000);
ok(a===2, 'and again one period later');
ck.frameNow(5000);
ok(b===1, 'the slower slot fires on its own period, not the fast one\'s');
/* a tab restored after an hour: the missed cycles are counted, and each slot
   still runs exactly once */
const before_a=a, before_b=b;
ck.frameNow(5000+3600000);
ok(a===before_a+1 && b===before_b+1, 'an hour-long gap costs one run per slot');
ok(ck.stats().missed>0, 'the skipped cycles are counted honestly');

let ck2=clockFactory();
ck2.setNow(0);
let order=[];
for(let i=0;i<5;i++){ (function(i){ ck2.every(1000, function(){ order.push(i); }); })(i); }
ck2.frameNow(10000);
ok(order.length===2, 'one frame fires at most two slots');
ck2.frameNow(10001);
ok(order.length===4, 'the next frame continues the wake-up');
ck2.frameNow(10002);
ok(order.length===5, 'and the fifth slot is reached on the third frame');

let ck3=clockFactory();
ck3.setNow(0);
let boom=0, after=0;
ck3.every(1000, function(){ boom++; throw new Error('boom'); }, {label:'throws'});
ck3.every(1000, function(){ after++; }, {label:'survives'});
ck3.frameNow(1000);
ok(boom===1 && after===1, 'a throwing slot does not stop the one behind it');
ok(ck3.stats().errors===1, 'the throw is counted');
ck3.frameNow(2000);
ok(boom===2 && after===2, 'and the clock keeps its schedule afterwards');
const h3=ck3.list()[0];
ok(ck3.off(h3)===true, 'a slot can be cancelled');
ck3.frameNow(3000);
ok(boom===2 && after===3, 'the cancelled slot stops and the other keeps running');
ok(ck3.off({})===false, 'cancelling something that is not a slot is a no-op');
ok(ck3.clear()===1, 'clear() reports how many slots it dropped');
ok(ck3.list().length===0, 'and the clock is empty afterwards');

let ck4=clockFactory();
ck4.setNow(0);
let gated=0;
ck4.every(1000, function(){ gated++; }, {when:function(){ return false; }});
ck4.frameNow(5000);
ok(gated===0, 'a slot whose when() is false never runs');
ck4.frameNow(6000);
ok(gated===0 && ck4.stats().missed===0,
   'and holding it back is not reported as missed cycles');

let ck5=clockFactory();
ck5.setNow(0);
let imm=0;
ck5.every(2000, function(){ imm++; }, {immediate:true});
ck5.frameNow(0);
ok(imm===1, 'an immediate slot runs on the first frame');
ok(!ck5.list()[0].first, 'and its first run is not counted as a missed cycle');
let threw=false;
try{ clockTick(); }catch(e){ threw=true; }
ok(!threw, 'the shared 1s tick is safe when the page it looks at is not there');

/* ── windowed grid layout ──────────────────────────────────────────────── */
ok(vsCols(1157,306,16)===3, 'a 1157px grid fits three 306px columns');
ok(vsCols(617,306,16)===1, '617px fits one (two would need 624)');
ok(vsCols(0,306,16)===1, 'a hidden grid measures zero and falls back to one column');
ok(vsCols(-5,306,16)===1, 'a negative measurement cannot produce a negative column count');
ok(vsCols(1000,0,16)===1, 'a missing minimum width cannot divide by zero');

const L1=vsLayout(7,3,[100,100,100,100,100,100,100],260,16,null);
ok(L1.rows===3, 'seven items in three columns make three rows');
ok(JSON.stringify(L1.sets)===JSON.stringify([[0,1,2],[3,4,5],[6]]),
   'the row packing is row-major');
ok(L1.tops[0]===0 && L1.tops[1]===116 && L1.tops[2]===232, 'row offsets include the gap');
ok(L1.height===332, 'the total height is the last row plus every gap');
ok(JSON.stringify(vsLayout(7,3,[100,100,100,100,100,100,100],260,16,null))===JSON.stringify(L1),
   'the layout is deterministic');

const L2=vsLayout(4,3,[100,100,100,100],260,16,[1,3,1,1]);
ok(JSON.stringify(L2.sets)===JSON.stringify([[0],[1],[2,3]]),
   'a full-span item takes a whole row and the next item starts a fresh one');
/* the item-to-row map is what makes a prepend anchor exact: without it the
   anchor's new row would have to be guessed at with index/columns, which is
   wrong as soon as a full-width row is in the list */
ok(JSON.stringify(L1.rowOf)===JSON.stringify([0,0,0,1,1,1,2]),
   'the layout reports which row each item landed in');
ok(JSON.stringify(L2.rowOf)===JSON.stringify([0,1,2,2]),
   'and it counts the full-width rows correctly');
ok(L2.rowOf[3]===2 && L2.tops[L2.rowOf[3]]===232,
   'an item after a full-width row is found at the row it is really in');
ok(L2.rowOf.length===4 && vsLayout(0,3,[],260,16,null).rowOf.length===0,
   'the map is exactly one entry per item');
ok(L2.rowH.length===3 && L2.tops[1]===116, 'and the rows after it stay in sequence');
ok(JSON.stringify(vsLayout(4,1,[100,100,100,100],260,16,[1,1,1,1]).sets)===JSON.stringify([[0],[1],[2],[3]]),
   'a one-column grid is one item per row');
/* the bug this replaced: every item was given a row of its own because a span
   of 1 was read as truthy */
ok(vsLayout(6,3,[100,100,100,100,100,100],260,16,[1,1,1,1,1,1]).rows===2,
   'per-item spans of one do not collapse the grid into one item per row');
ok(vsLayout(0,3,[],260,16,null).rows===0 && vsLayout(0,3,[],260,16,null).height===0,
   'an empty list has no rows and no height');
ok(vsLayout(3,3,[0,0,0],280,16,null).height===280, 'unmeasured items use the estimate');
ok(vsLayout(3,3,[0,900,0],280,16,null).rowH[0]===900, 'a measured row uses the tallest cell');

/* a hundred rows of 100 with a 16px gap: tops are 0,116,232,… */
const L3=vsLayout(100,1,new Array(100).fill(100),260,16,null);
ok(JSON.stringify(vsWindow(0,300,L3,0))===JSON.stringify({first:0,last:2}),
   'the window covers the rows the viewport intersects');
ok(vsWindow(0,300,L3,500).last===6, 'overscan extends the window by that many pixels');
ok(vsWindow(5000,300,L3,0).first===43, 'scrolling moves the window start to the row in view');
ok(vsWindow(5000,300,L3,0).last>=vsWindow(5000,300,L3,0).first,
   'the window is never inverted');
ok(JSON.stringify(vsWindow(-5000,300,L3,0))===JSON.stringify({first:0,last:0}),
   'a grid measured below the fold renders its first row, not nothing');
ok(JSON.stringify(vsWindow(0,300,vsLayout(0,3,[],260,16,null),0))===JSON.stringify({first:0,last:-1}),
   'an empty layout has an empty window');
ok(vsWindow(999999,300,L3,0).last===99, 'the window is clamped to the last row');
ok(vsWindow(999999,300,L3,0).first<=99, 'and never runs past the end of the list');

/* zeros are "not measured yet" and take no part in the median */
ok(vsMedian([0,100,200,300])===200, 'the estimate is the median of what was measured');
ok(vsMedian([0,0,0])===0, 'nothing measured yet means no estimate');
ok(vsMedian([450])===450, 'a single measurement is the estimate');
ok(vsMedian([0,100,90000,110])===110, 'one enormous card cannot inflate the estimate');

/* ── اخبار منتخب carousel ─────────────────────────────────────────────── */
ok(LEAD_PER===4 && LEAD_POOL===20, 'the row is four cards drawn from a pool of twenty');
ok(LEAD_ROTATE_MS>=5000, 'a carousel that turns faster than five seconds is unreadable');

/* twenty-four stories over six assets, each six minutes older than the last */
let leadArts=[], li=0;
for(const sym of ['BTC','ETH','XAU','WTI','DXY','SPX']){
  for(let k=0;k<4;k++){
    li+=1;
    leadArts.push(art({id:'L'+li, title:'story '+li, title_fa:'خبر '+li, assets:[sym],
      credibility:0.9-k*0.05, published_ts:NOW-li*360}));
  }
}
const lp=leadPick(leadArts, NOW);
ok(lp.length===LEAD_POOL, 'exactly twenty stories are selected');
ok(new Set(lp.slice(0,6).map(a=>a.assets[0])).size===6,
   'the first six cards cover six different assets');
ok(lp[0].credibility>=lp[lp.length-1].credibility, 'credibility orders the pool');
ok(leadPick([art({id:'low',credibility:0.4,assets:['BTC'],published_ts:NOW-600})], NOW).length===0,
   'a story under the credibility floor is not selected at all');
const tie=leadPick([art({id:'old',credibility:0.8,assets:['BTC'],published_ts:NOW-20*H}),
                    art({id:'new',credibility:0.8,assets:['ETH'],published_ts:NOW-3600})], NOW);
ok(tie[0].id==='new', 'between equals the fresher story comes first');
ok(leadPick(leadArts, NOW).map(a=>a.id).join()===lp.map(a=>a.id).join(), 'the pick is deterministic');
ok(leadTs({published_ts:NOW*1000})===NOW, 'a millisecond epoch is normalised, not trusted');

const leadpg=leadPages(lp);
ok(leadpg===5, 'twenty stories page as five rows of four');
ok(leadWindow(lp,0).length===4, 'a page is four cards');
ok(leadWindow(lp,4)[3].id===lp[19].id, 'the last page is full and ends on the last story');
ok(leadWindow(lp,5)[0].id===lp[0].id, 'past the last page the row wraps to the first');
ok(leadWindow(lp,-1)[0].id===lp[16].id, 'a negative page wraps backwards instead of rendering nothing');
ok(leadWindow([], 3).length===0 && leadPages([])===1, 'an empty pool has one empty page, not zero');
const leadSeen=new Set();
for(let p=0;p<leadpg;p++) leadWindow(lp,p).forEach(a=>leadSeen.add(a.id));
ok(leadSeen.size===20, 'five pages between them show all twenty stories, none twice');

const leadHead=leadHeadHTML(lp,0);
ok(leadHead.indexOf('leadPlay')>=0, 'the head carries the pause control');
ok(leadHead.indexOf('lead-dot')>=0 && leadHead.indexOf('lead-pos')>=0,
   'and a dot for every page plus the position');
ok(leadHead.indexOf('aria-pressed="false"')>=0, 'the pause control says whether the row is turning');
ok(leadHead.indexOf('lead-dot on')>=0 || leadHead.indexOf('lead-dot on"')>=0,
   'the current page is the marked dot');
ok(leadHeadHTML([leadArts[0]],0).indexOf('lead-btn')<0,
   'a single page of stories needs no pager at all');

const leadNoImg=leadCardHTML(art({id:'A1', title_fa:'یک خبر', assets:['BTC'], topic:'macro'}));
ok(leadNoImg.indexOf('class="thumb"')<0, 'a story without an image renders no banner');
ok(leadNoImg.indexOf('openArticle(&quot;A1&quot;)')>=0, 'the card opens its own story');
ok(leadNoImg.indexOf('hideNews(')>=0, 'every card keeps the hide button');
const leadBadUrl=leadCardHTML(art({id:'A2', title_fa:'x', assets:['BTC'], topic:'macro',
  image:'javascript:alert(1)'}));
ok(leadBadUrl.indexOf('javascript:')<0, 'a javascript: image URL never reaches a src attribute');
const leadTrap=leadCardHTML(art({id:'A3', title_fa:'تیتر "قلابی"', assets:['BTC'], topic:'macro'}));
ok(leadTrap.indexOf('<div class="lead-ttl">تیتر')>=0 && leadTrap.indexOf('"قلابی"')<0,
   'the headline is escaped, not injected into the card');

if(FAILED){ console.log('FAILED assertions: '+FAILED); process.exit(1); }
console.log('all dashboard logic assertions passed');
"""


@pytest.fixture(scope="session")
def logic_result(tmp_path_factory):
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not on PATH")
    page = _page()
    harness = "\n".join([STUBS] + [extract(page, u) for u in UNITS] + [ASSERTS])
    path = tmp_path_factory.mktemp("logic") / "harness.js"
    path.write_text(harness, encoding="utf-8")
    proc = subprocess.run([node, str(path)], capture_output=True, text=True, encoding="utf-8")
    return proc


def test_pure_dashboard_logic(logic_result):
    if logic_result.returncode != 0:
        pytest.fail("node harness failed:\n" + (logic_result.stdout or "") +
                    (logic_result.stderr or ""))
    assert "all dashboard logic assertions passed" in logic_result.stdout
