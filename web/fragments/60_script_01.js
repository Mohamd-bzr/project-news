/* ══ CHROME POLISH ════════════════════════════════════════════════════════
   Two passes over every text node the interface renders: emoji become sprite
   glyphs (chrome authored in markup already uses the sprite), and the middle
   dot that the old build strung through its meta lines becomes the hairline
   separator the shell uses. Prose is skipped on purpose — article bodies, news
   cards, report text and the telegram message/preview keep exactly what was
   written, emoji and dots included. */
(function(){
  var MAP = {
    '\uD83D\uDCF0':'news','\uD83D\uDCCA':'chart','\uD83D\uDCC8':'chart','\uD83D\uDCC9':'chart',
    '\uD83D\uDCA1':'bulb','\uD83D\uDCC5':'calendar','\uD83D\uDDD3\uFE0F':'calendar','\uD83D\uDDD3':'calendar',
    '\uD83C\uDFDB\uFE0F':'bank','\uD83C\uDFDB':'bank','\uD83D\uDDC4\uFE0F':'archive','\uD83D\uDDC4':'archive',
    '\u2B50':'star','\u2605':'star','\u2606':'star','\uD83E\uDE7A':'pulse',
    '\uD83D\uDCE8':'send','\uD83D\uDE80':'send','\u2699\uFE0F':'gear','\u2699':'gear',
    '\uD83D\uDCE1':'rss','\uD83D\uDCB9':'coins','\uD83E\uDE99':'coins','\uD83D\uDD0D':'search',
    '\u2715':'x','\u2717':'x','\u27F3':'refresh','\u2630':'menu','\u26A1':'mark',
    '\u26A0\uFE0F':'warn','\u26A0':'warn','\uD83D\uDCC4':'file','\uD83D\uDCDD':'file',
    '\uD83D\uDD50':'clock','\uD83D\uDD52':'clock','\u23F1':'clock','\uD83D\uDD25':'fire',
    '\uD83C\uDFF7\uFE0F':'tag','\uD83C\uDFF7':'tag','\uD83D\uDD17':'link','\uD83C\uDF19':'moon',
    '\uD83D\uDD14':'bell','\uD83D\uDD15':'bell-off','#\uFE0F\u20E3':'hash','\uD83D\uDC41\uFE0F':'eye','\uD83D\uDC41':'eye',
    '\uD83D\uDE48':'eye-off','\uD83D\uDCCC':'pin','\uD83D\uDCBE':'save','\u2795':'plus',
    '\u2713':'check','\u2714':'check','\u2705':'check','\u26F6':'expand','\u21E4':'panel','\u21E5':'panel',
    '\u2764\uFE0F':'heart','\u2764':'heart','\uD83D\uDCAC':'comment','\uD83C\uDF10':'globe',
    '\uD83C\uDFAF':'target','\uD83C\uDFAC':'film','\uD83C\uDFC5':'trophy','\uD83C\uDFC6':'trophy',
    '\uD83D\uDCDA':'book','\uD83D\uDCD6':'book','\uD83D\uDC65':'users','\uD83D\uDC64':'users',
    '\uD83D\uDCCB':'list','\uD83E\uDDE9':'grid','\uD83C\uDF89':'trophy','\uD83D\uDCA0':'grid',
    '\u270D\uFE0F':'pen','\u270D':'pen','\uD83D\uDCDD':'pen','\u21A9\uFE0F':'undo','\u21A9':'undo',
    '\uD83D\uDDD7\uFE0F':'shrink','\uD83D\uDDD7':'shrink','\uD83D\uDE31':'pulse',
    '\uD83D\uDD16':'bookmark','\uD83C\uDDEE\uD83C\uDDF7':'globe'
  };
  var KEYS = Object.keys(MAP).sort(function(a,b){ return b.length-a.length; });
  if(!KEYS.length) return;
  /* emoji and country-flag pairs are matched in one pass; a flag the chrome has
     no slot for is removed rather than left as two letters on Windows */
  var RX = new RegExp('(' + KEYS.join('|') +
         '|[\uD83C][\uDDE6-\uDDFF](?:[\uD83C][\uDDE6-\uDDFF])?)','g');
  /* prose keeps whatever its author wrote; chrome — headings, meta rows, buttons,
     chips, toasts — is converted, so the modal bodies are covered too now. */
  var SKIP = '#artBody p,.idea-txt,.idea-ttl,.rep-doc,.ncard,.lead-card,.relrow,.cites,'+
             '#tgPreview,#tgTemplate,textarea,code,pre,script,style';
  /* the middle dot was the old build's one connective, everywhere; in chrome it
     becomes the hairline the shell already uses between fields (.ms) */
  var SEP_SKIP = '#artBody p,.rep-doc,.idea-txt,.idea-ttl,.relrow,.cites,.ncard,.lead-card,'+
                 '#tgPreview,#tgTemplate,textarea,code,pre,script,style,option';
  function iconEl(name){
    var ns='http://www.w3.org/2000/svg';
    var s=document.createElementNS(ns,'svg');
    s.setAttribute('class','ic'); s.setAttribute('aria-hidden','true');
    var u=document.createElementNS(ns,'use'); u.setAttribute('href','#i-'+name);
    s.appendChild(u); return s;
  }
  function sepEl(){
    var s=document.createElement('i');
    s.className='vr'; s.setAttribute('aria-hidden','true');
    return s;
  }
  function inZone(p,sel){ return !!(p && p.closest && p.closest(sel)); }
  function isFlag(s){
    if(!s.length || s.length%2) return false;
    for(var i=0;i<s.length;i+=2){
      if(s.charCodeAt(i)!==0xD83C) return false;
      var lo=s.charCodeAt(i+1);
      if(lo<0xDDE6 || lo>0xDDFF) return false;   /* U+1F1E6..U+1F1FF */
    }
    return true;
  }
  function swap(node){
    var v=node.nodeValue;
    if(!v) return false;
    var p=node.parentElement;
    var doIcon = RX.test(v) && !inZone(p,SKIP);
    RX.lastIndex=0;
    var doSep = v.indexOf(' \u00B7 ')>-1 && !inZone(p,SEP_SKIP);
    if(!doIcon && !doSep) return false;
    var parts=doIcon ? v.split(RX) : [v], frag=document.createDocumentFragment(), changed=false;
    for(var i=0;i<parts.length;i++){
      var t=parts[i]; if(!t) continue;
      var name=doIcon ? MAP[t] : null;
      if(name){ frag.appendChild(iconEl(name)); changed=true; continue; }
      if(doIcon && isFlag(t.trim())){ changed=true; continue; }
      if(!doSep){ frag.appendChild(document.createTextNode(t)); continue; }
      var sub=t.split(' \u00B7 ');
      for(var k=0;k<sub.length;k++){
        if(k){ frag.appendChild(sepEl()); changed=true; }
        if(sub[k]) frag.appendChild(document.createTextNode(sub[k]));
      }
    }
    if(changed) node.parentNode.replaceChild(frag,node);
    return changed;
  }
  function walk(root){
    if(!root) return;
    if(root.nodeType===3){ swap(root); return; }
    if(root.nodeType!==1) return;
    var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode:function(n){
      var el=n.parentElement;
      return (el && el.closest(SKIP) && el.closest(SEP_SKIP)) ? NodeFilter.FILTER_REJECT
                                                             : NodeFilter.FILTER_ACCEPT;
    }});
    var batch=[], n; while((n=w.nextNode())) batch.push(n);
    for(var i=0;i<batch.length;i++) swap(batch[i]);
  }
  function boot(){
    walk(document.body);
    var busy=false, queued=[];
    var mo=new MutationObserver(function(muts){
      if(busy){ for(var i=0;i<muts.length;i++) queued.push(muts[i]); return; }
      busy=true;
      try{
        for(var i=0;i<muts.length;i++){
          var m=muts[i];
          if(m.type==='characterData'){ swap(m.target); continue; }
          for(var j=0;j<m.addedNodes.length;j++) walk(m.addedNodes[j]);
        }
      }catch(e){}
      busy=false; queued.length=0;
    });
    mo.observe(document.body,{childList:true,subtree:true,characterData:true});
    window.__iconify=function(root){ walk(root||document.body); };
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot);
  else boot();
})();
