/* DL6.1 · theme toggle — persisted, meta-following, icon-swapping */
(function(){
  var KEY='mohmd-theme';
  var meta=document.querySelector('meta[name="theme-color"]');
  function apply(t){
    document.documentElement.setAttribute('data-theme', t);
    if(meta) meta.setAttribute('content', t==='light' ? '#F2F5F9' : '#0C111C');
    var moon=document.getElementById('themeIcMoon'), sun=document.getElementById('themeIcSun');
    if(moon) moon.style.display = t==='light' ? 'none' : '';
    if(sun) sun.style.display = t==='light' ? '' : 'none';
  }
  window.toggleTheme=function(){
    var t=document.documentElement.getAttribute('data-theme')==='light' ? 'dark' : 'light';
    try{ localStorage.setItem(KEY, t); }catch(e){}
    apply(t);
  };
  var saved='dark';
  try{ saved=localStorage.getItem(KEY) || 'dark'; }catch(e){}
  apply(saved);
})();
