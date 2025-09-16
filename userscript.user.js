// ==UserScript==
// @name         Work Wellness Assistant Bridge
// @namespace    http://tampermonkey.net/
// @version      0.2
// @description  Detect YouTube usage and show work time panel
// @match        *://*/*
// @grant        GM_addStyle
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    const API = 'http://localhost:5600';

    // Small UI panel
    GM_addStyle(`
      #wwa_panel{position:fixed; right:12px; bottom:12px; z-index:2147483647; font-family:system-ui,Arial;}
      #wwa_panel .card{background:#fff;border:1px solid #ddd;border-radius:10px;padding:8px 10px;box-shadow:0 2px 12px rgba(0,0,0,.08)}
      #wwa_panel .row{display:flex;gap:8px}
      #wwa_panel button{padding:4px 8px;border:1px solid #888;border-radius:8px;background:#fff;cursor:pointer}
      #wwa_panel button:hover{background:#f5f5f5}
    `);

    const box = document.createElement('div');
    box.id = 'wwa_panel';
    box.innerHTML = `
      <div class="card">
        <div style="font-weight:700">Work status</div>
        <div class="row"><div>Work: <span id="wwa_work">-</span> min</div><div>Left: <span id="wwa_left">-</span> min</div></div>
        <div class="row" style="margin-top:6px">
          <button id="wwa_start">Start</button>
          <button id="wwa_end">End</button>
          <a href="${API}/panel" target="_blank"><button>Panel</button></a>
        </div>
      </div>`;
    document.documentElement.appendChild(box);

    document.getElementById('wwa_start').onclick = ()=> fetch(`${API}/start`, {method:'POST'});
    document.getElementById('wwa_end').onclick = ()=> fetch(`${API}/end`, {method:'POST'});

    async function refresh(){
        try{
            const r = await fetch(`${API}/status`, {cache:'no-store'});
            if(!r.ok) return;
            const s = await r.json();
            document.getElementById('wwa_work').textContent = s.work_minutes;
            document.getElementById('wwa_left').textContent = s.remaining_minutes;
        }catch(_){ /* ignore */ }
    }
    setInterval(refresh, 15000); refresh();

    // YouTube watching detection
    const onYouTube = /(^|\.)youtube\.com$/.test(location.hostname);
    let ytActive = false;

    function startYT(){
        if(ytActive) return; ytActive = true;
        fetch(`${API}/event`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({type:'youtube_start', url: location.href})});
    }
    function stopYT(){
        if(!ytActive) return; ytActive = false;
        fetch(`${API}/event`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({type:'youtube_stop', url: location.href})});
    }

    function visibilityCheck(){
        if(!onYouTube) return;
        const visible = document.visibilityState === 'visible';
        if(visible) startYT(); else stopYT();
    }

    if(onYouTube){
        document.addEventListener('visibilitychange', visibilityCheck);
        window.addEventListener('focus', visibilityCheck);
        window.addEventListener('blur', visibilityCheck);
        visibilityCheck();
    }

    // Generic manual break buttons via hotkeys
    // Ctrl+Alt+B = break start, Ctrl+Alt+N = break end
    document.addEventListener('keydown', e=>{
        if(e.ctrlKey && e.altKey && e.code==='KeyB'){
            fetch(`${API}/event`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({type:'break_start', reason:'manual-hotkey'})});
        }
        if(e.ctrlKey && e.altKey && e.code==='KeyN'){
            fetch(`${API}/event`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({type:'break_end', reason:'manual-hotkey'})});
        }
    });
})();
