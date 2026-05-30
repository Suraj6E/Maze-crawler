"""Build a self-contained HTML replay viewer for a Maze Crawler (`crawl`) match.

The renderer is adapted from the one bundled in kaggle-environments
(kaggle_environments/envs/crawl/crawl.js), with two extra controls the bundled
one lacks:

  * Theme toggle ............ light  or  dark
  * View toggle ............. All / P1 / P2  (per-player fog of war)

plus playback (slider, play/pause, step buttons, speed, keyboard).

`write_viewer(env, out_path)` writes one standalone .html file — open it in any
browser; no server needed.
"""

import json
from pathlib import Path

_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Maze Crawler — Replay</title>
<style>
  :root { color-scheme: light dark; }
  body { margin: 0; font-family: system-ui, sans-serif; background: var(--page); color: var(--fg);
         display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 16px; }
  body.dark  { --page:#13131f; --fg:#e8e8f0; --panel:#20203a; --btn:#2d2d4d; --btnfg:#e8e8f0; --accent:#4d7dff; }
  body.light { --page:#f2f3f5; --fg:#1c1c22; --panel:#ffffff; --btn:#e3e6ea; --btnfg:#1c1c22; --accent:#2563eb; }
  #title { font-weight: 700; font-size: 18px; }
  canvas { background: var(--panel); border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.18); }
  .controls { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; background: var(--panel);
              padding: 10px 14px; border-radius: 8px; box-shadow: 0 1px 6px rgba(0,0,0,0.12); }
  button { background: var(--btn); color: var(--btnfg); border: none; border-radius: 6px;
           padding: 6px 10px; font-size: 13px; cursor: pointer; }
  button:hover { filter: brightness(1.08); }
  button.active { background: var(--accent); color: #fff; }
  .group { display: flex; gap: 4px; align-items: center; }
  .label { font-size: 12px; opacity: 0.7; }
  input[type=range] { width: 320px; accent-color: var(--accent); }
  #stepReadout { font-variant-numeric: tabular-nums; min-width: 92px; font-size: 13px; }
</style>
</head>
<body class="dark">
  <div id="title">Maze Crawler — Replay</div>
  <canvas id="board" width="760" height="680"></canvas>
  <div class="controls">
    <div class="group">
      <button id="first" title="First (Home)">⏮</button>
      <button id="prev"  title="Prev (←)">◀</button>
      <button id="play"  title="Play/Pause (Space)">▶</button>
      <button id="next"  title="Next (→)">▶</button>
      <button id="last"  title="Last (End)">⏭</button>
    </div>
    <input type="range" id="slider" min="0" value="0">
    <span id="stepReadout">0 / 0</span>
    <div class="group">
      <span class="label">Speed</span>
      <button class="spd" data-spd="500">0.5x</button>
      <button class="spd active" data-spd="200">1x</button>
      <button class="spd" data-spd="80">3x</button>
      <button class="spd" data-spd="30">8x</button>
    </div>
    <div class="group">
      <span class="label">View</span>
      <button class="view active" data-view="all">All</button>
      <button class="view" data-view="p1">P1</button>
      <button class="view" data-view="p2">P2</button>
    </div>
    <div class="group">
      <span class="label">Theme</span>
      <button id="theme">Light</button>
    </div>
  </div>

<script>
const ENV = /*__DATA__*/;
const CANVAS_W = /*__W__*/, CANVAS_H = /*__H__*/;

// ---- palettes -------------------------------------------------------------
const THEMES = {
  dark:  { bg:'#20203a', cellBg:'rgba(255,255,255,0.03)', wall:'#556677',
           divider:'rgba(255,255,255,0.10)', text:'#aab', rowLabel:'#889',
           fog:'rgba(0,0,0,0.60)', fogStrong:'rgba(0,0,0,0.84)', bar:'#333' },
  light: { bg:'#ffffff', cellBg:'rgba(0,0,0,0.025)', wall:'#8595a4',
           divider:'rgba(0,0,0,0.10)', text:'#556', rowLabel:'#99a',
           fog:'rgba(120,124,140,0.45)', fogStrong:'rgba(96,100,116,0.86)', bar:'#ccc' },
};
const PLAYER_COLORS = ['#2196F3', '#F44336'];
const PLAYER_COLORS_LIGHT = ['rgba(33,150,243,0.20)', 'rgba(244,67,54,0.20)'];
const TYPE_LABELS = {0:'F',1:'S',2:'W',3:'M'};
const WALL_N=1, WALL_E=2, WALL_S=4, WALL_W=8;
const FACTORY=0, SCOUT=1, WORKER=2, MINER=3;

function isFixedWall(col, dir, w){ const half=(w/2)|0;
  if(dir==='W'&&col===0)return true; if(dir==='E'&&col===w-1)return true;
  if(dir==='E'&&col===half-1)return true; if(dir==='W'&&col===half)return true; return false; }
function dblLine(c,x1,y1,x2,y2){ const dx=x2-x1,dy=y2-y1,len=Math.sqrt(dx*dx+dy*dy); if(!len)return;
  const nx=-dy/len*1.5, ny=dx/len*1.5; c.beginPath();
  c.moveTo(x1+nx,y1+ny); c.lineTo(x2+nx,y2+ny); c.moveTo(x1-nx,y1-ny); c.lineTo(x2-nx,y2-ny); c.stroke(); }

// ---- renderer (adapted from crawl.js, + theme + viewMode) -----------------
function renderStep(stepIdx, theme, viewMode){
  const T = THEMES[theme];
  const canvas = document.getElementById('board');
  const c = canvas.getContext('2d');
  const cur = ENV.steps[stepIdx];
  if(!cur || !cur[0]) return;
  const obs = cur[0].observation, config = ENV.configuration;
  const gridWidth = config.width || 20;
  const southBound = obs.southBound || 0;
  const northBound = obs.northBound || 19;
  const windowHeight = northBound - southBound + 1;
  const gWalls=obs.globalWalls||{}, gCry=obs.globalCrystals||{}, gRob=obs.globalRobots||{},
        gMine=obs.globalMines||{}, gNode=obs.globalMiningNodes||{};
  const VISION = {0:config.visionFactory||4, 1:config.visionScout||5, 2:config.visionWorker||3, 3:config.visionMiner||3};

  const robots=[]; for(const uid in gRob){ const d=gRob[uid]; robots.push({type:d[0],col:d[1],row:d[2],energy:d[3],owner:d[4]}); }
  const visible=[{},{}];
  for(const r of robots){ const rng=VISION[r.type]||3;
    for(let dc=-rng;dc<=rng;dc++) for(let dr=-rng;dr<=rng;dr++)
      if(Math.abs(dc)+Math.abs(dr)<=rng){ const vc=r.col+dc; if(vc>=0&&vc<gridWidth) visible[r.owner][vc+','+(r.row+dr)]=true; } }

  // viewMode -> which owner's eyes we look through (null = all)
  const eye = viewMode==='p1' ? 0 : viewMode==='p2' ? 1 : null;
  const sees = (col,row)=> eye===null ? (visible[0][col+','+row]||visible[1][col+','+row]) : visible[eye][col+','+row];

  const mines={}; for(const k in gMine){ const m=gMine[k]; mines[k]={energy:m[0],maxEnergy:m[1],owner:m[2]}; }
  const totalE=[0,0], counts=[{F:0,S:0,W:0,M:0},{F:0,S:0,W:0,M:0}];
  for(const r of robots){ totalE[r.owner]+=r.energy; counts[r.owner][TYPE_LABELS[r.type]]++; }

  canvas.width=CANVAS_W; canvas.height=CANVAS_H;
  const headerH=30, statusH=20, cw=CANVAS_W, ch=CANVAS_H-headerH-statusH;
  const cellSize=Math.min(cw/gridWidth, ch/windowHeight);
  const gridW=cellSize*gridWidth, gridH=cellSize*windowHeight;
  const offX=(cw-gridW)/2, offY=headerH+(ch-gridH)/2;
  const toXY=(col,row)=>({x:offX+col*cellSize, y:offY+(northBound-row)*cellSize});

  c.fillStyle=T.bg; c.fillRect(0,0,canvas.width,canvas.height);

  // header
  c.font='bold 12px sans-serif'; c.textBaseline='top';
  const hdr=p=>'P'+(p+1)+': E='+totalE[p]+' F:'+counts[p].F+' S:'+counts[p].S+' W:'+counts[p].W+' M:'+counts[p].M;
  c.fillStyle=PLAYER_COLORS[0]; c.textAlign='left';  c.globalAlpha=(eye===1?0.35:1); c.fillText(hdr(0),8,8);
  c.fillStyle=PLAYER_COLORS[1]; c.textAlign='right'; c.globalAlpha=(eye===0?0.35:1); c.fillText(hdr(1),canvas.width-8,8);
  c.globalAlpha=1;

  // cells + walls
  for(let row=southBound;row<=northBound;row++){ const rw=gWalls[String(row)];
    for(let col=0;col<gridWidth;col++){ const p=toXY(col,row), w=rw?rw[col]:0;
      c.fillStyle=T.cellBg; c.fillRect(p.x+0.5,p.y+0.5,cellSize-1,cellSize-1);
      c.strokeStyle=T.wall; c.lineWidth=2;
      if(w&WALL_N){ c.beginPath(); c.moveTo(p.x,p.y); c.lineTo(p.x+cellSize,p.y); c.stroke(); }
      if(w&WALL_S){ c.beginPath(); c.moveTo(p.x,p.y+cellSize); c.lineTo(p.x+cellSize,p.y+cellSize); c.stroke(); }
      if(w&WALL_E){ if(isFixedWall(col,'E',gridWidth)) dblLine(c,p.x+cellSize,p.y,p.x+cellSize,p.y+cellSize);
                    else { c.beginPath(); c.moveTo(p.x+cellSize,p.y); c.lineTo(p.x+cellSize,p.y+cellSize); c.stroke(); } }
      if(w&WALL_W){ if(isFixedWall(col,'W',gridWidth)) dblLine(c,p.x,p.y,p.x,p.y+cellSize);
                    else { c.beginPath(); c.moveTo(p.x,p.y); c.lineTo(p.x,p.y+cellSize); c.stroke(); } }
    } }

  // center divider
  const divX=offX+(gridWidth/2)*cellSize; c.strokeStyle=T.divider; c.lineWidth=1; c.setLineDash([4,4]);
  c.beginPath(); c.moveTo(divX,offY); c.lineTo(divX,offY+gridH); c.stroke(); c.setLineDash([]);

  // mining nodes (not remembered -> hidden outside the viewed player's sight)
  for(const k in gNode){ const [col,row]=k.split(',').map(Number); if(row<southBound||row>northBound) continue;
    if(eye!==null && !sees(col,row)) continue;
    const p=toXY(col,row), cx=p.x+cellSize/2, cy=p.y+cellSize/2, r=cellSize*0.2;
    c.fillStyle='rgba(205,133,63,0.15)'; c.fillRect(p.x+1,p.y+1,cellSize-2,cellSize-2);
    c.strokeStyle='#CD853F'; c.lineWidth=Math.max(1.5,cellSize*0.06);
    c.beginPath(); c.moveTo(cx,cy-r); c.lineTo(cx+r,cy); c.lineTo(cx,cy+r); c.lineTo(cx-r,cy); c.closePath(); c.stroke();
    c.fillStyle='#CD853F'; c.beginPath(); c.arc(cx,cy,cellSize*0.06,0,7); c.fill(); }

  // crystals (not remembered)
  for(const k in gCry){ const [col,row]=k.split(',').map(Number); if(row<southBound||row>northBound) continue;
    if(eye!==null && !sees(col,row)) continue;
    const p=toXY(col,row), cx=p.x+cellSize/2, cy=p.y+cellSize/2, r=cellSize*0.18;
    c.fillStyle='rgba(255,215,0,0.7)'; c.strokeStyle='#FFD700'; c.lineWidth=1;
    c.beginPath(); c.moveTo(cx,cy-r*1.2); c.lineTo(cx+r,cy); c.lineTo(cx,cy+r*0.8); c.lineTo(cx-r,cy); c.closePath(); c.fill(); c.stroke();
    if(cellSize>16){ c.fillStyle='#FFD700'; c.font=Math.max(7,cellSize*0.22)+'px sans-serif';
      c.textAlign='center'; c.textBaseline='middle'; c.fillText(String(gCry[k]),cx,cy+r*1.5); } }

  // mines (remembered -> always shown)
  for(const k in mines){ const [col,row]=k.split(',').map(Number); if(row<southBound||row>northBound) continue;
    const p=toXY(col,row), m=mines[k], cx=p.x+cellSize/2, cy=p.y+cellSize/2, r=cellSize*0.25, col2=PLAYER_COLORS[m.owner];
    c.fillStyle=col2; c.globalAlpha=0.4; c.beginPath(); c.moveTo(cx,cy-r); c.lineTo(cx+r,cy+r*0.7); c.lineTo(cx-r,cy+r*0.7); c.closePath(); c.fill();
    c.globalAlpha=1; c.strokeStyle=col2; c.lineWidth=1.5; c.stroke();
    const pct=m.maxEnergy>0?m.energy/m.maxEnergy:0, bw=cellSize*0.5, bh=Math.max(2,cellSize*0.06);
    c.fillStyle=T.bar; c.fillRect(cx-bw/2,p.y+cellSize-bh-1,bw,bh); c.fillStyle='#FFD700'; c.fillRect(cx-bw/2,p.y+cellSize-bh-1,bw*pct,bh); }

  // robots (factories drawn last so they sit on top); hide enemies the eye can't see
  const sorted=robots.slice().sort((a,b)=> (a.type===FACTORY)-(b.type===FACTORY));
  for(const r of sorted){ if(r.row<southBound||r.row>northBound) continue;
    if(eye!==null && r.owner!==eye && !sees(r.col,r.row)) continue;   // own robots always visible
    const p=toXY(r.col,r.row), color=PLAYER_COLORS[r.owner], light=PLAYER_COLORS_LIGHT[r.owner];
    const cx=p.x+cellSize/2, cy=p.y+cellSize/2, rr=cellSize*0.35;
    c.fillStyle=light; c.strokeStyle=color; c.lineWidth=2;
    if(r.type===FACTORY){ const s=cellSize*0.6; c.fillRect(cx-s/2,cy-s/2,s,s); c.strokeRect(cx-s/2,cy-s/2,s,s);
      const n=s*0.15; c.fillStyle=color; c.fillRect(cx-n,cy-s/2-n,n*2,n); c.fillRect(cx-n,cy+s/2,n*2,n); c.fillRect(cx-s/2-n,cy-n,n,n*2); c.fillRect(cx+s/2,cy-n,n,n*2); }
    else if(r.type===SCOUT){ c.lineWidth=1.5; c.beginPath(); c.moveTo(cx,cy-rr); c.lineTo(cx+rr,cy); c.lineTo(cx,cy+rr); c.lineTo(cx-rr,cy); c.closePath(); c.fill(); c.stroke(); }
    else if(r.type===WORKER){ c.lineWidth=1.5; c.beginPath(); for(let h=0;h<6;h++){ const a=Math.PI/3*h-Math.PI/6, px=cx+rr*Math.cos(a), py=cy+rr*Math.sin(a); h?c.lineTo(px,py):c.moveTo(px,py); } c.closePath(); c.fill(); c.stroke(); }
    else { c.lineWidth=1.5; c.beginPath(); c.arc(cx,cy,rr,0,7); c.closePath(); c.fill(); c.stroke(); }
    c.fillStyle=color; c.font='bold '+Math.max(10,cellSize*0.35)+'px sans-serif'; c.textAlign='center'; c.textBaseline='middle'; c.fillText(TYPE_LABELS[r.type],cx,cy);
    const bw=cellSize*0.7, bh=Math.max(2,cellSize*0.08), maxE=r.type===FACTORY?1000:r.type===SCOUT?50:r.type===WORKER?200:300, pct=Math.min(1,r.energy/maxE);
    c.fillStyle=T.bar; c.fillRect(cx-bw/2,p.y+cellSize-bh-1,bw,bh);
    c.fillStyle=pct>0.3?'#4CAF50':pct>0.1?'#FF9800':'#F44336'; c.fillRect(cx-bw/2,p.y+cellSize-bh-1,bw*pct,bh); }

  // fog of war overlay
  for(let row=southBound;row<=northBound;row++) for(let col=0;col<gridWidth;col++){
    const p0=visible[0][col+','+row], p1=visible[1][col+','+row], p=toXY(col,row);
    if(eye!==null){                                  // single-player view
      if(!sees(col,row)){ c.fillStyle=T.fogStrong; c.fillRect(p.x,p.y,cellSize,cellSize); }
    } else {                                         // combined view
      if(!p0&&!p1){ c.fillStyle=T.fog; c.fillRect(p.x,p.y,cellSize,cellSize); }
      else if(p0&&!p1){ c.fillStyle='rgba(33,150,243,0.08)'; c.fillRect(p.x,p.y,cellSize,cellSize); }
      else if(!p0&&p1){ c.fillStyle='rgba(244,67,54,0.08)'; c.fillRect(p.x,p.y,cellSize,cellSize); }
    } }

  // scroll boundary
  const by=offY+gridH-cellSize; c.fillStyle='rgba(244,67,54,0.12)'; c.fillRect(offX,by,gridW,cellSize);
  c.strokeStyle='rgba(244,67,54,0.5)'; c.lineWidth=2; c.setLineDash([6,3]); c.beginPath(); c.moveTo(offX,by); c.lineTo(offX+gridW,by); c.stroke(); c.setLineDash([]);

  // row labels
  c.fillStyle=T.rowLabel; c.font=Math.max(8,cellSize*0.25)+'px sans-serif'; c.textAlign='right'; c.textBaseline='middle';
  const ls=Math.max(1,Math.floor(windowHeight/10));
  for(let lr=southBound;lr<=northBound;lr+=ls){ const lp=toXY(0,lr); c.fillText(String(lr),offX-4,lp.y+cellSize/2); }

  // status
  const over=cur.every(s=>s.status==='DONE'); c.font='11px sans-serif'; c.textBaseline='bottom'; c.fillStyle=T.text; c.textAlign='center';
  let txt='Step '+(obs.step||stepIdx)+'  |  Scroll: '+southBound+'-'+northBound+'  |  View: '+(viewMode==='all'?'All':viewMode.toUpperCase());
  if(over){ const r0=cur[0].reward, r1=cur[1].reward; let res='Draw'; if(r0!=null&&r1!=null){ if(r0>r1)res='P1 wins!'; else if(r1>r0)res='P2 wins!'; } txt=res+'  |  '+txt; }
  else { txt+='  |  Mines: '+Object.keys(mines).length+'  |  Crystals: '+Object.keys(gCry).length; }
  c.fillText(txt,canvas.width/2,canvas.height-4);
}

// ---- controller -----------------------------------------------------------
const nSteps = ENV.steps.length;
let cur=0, playing=false, speed=200, theme='dark', viewMode='all', timer=null;
const $=id=>document.getElementById(id);
const slider=$('slider'); slider.max=nSteps-1;

function draw(){ renderStep(cur, theme, viewMode); slider.value=cur; $('stepReadout').textContent=cur+' / '+(nSteps-1); }
function go(i){ cur=Math.max(0,Math.min(nSteps-1,i)); draw(); }
function setPlaying(p){ playing=p; $('play').textContent=playing?'⏸':'▶';
  if(timer){clearInterval(timer); timer=null;}
  if(playing) timer=setInterval(()=>{ if(cur>=nSteps-1){setPlaying(false);return;} go(cur+1); }, speed); }

$('first').onclick=()=>go(0); $('last').onclick=()=>go(nSteps-1);
$('prev').onclick=()=>{setPlaying(false);go(cur-1);}; $('next').onclick=()=>{setPlaying(false);go(cur+1);};
$('play').onclick=()=>setPlaying(!playing);
slider.oninput=e=>{setPlaying(false);go(+e.target.value);};
document.querySelectorAll('.spd').forEach(b=>b.onclick=()=>{ speed=+b.dataset.spd;
  document.querySelectorAll('.spd').forEach(x=>x.classList.remove('active')); b.classList.add('active'); if(playing)setPlaying(true); });
document.querySelectorAll('.view').forEach(b=>b.onclick=()=>{ viewMode=b.dataset.view;
  document.querySelectorAll('.view').forEach(x=>x.classList.remove('active')); b.classList.add('active'); draw(); });
$('theme').onclick=()=>{ theme=theme==='dark'?'light':'dark'; document.body.className=theme; $('theme').textContent=theme==='dark'?'Light':'Dark'; draw(); };
document.addEventListener('keydown',e=>{ if(e.key==='ArrowLeft'){setPlaying(false);go(cur-1);}
  else if(e.key==='ArrowRight'){setPlaying(false);go(cur+1);} else if(e.key===' '){e.preventDefault();setPlaying(!playing);}
  else if(e.key==='Home')go(0); else if(e.key==='End')go(nSteps-1); });

draw();
</script>
</body>
</html>
"""


def write_viewer(env, out_path, width=760, height=680):
    """Render `env` (a finished kaggle-environments match) to a standalone HTML viewer."""
    data = env.toJSON()
    payload = {"steps": data["steps"], "configuration": data["configuration"]}
    html = (
        _TEMPLATE
        .replace("/*__DATA__*/", json.dumps(payload, default=str, separators=(",", ":")))
        .replace("/*__W__*/", str(width))
        .replace("/*__H__*/", str(height))
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
