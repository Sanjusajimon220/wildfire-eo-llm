"""
groundtruth_map.py — the shared interactive-map builder.

One copy, imported by every fire notebook. Fix a bug here and all four chapters get it.

    import groundtruth_map as gm
    gm.build(CONFIG, AOI, PLACES, severity=severity, burn_mask=burn_mask)

Everything that needs human judgement (windows, thresholds, QA) stays in the notebook.
Only this presentation layer is shared.
"""

import json, base64, urllib.request, datetime as dt
import ee


def _mask_s2(img, cfg):
    good = img.select(cfg['cs_band']).gte(cfg['cs_threshold'])
    if cfg.get('scl_shadow_backup'):
        good = good.And(img.select('SCL').neq(3))
    return img.updateMask(good)


def _s2_rgb(cfg, region, start, end):
    csplus = ee.ImageCollection(cfg['cs_plus_collection'])
    col = (ee.ImageCollection(cfg['s2_collection'])
           .filterBounds(region).filterDate(start, end)
           .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cfg['max_cloud_pct']))
           .linkCollection(csplus, [cfg['cs_band']])
           .map(lambda im: _mask_s2(im, cfg)))
    return col.select(['B4', 'B3', 'B2']).median().clip(region)


def _png_datauri(img, vis, region, px, label):
    url = img.getThumbURL({**vis, 'region': region, 'dimensions': px, 'format': 'png'})
    raw = urllib.request.urlopen(url, timeout=300).read()
    if raw[:4] != b'\x89PNG':
        raise RuntimeError(f'{label}: not a PNG -> {raw[:200]}')
    print(f'  {label:9} {len(raw)/1e6:5.2f} MB')
    return 'data:image/png;base64,' + base64.b64encode(raw).decode()


def build(CONFIG, AOI, PLACES,
          severity=None, burn_mask=None,
          img_bbox=None, px=1400, out=None):
    """Export imagery, embed it, write a self-contained HTML page. Returns the path."""

    FID = CONFIG['fire_id']
    bb  = CONFIG['aoi_bbox']

    IMG_BBOX = img_bbox or [bb[0]-0.02, bb[1]-0.02, bb[2]+0.02, bb[3]+0.02]
    IMG = ee.Geometry.Rectangle(IMG_BBOX)

    print('exporting imagery ...')
    RGB_VIS = {'min': 200, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}
    URI_PRE  = _png_datauri(_s2_rgb(CONFIG, IMG, CONFIG['pre_start'],  CONFIG['pre_end']),
                            RGB_VIS, IMG, px, 'before')
    URI_POST = _png_datauri(_s2_rgb(CONFIG, IMG, CONFIG['post_start'], CONFIG['post_end']),
                            RGB_VIS, IMG, px, 'after')
    try:
        if severity is None:
            raise ValueError('no severity computed')
        URI_SEV = _png_datauri(severity.updateMask(burn_mask).clip(AOI),
                               {'min': 1, 'max': 4,
                                'palette': ['ffe08a', 'f9a03f', 'e8532b', '9d0208']},
                               AOI, px, 'severity')
        HAS_SEV = True
    except Exception as e:
        URI_SEV, HAS_SEV = '', False
        print('  severity skipped:', e)

    # ---- FIRMS detections -> compact string; origin derived automatically ----
    gj = json.load(open(f'firms_timeline_{FID}.geojson'))
    lons = [f['geometry']['coordinates'][0] for f in gj['features']]
    lats = [f['geometry']['coordinates'][1] for f in gj['features']]
    LON0, LAT0 = int(max(lons)) + 1, int(min(lats))

    by_ts = {}
    for f in gj['features']:
        lon, lat = f['geometry']['coordinates']
        pr = f['properties']
        ts = pr['date'][:16].replace(' ', 'T')
        by_ts.setdefault(ts, []).append(
            f"{round((LON0-lon)*1e5)},{round((lat-LAT0)*1e5)},"
            f"{round(float(pr.get('frp', 0) or 0))}")
    RAW = ';'.join(f"{t}|{' '.join(v)}" for t, v in sorted(by_ts.items()))
    print(f'{sum(len(v) for v in by_ts.values())} detections, {len(by_ts)} overpasses')

    # ---- numbers ----
    facts = json.load(open(f'facts_{FID}.json'))
    ign = facts['firms']
    sev_ha = facts.get('severity_ha') or {}
    tot_ha = facts.get('total_burned_ha')
    off = facts.get('official_reference', {}) or {}
    SEV_ROWS = ''.join(
        f'<div class="key"><span class="dot" style="background:#{c}"></span>{n}'
        f'<b style="margin-left:auto;color:#fff">{sev_ha.get(k, 0):,.0f} ha</b></div>'
        for k, n, c in [('low', 'Low', 'ffe08a'),
                        ('moderate_low', 'Moderate-low', 'f9a03f'),
                        ('moderate_high', 'Moderate-high', 'e8532b'),
                        ('high', 'High', '9d0208')])

    HTML = r'''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>__NAME__ &mdash; how the fire spread</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@700&family=Space+Mono:wght@400;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
    <style>
    :root{--paper:#0f1218;--ink:#f2f4f8;--sub:#9aa4b4;--line:#2a3240;--hot:#ef6a2b;--panel:rgba(16,20,27,.95)}
    *{box-sizing:border-box}html,body{margin:0;height:100%}
    body{background:var(--paper);color:var(--ink);font-family:Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
    .fig{position:fixed;inset:0}#map{position:absolute;inset:0;background:#0b0e13}
    #glow{position:absolute;inset:0;pointer-events:none;z-index:410}
    #divider{position:absolute;top:0;bottom:0;width:2px;background:rgba(255,255,255,.9);
     box-shadow:0 0 8px rgba(0,0,0,.7);z-index:406;pointer-events:none;display:none}
    #divider:after{content:'';position:absolute;top:50%;left:50%;width:28px;height:28px;margin:-14px 0 0 -14px;
     border-radius:50%;background:rgba(255,255,255,.92);box-shadow:0 0 10px rgba(0,0,0,.6)}
    .head{position:absolute;top:0;left:270px;right:190px;z-index:500;padding:14px 18px 26px;pointer-events:none;
     background:linear-gradient(180deg,rgba(9,12,17,.9),rgba(9,12,17,.45) 60%,transparent)}
    .eyebrow{font-family:"Space Mono",monospace;font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:var(--hot);margin:0 0 5px}
    h1{font-family:"Space Grotesk",sans-serif;font-size:clamp(17px,2.2vw,24px);line-height:1.12;margin:0 0 6px}
    .dek{font-size:12.5px;line-height:1.5;color:#c3cad6;margin:0;max-width:62ch}.dek b{color:#fff}
    .clock{position:absolute;top:12px;right:16px;z-index:520;text-align:right;background:var(--panel);
     border:1px solid var(--line);border-radius:11px;padding:9px 13px;pointer-events:none}
    .clock .date{font-family:"Space Mono",monospace;font-weight:700;font-size:clamp(15px,2vw,21px)}
    .clock .time{font-family:"Space Mono",monospace;font-size:11px;color:var(--sub)}
    .clock .day{font-family:"Space Mono",monospace;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--hot);margin-top:5px;font-weight:700}
    #leftRail{position:absolute;left:16px;top:14px;bottom:140px;z-index:500;width:238px;
     display:flex;flex-direction:column;gap:8px;overflow-y:auto;padding-right:4px}
    #leftRail::-webkit-scrollbar{width:6px}
    #leftRail::-webkit-scrollbar-thumb{background:#2f3949;border-radius:3px}
    #leftRail .panel{position:static;width:100%;flex:none}
    .panel{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:12px 13px}
    .panel h2{font-family:"Space Mono",monospace;font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--sub);margin:0 0 9px;font-weight:700}
    .layers{position:sticky;top:0;z-index:2;box-shadow:0 6px 14px rgba(9,12,17,.85)}
    .lay{display:flex;align-items:center;gap:8px;font-size:11.5px;margin:5px 0;cursor:pointer;color:#c3cad6}
    .lay input{accent-color:var(--hot);flex:none}
    .sec{margin-top:9px;padding-top:9px;border-top:1px solid var(--line)}
    .sec label.rng{font-family:"Space Mono",monospace;font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--sub);display:flex;justify-content:space-between;margin-bottom:4px}
    .hint{font-size:10px;line-height:1.4;color:var(--sub);margin:5px 0 0}
    .ramp{height:9px;border-radius:5px;background:linear-gradient(90deg,#f9a03f,#ef6a2b,#d62828,#6a040f);margin-bottom:4px}
    .rl{display:flex;justify-content:space-between;font-family:"Space Mono",monospace;font-size:10px;color:var(--sub)}
    .key{display:flex;align-items:center;gap:8px;font-size:11.5px;color:#c3cad6;margin-top:7px}
    .dot{width:11px;height:11px;border-radius:50%;flex:none}
    .dot.ign{background:#fff;border:3px solid #000}
    .sizes{display:flex;align-items:flex-end;gap:9px;margin-top:9px}
    .sizes i{display:block;border-radius:50%;background:var(--hot);opacity:.85}
    .note{margin-top:10px;padding-top:9px;border-top:1px solid var(--line);font-size:10px;line-height:1.45;color:var(--sub)}
    .meta{margin-top:9px;padding-top:9px;border-top:1px solid var(--line);
     font-family:"Space Mono",monospace;font-size:9.5px;line-height:1.6;color:var(--sub)}
    .meta b{color:#c3cad6;font-weight:400}
    .valid{display:flex;justify-content:space-between;font-size:11px;color:#c3cad6;margin-top:6px;font-family:Inter,sans-serif}
    .valid b{color:#fff}.ok{color:#7ddc8f}
    .ctl{position:absolute;left:0;right:0;bottom:0;z-index:510;display:flex;align-items:center;gap:12px;padding:13px 18px 15px;
     background:linear-gradient(0deg,rgba(9,12,17,.95),rgba(9,12,17,.6) 65%,transparent)}
    button.play{flex:none;width:43px;height:43px;border-radius:50%;border:none;cursor:pointer;background:var(--hot);color:#140800;
     display:grid;place-items:center;box-shadow:0 0 18px rgba(239,106,43,.5)}
    button.play svg{width:19px;height:19px}
    .ghost{flex:none;background:transparent;border:1px solid var(--line);color:var(--sub);height:32px;padding:0 11px;
     border-radius:8px;cursor:pointer;font-family:"Space Mono",monospace;font-size:11px}
    .ghost:hover{color:#fff;border-color:#48566c}
    .track{flex:1;min-width:70px;display:flex;align-items:center}
    input[type=range]{width:100%;-webkit-appearance:none;height:5px;border-radius:4px;background:#2b3442;outline:none;cursor:pointer}
    input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:15px;height:15px;border-radius:50%;background:#fff;border:2px solid var(--hot)}
    input[type=range]::-moz-range-thumb{width:15px;height:15px;border-radius:50%;background:#fff;border:2px solid var(--hot)}
    .count{flex:none;font-family:"Space Mono",monospace;font-size:11px;color:var(--sub);min-width:176px;text-align:right}
    .count b{color:#fff}
    .leaflet-control-scale{margin-bottom:68px!important;margin-left:266px!important}
    .leaflet-control-zoom{margin-bottom:140px!important;margin-right:16px!important}
    .leaflet-control-scale-line{background:rgba(0,0,0,.5)!important;color:#fff!important;border-color:#7d8798!important}
    @media(max-width:900px){#leftRail{display:none}.head{left:0;right:0}.leaflet-control-scale{margin-left:12px!important}}
    @media(max-width:640px){.count{display:none}.clock{top:auto;bottom:118px;right:12px}}
    </style>
    <div class="fig">
     <div id="map"></div><canvas id="glow"></canvas><div id="divider"></div>

     <div class="head"><p class="eyebrow">Groundtruth &middot; Satellite journalism</p>
      <h1>How the __NAME__ fire spread, day by day</h1>
      <p class="dek">Each mark is where a satellite detected active fire; bigger marks burned more fiercely. It began on <b>__IGNDATE__</b> in __REGION__ and burned for __NDAYS__ days.</p></div>

     <div class="clock"><div class="date" id="cDate">&mdash;</div><div class="time" id="cTime">&nbsp;</div><div class="day" id="cDay">&nbsp;</div></div>

     <div id="leftRail">
      <div class="panel layers"><h2>What you're looking at</h2>
       <label class="lay"><input type="radio" name="view" value="base"> Global satellite only</label>
       <label class="lay"><input type="radio" name="view" value="pre"> + Sentinel-2 before &middot; 10 m</label>
       <label class="lay"><input type="radio" name="view" value="post"> + Sentinel-2 after &middot; 10 m</label>
       <label class="lay"><input type="radio" name="view" value="swipe" checked> + Compare before / after</label>
       <div class="sec" id="swipeWrap"><label class="rng"><span>&#9664; Before</span><span>After &#9654;</span></label>
        <input type="range" id="swipe" min="0" max="100" value="50">
        <p class="hint">Drag right to reveal the after image.</p></div>
       <div class="sec"><label class="rng"><span>Image opacity</span><span id="opVal">100%</span></label>
        <input type="range" id="opacity" min="0" max="100" value="100">
        <p class="hint">Fades Sentinel-2 to reveal the global satellite base underneath.</p></div>
       <div class="sec">
        <label class="lay"><input type="checkbox" id="lFire" checked> Fire detections &middot; VIIRS 375 m</label>
        <label class="lay" id="sevRow"><input type="checkbox" id="lSev"> Burn severity &middot; dNBR 20 m</label>
        <label class="lay"><input type="checkbox" id="lStreet" checked> Place names</label>
       </div>
      </div>

      <div class="panel" id="fireLeg"><h2>Fire detections</h2>
       <div class="ramp"></div>
       <div class="rl"><span>__D0__</span><span>__D1__</span></div>
       <div class="sizes">
        <span style="text-align:center"><i style="width:7px;height:7px;margin:0 auto 4px"></i>
         <span style="font-family:'Space Mono',monospace;font-size:9px;color:var(--sub)">low</span></span>
        <span style="text-align:center"><i style="width:12px;height:12px;margin:0 auto 4px"></i>
         <span style="font-family:'Space Mono',monospace;font-size:9px;color:var(--sub)">__FRPMID__</span></span>
        <span style="text-align:center"><i style="width:18px;height:18px;margin:0 auto 4px"></i>
         <span style="font-family:'Space Mono',monospace;font-size:9px;color:var(--sub)">__FRPMAX__ MW</span></span>
        <span style="font-size:10px;color:var(--sub);padding-bottom:2px">fire power</span>
       </div>
       <div class="key"><span class="dot ign"></span> Where the fire started</div>
       <p class="note">Colour = the day it burned. Size = fire radiative power.</p>
       <div class="meta">SOURCE <b>__FIRMSSRC__</b><br>RESOLUTION <b>375 m</b><br>
        PERIOD <b>__D0__ &ndash; __D1__ __YEAR__</b><br>NOTE <b>hotspots, not a perimeter</b></div>
      </div>

      <div class="panel" id="sevLeg" style="display:none"><h2>Burn severity &middot; dNBR</h2>
       __SEVROWS__
       <p class="note">Total __TOTHA__ ha, measured once after the smoke cleared &mdash; a final result, not a daily sequence.</p>
       <div class="meta">SOURCE <b>Sentinel-2 L2A</b><br>RESOLUTION <b>20 m</b><br>
        ACQUISITION <b>__ACQ__</b><br>METHOD <b>dNBR (Key &amp; Benson)</b></div>
       <div class="meta">VALIDATION
        <div class="valid"><span>This analysis</span><b>__OURHA__ ha</b></div>
        <div class="valid"><span>__OFFSRC__</span><b>__OFFHA__ ha</b></div>
        <div class="valid"><span>Difference</span><b class="ok">__PCTDIFF__</b></div>
       </div>
      </div>
     </div>

     <div class="ctl">
      <button class="play" id="play" aria-label="Play"><svg id="pIcon" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></button>
      <button class="ghost" id="restart">Restart</button><button class="ghost" id="speed">1&times;</button>
      <button class="ghost" id="fit">Reset view</button>
      <div class="track"><input id="scrub" type="range" min="0" max="1000" value="0" aria-label="Timeline"></div>
      <div class="count"><b id="cN">0</b> detections &middot; <b id="cKm">0</b> km from start</div></div>
    </div>
    <script>
    var RAW="__RAW__", IGN={lng:__IGNLON__,lat:__IGNLAT__};
    var LON0=__LON0__, LAT0=__LAT0__, HAS_SEV=__HASSEV__;
    var IMGB=L.latLngBounds([[__IS__,__IW__],[__IN__,__IE__]]);
    var AOIB=L.latLngBounds([[__AS__,__AW__],[__AN__,__AE__]]);
    var PLACES=__PLACES__;
    var URI_PRE="__URIPRE__", URI_POST="__URIPOST__", URI_SEV="__URISEV__";

    var PTS=[];
    RAW.split(';').forEach(function(g){var p=g.split('|'),t=Date.parse(p[0]+':00Z');
     p[1].trim().split(' ').forEach(function(q){var a=q.split(',');
      PTS.push({lng:LON0-(+a[0])/1e5,lat:LAT0+(+a[1])/1e5,t:t,frp:+(a[2]||0)});});});
    PTS.sort(function(a,b){return a.t-b.t;});
    var tMin=PTS[0].t,tMax=PTS[PTS.length-1].t,span=tMax-tMin,DAY=864e5,nDays=Math.ceil(span/DAY)+1;
    var FRPMAX=PTS.reduce(function(m,p){return Math.max(m,p.frp);},0)||1;
    var RAMP=['#f9a03f','#ef6a2b','#d62828','#9d0208','#6a040f'];
    function hx(h){return [parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)];}
    PTS.forEach(function(p){var f=(p.t-tMin)/span,s=f*(RAMP.length-1),
     i=Math.min(RAMP.length-2,Math.floor(s)),k=s-i,A=hx(RAMP[i]),B=hx(RAMP[i+1]);
     p.c=A.map(function(v,j){return Math.round(v+(B[j]-v)*k);});
     p.sz=5+9*Math.sqrt(Math.min(1,p.frp/FRPMAX));});

    var map=L.map('map',{zoomControl:true,attributionControl:false,minZoom:8});
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19}).addTo(map);
    map.createPane('pPre');map.createPane('pPost');map.createPane('pSev');map.createPane('pLab');
    map.getPane('pPre').style.zIndex=250;
    map.getPane('pPost').style.zIndex=260;
    map.getPane('pSev').style.zIndex=270;
    map.getPane('pLab').style.zIndex=390;map.getPane('pLab').style.pointerEvents='none';
    var labels=L.tileLayer('https://{s}.basemap.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png',
     {maxZoom:19,subdomains:'abcd',pane:'pLab'}).addTo(map);
    L.control.scale({imperial:false,position:'bottomleft'}).addTo(map);

    var lyPre =L.imageOverlay(URI_PRE, IMGB,{pane:'pPre'});
    var lyPost=L.imageOverlay(URI_POST,IMGB,{pane:'pPost'});
    var lySev =HAS_SEV?L.imageOverlay(URI_SEV,AOIB,{pane:'pSev',opacity:.85}):null;
    if(!lySev){document.getElementById('sevRow').style.display='none';}

    function fitAll(){map.fitBounds(IMGB.pad(0.45));}
    fitAll();
    L.marker([IGN.lat,IGN.lng],{zIndexOffset:900,icon:L.divIcon({className:'',iconSize:[20,20],iconAnchor:[10,10],
     html:'<div style="width:13px;height:13px;border-radius:50%;background:#fff;border:3px solid #000;box-shadow:0 0 0 3px rgba(0,0,0,.5)"></div>'})})
     .addTo(map).bindTooltip('Fire started here',{direction:'top',offset:[0,-10]});

    var placeLayer=L.layerGroup();
    PLACES.forEach(function(p){
      L.marker([p[1],p[2]],{interactive:false,keyboard:false,pane:'pLab',
        icon:L.divIcon({className:'',iconSize:[170,16],iconAnchor:[6,8],
          html:'<div style="display:flex;align-items:center;gap:5px;white-space:nowrap">'
            +'<span style="width:5px;height:5px;border-radius:50%;background:#fff;'
            +'box-shadow:0 0 3px rgba(0,0,0,.9);flex:none"></span>'
            +'<span style="font:500 11px Inter,sans-serif;color:#fff;'
            +'text-shadow:0 0 4px #000,0 0 8px #000">'+p[0]+'</span></div>'})
      }).addTo(placeLayer);
    });
    function updatePlaces(){
      var on=map.getZoom()>=10 && document.getElementById('lStreet').checked;
      if(on){if(!map.hasLayer(placeLayer))placeLayer.addTo(map);}
      else if(map.hasLayer(placeLayer))map.removeLayer(placeLayer);
    }
    map.on('zoomend',updatePlaces);updatePlaces();

    /* ---- swipe: clip the IMAGE element (well-defined box, no pane transform issues) ---- */
    var divider=document.getElementById('divider');
    function currentMode(){return document.querySelector('input[name=view]:checked').value;}
    function applySwipe(){
      var el=lyPost.getElement();
      if(!el||!map.hasLayer(lyPost)){divider.style.display='none';return;}
      var v=+document.getElementById('swipe').value, size=map.getSize();
      var frac=1-v/100;                                  // v=100 -> all AFTER
      var xC=size.x*frac;
      var xL=map.containerPointToLayerPoint([xC,0]).x;
      var nw=map.latLngToLayerPoint(IMGB.getNorthWest());
      var se=map.latLngToLayerPoint(IMGB.getSouthEast());
      var w=se.x-nw.x;
      var pct=w>0?Math.max(0,Math.min(100,(xL-nw.x)/w*100)):0;
      el.style.clipPath='inset(0 0 0 '+pct+'%)';
      el.style.webkitClipPath=el.style.clipPath;
      divider.style.display='block';
      divider.style.left=xC+'px';
    }
    function clearClip(){
      [lyPre,lyPost].forEach(function(l){var e=l.getElement();
        if(e){e.style.clipPath='';e.style.webkitClipPath='';}});
      divider.style.display='none';
    }
    function setView(mode){
      if(map.hasLayer(lyPre))map.removeLayer(lyPre);
      if(map.hasLayer(lyPost))map.removeLayer(lyPost);
      clearClip();
      document.getElementById('swipeWrap').style.display=(mode==='swipe')?'block':'none';
      if(mode==='pre'){lyPre.addTo(map);}
      else if(mode==='post'){lyPost.addTo(map);}
      else if(mode==='swipe'){lyPre.addTo(map);lyPost.addTo(map);setTimeout(applySwipe,80);}
    }
    document.querySelectorAll('input[name=view]').forEach(function(r){
      r.onchange=function(){if(r.checked)setView(r.value);};});
    document.getElementById('swipe').oninput=applySwipe;
    map.on('move zoom zoomend moveend resize',function(){
      if(currentMode()==='swipe')applySwipe();});
    lyPost.on('load add',function(){if(currentMode()==='swipe')setTimeout(applySwipe,20);});

    document.getElementById('opacity').oninput=function(e){var o=e.target.value/100;
     lyPre.setOpacity(o);lyPost.setOpacity(o);
     document.getElementById('opVal').textContent=e.target.value+'%';};
    document.getElementById('lStreet').onchange=function(e){
     if(e.target.checked){labels.addTo(map);}else{map.removeLayer(labels);}
     updatePlaces();};
    setView('swipe');

    /* ---- fire glow ---- */
    var cv=document.getElementById('glow'),ctx=cv.getContext('2d');
    function rs(){var s=map.getSize(),d=Math.min(2,window.devicePixelRatio||1);
     cv.width=s.x*d;cv.height=s.y*d;cv.style.width=s.x+'px';cv.style.height=s.y+'px';ctx.setTransform(d,0,0,d,0,0);}
    rs();map.on('resize',rs);
    var showFire=true, FL=8*36e5;
    function draw(){
     var s=map.getSize();ctx.clearRect(0,0,s.x,s.y);
     if(!showFire)return;
     ctx.globalCompositeOperation='lighter';
     for(var i=0;i<PTS.length;i++){var p=PTS[i];if(p.t>clock)continue;
      var q=map.latLngToContainerPoint([p.lat,p.lng]);
      if(q.x<-30||q.y<-30||q.x>s.x+30||q.y>s.y+30)continue;
      var f=Math.max(0,1-(clock-p.t)/FL),r=p.c[0],g=p.c[1],b=p.c[2],rad=p.sz+f*9;
      var gr=ctx.createRadialGradient(q.x,q.y,0,q.x,q.y,rad);
      gr.addColorStop(0,'rgba('+r+','+g+','+b+','+(.5+f*.35)+')');
      gr.addColorStop(.55,'rgba('+r+','+g+','+b+',.22)');
      gr.addColorStop(1,'rgba('+r+','+g+','+b+',0)');
      ctx.fillStyle=gr;ctx.beginPath();ctx.arc(q.x,q.y,rad,0,6.2832);ctx.fill();
      if(f>0){ctx.fillStyle='rgba(255,'+(210+Math.round(f*40))+',150,'+(f*.9)+')';
       ctx.beginPath();ctx.arc(q.x,q.y,2+f*2.5,0,6.2832);ctx.fill();}}
     ctx.globalCompositeOperation='source-over';}

    /* ---- clock, timeline, controls ---- */
    var MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    function fD(d){return d.getUTCDate()+' '+MON[d.getUTCMonth()]+' '+d.getUTCFullYear();}
    function fT(d){return ('0'+d.getUTCHours()).slice(-2)+':'+('0'+d.getUTCMinutes()).slice(-2)+' UTC';}
    function km(a,b){var R=6371,x=(b.lat-a.lat)*Math.PI/180,y=(b.lng-a.lng)*Math.PI/180,
     h=Math.pow(Math.sin(x/2),2)+Math.cos(a.lat*Math.PI/180)*Math.cos(b.lat*Math.PI/180)*Math.pow(Math.sin(y/2),2);
     return R*2*Math.atan2(Math.sqrt(h),Math.sqrt(1-h));}
    var red=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var clock=red?tMax:tMin,playing=false,sp=0,SP=[1,2,4],$=function(i){return document.getElementById(i);};

    function syncLegends(){
      $('fireLeg').style.display=showFire?'block':'none';
      $('sevLeg').style.display=$('lSev').checked?'block':'none';
    }
    $('lFire').onchange=function(e){showFire=e.target.checked;syncLegends();draw();};
    $('lSev').onchange=function(e){
      if(!lySev)return;
      e.target.checked?lySev.addTo(map):map.removeLayer(lySev);
      syncLegends();};
    function ensureFireOn(){
      if(showFire)return;
      showFire=true;$('lFire').checked=true;syncLegends();draw();}
    syncLegends();

    function ui(){var d=new Date(clock);$('cDate').textContent=fD(d);$('cTime').textContent=fT(d);
     $('cDay').textContent='Day '+Math.min(nDays,Math.floor((clock-tMin)/DAY)+1)+' of '+nDays;
     var n=0,far=0;for(var i=0;i<PTS.length;i++){if(PTS[i].t<=clock){n++;var k=km(IGN,PTS[i]);if(k>far)far=k;}}
     $('cN').textContent=n.toLocaleString();$('cKm').textContent=far.toFixed(1);
     $('scrub').value=Math.round((clock-tMin)/span*1000);}
    function setPlay(v){playing=v;
     $('pIcon').innerHTML=v?'<path d="M6 5h4v14H6zM14 5h4v14h-4z"/>':'<path d="M8 5v14l11-7z"/>';
     $('play').setAttribute('aria-label',v?'Pause':'Play');}

    var last=performance.now();
    function frame(now){var dt=now-last;last=now;
     if(playing){clock+=dt*(span/16000)*SP[sp];if(clock>=tMax){clock=tMax;setPlay(false);}ui();}
     draw();requestAnimationFrame(frame);}
    ui();requestAnimationFrame(frame);
    if(!red)setTimeout(function(){setPlay(true);},700);

    $('play').onclick=function(){ensureFireOn();if(clock>=tMax)clock=tMin;setPlay(!playing);};
    $('restart').onclick=function(){ensureFireOn();clock=tMin;ui();setPlay(true);};
    $('speed').onclick=function(e){sp=(sp+1)%SP.length;e.target.innerHTML=SP[sp]+'&times;';};
    $('fit').onclick=fitAll;
    $('scrub').oninput=function(e){ensureFireOn();setPlay(false);clock=tMin+(e.target.value/1000)*span;ui();};
    map.on('move zoom',function(){if(!playing)draw();});
    </script>'''


    frp_max = max((int(p.split(',')[2]) for v in by_ts.values() for p in v), default=0)
    d0 = dt.datetime.fromisoformat(ign['first_detection'])
    d1 = dt.datetime.fromisoformat(ign['last_detection'])
    rep = {
     '__NAME__': facts['fire_name'], '__REGION__': facts['region'],
     '__IGNDATE__': d0.strftime('%d %B %Y'), '__NDAYS__': str(ign['active_days']),
     '__D0__': d0.strftime('%d %b'), '__D1__': d1.strftime('%d %b'), '__YEAR__': d0.strftime('%Y'),
     '__RAW__': RAW, '__IGNLON__': str(ign['ignition_lon']), '__IGNLAT__': str(ign['ignition_lat']),
     '__LON0__': str(LON0), '__LAT0__': str(LAT0),
     '__HASSEV__': 'true' if HAS_SEV else 'false',
     '__PLACES__': json.dumps(PLACES, ensure_ascii=False),
     '__IW__': str(IMG_BBOX[0]), '__IS__': str(IMG_BBOX[1]),
     '__IE__': str(IMG_BBOX[2]), '__IN__': str(IMG_BBOX[3]),
     '__AW__': str(bb[0]), '__AS__': str(bb[1]), '__AE__': str(bb[2]), '__AN__': str(bb[3]),
     '__SEVROWS__': SEV_ROWS, '__TOTHA__': f"{tot_ha:,.0f}" if tot_ha else 'not yet measured',
     '__FRPMID__': str(round(frp_max/4)), '__FRPMAX__': str(frp_max),
     '__FIRMSSRC__': 'NASA FIRMS &middot; ' + CONFIG['firms_source'],
     '__ACQ__': facts['post_fire_window'][0] + ' &ndash; ' + facts['post_fire_window'][1],
     '__OURHA__': (f"{off['our_area_ha']:,.0f}" if off.get('our_area_ha')
                    else (f"{tot_ha:,.0f}" if tot_ha else '—')),
     '__OFFSRC__': off.get('source', 'official reference'),
     '__OFFHA__': (f"{off['area_ha']:,.0f}" if off.get('area_ha') else 'pending'),
     '__PCTDIFF__': (f"{off['pct_diff']:+.1f}%" if off.get('pct_diff') is not None else '—'),
     '__URIPRE__': URI_PRE, '__URIPOST__': URI_POST, '__URISEV__': URI_SEV,
    }
    for k, v in rep.items():
        HTML = HTML.replace(k, v)

    outpath = out or f'fire_spread_{FID}.html'
    open(outpath, 'w').write(HTML)
    mb = len(HTML)/1e6
    print(f'\nwrote {outpath}  ({mb:.1f} MB, self-contained)')
    if mb > 12:
        print('  -> heavy for the web. Re-run with PX = 1100 to shrink.')
    print('Self-contained: this single file is the whole map.')
    return outpath