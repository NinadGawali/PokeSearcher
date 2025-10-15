// static/app.js
// Smooth movement + walk-frame cycling while moving (4 frames per direction supported)
// Added Start / Pause controls and New-grid behavior (New grid only generates; Start begins animation)

const board = document.getElementById('board');
const boardWrap = document.getElementById('board-wrap');
const btnNew = document.getElementById('btn-new');
const btnStart = document.getElementById('btn-start');
const btnPause = document.getElementById('btn-pause');
const startCoord = document.getElementById('startCoord');
const goalCoord = document.getElementById('goalCoord');
const pathLen = document.getElementById('pathLen');
const expandedEl = document.getElementById('expanded');
const delayRange = document.getElementById('delayRange');
const delayLabel = document.getElementById('delayLabel');

const totalCostEl = document.getElementById('totalCost');
const currentCostEl = document.getElementById('currentCost');
const moveNumEl = document.getElementById('moveNum');
const totalMovesEl = document.getElementById('totalMoves');

let currentData = null;
let stepDelay = parseInt(delayRange.value, 10);

// cost map consistent with backend
const COSTS = { '.': 1, '~': 3 };

// animation controller (manages play/pause/abort)
const animationController = {
  playing: false,
  paused: false,
  abort: false,
  currentFrameCycle: null,
  runnerPromise: null, // the animatePath promise when playing
};

// Update label
delayLabel.textContent = `${stepDelay}ms`;
delayRange.addEventListener('input', (e) => {
  stepDelay = parseInt(e.target.value, 10);
  delayLabel.textContent = `${stepDelay}ms`;
});

// Button bindings
btnNew.addEventListener('click', onNewGridClick);
btnStart.addEventListener('click', onStartClick);
btnPause.addEventListener('click', onPauseClick);

// initial state: fetch a grid but do NOT start animation
fetchAndRender(false);

// ------------------ UI handlers ------------------

async function onNewGridClick(){
  // abort any running animation
  stopAnimation(true);
  // fetch and render new grid (do not auto-play)
  await fetchAndRender(false);
}

function onStartClick(){
  // if no grid, fetch one first
  if(!currentData){
    fetchAndRender(true); // fetch and auto-start
    return;
  }
  // start or resume
  startAnimation();
}

function onPauseClick(){
  pauseAnimation();
}

// ------------------ fetch/render ------------------

async function fetchAndRender(autoStart = false){
  // disable buttons briefly
  btnNew.disabled = true;
  btnStart.disabled = true;
  btnPause.disabled = true;
  btnNew.textContent = 'Generating...';

  try{
    const r = await fetch('/api/new');
    if(!r.ok) throw new Error('Server error');
    const data = await r.json();
    currentData = data;
    renderGridAndStats(data);
    computeAndShowCosts(data);
    // reset controller state
    resetControllerForNewGrid();
    if(autoStart){
      startAnimation();
    } else {
      // ensure Start enabled
      btnStart.disabled = false;
      btnPause.disabled = true;
    }
  }catch(err){
    alert('Error: ' + err.message);
    console.error(err);
  }finally{
    btnNew.disabled = false;
    btnNew.textContent = 'New grid';
  }
}

function renderGridAndStats(data){
  const grid = data.grid;
  const rows = grid.rows;
  const cols = grid.cols;
  const cells = grid.cells;

  // set CSS grid template
  board.style.gridTemplateColumns = `repeat(${cols}, var(--tile-size))`;
  board.style.gridTemplateRows = `repeat(${rows}, var(--tile-size))`;
  board.innerHTML = '';

  // build tile map for quick lookup
  const pathSet = new Set((data.path || []).map(p => `${p[0]}|${p[1]}`));
  const start = data.start;
  const goal = data.goal;

  for(let r=0;r<rows;r++){
    for(let c=0;c<cols;c++){
      const posKey = `${r}|${c}`;
      const div = document.createElement('div');
      div.classList.add('tile');

      const t = cells[r][c];
      if(t === '.'){
        div.classList.add('cell-normal');
        div.dataset.tile = '.';
      }else if(t === '~'){
        div.classList.add('cell-mud');
        div.dataset.tile = '~';
      }else if(t === '#'){
        div.classList.add('cell-wall');
        div.dataset.tile = '#';
      }

      if(pathSet.has(posKey) && !(r===start[0] && c===start[1]) && !(r===goal[0] && c===goal[1])){
        div.classList.add('cell-path');
      }

      div.dataset.r = r;
      div.dataset.c = c;
      div.style.position = 'relative';
      board.appendChild(div);
    }
  }

  // stats
  startCoord.textContent = `(${start[0]}, ${start[1]})`;
  goalCoord.textContent = `(${goal[0]}, ${goal[1]})`;
  pathLen.textContent = (data.path ? data.path.length - 1 : '-') ;
  expandedEl.textContent = data.expanded || 0;

  // Add Pokéball element inside goal cell
  const goalCell = document.querySelector(`div[data-r='${goal[0]}'][data-c='${goal[1]}']`);
  if(goalCell){
    goalCell.querySelectorAll('.pokeball').forEach(n => n.remove());
    const pb = document.createElement('div');
    pb.className = 'pokeball';
    pb.style.position = 'absolute';
    pb.style.left = '50%';
    pb.style.top = '50%';
    pb.style.transform = 'translate(-50%, -50%)';
    goalCell.appendChild(pb);
  }

  // Add Ash element (single absolute element inside board)
  let ash = document.getElementById('ash-sprite');
  if(!ash){
    ash = document.createElement('div');
    ash.id = 'ash-sprite';
    ash.className = 'ash';
    ash.style.position = 'absolute';
    ash.style.zIndex = 500;
    ash.style.pointerEvents = 'none';
    board.appendChild(ash);
  }

  // set ash size relative to tile
  const tileSize = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--tile-size'));
  ash.style.width = `${tileSize * 0.9}px`;
  ash.style.height = `${tileSize * 0.9}px`;
  ash.style.backgroundSize = 'contain';
  ash.textContent = '';

  // Attempt to set initial sprite for 'down' (or fallback)
  setAshSpriteForDirection(ash, 'down');

  // position ash at start cell center
  positionAshAtCell(ash, data.start[0], data.start[1]);

  // reset info displays
  currentCostEl.textContent = '0';
  moveNumEl.textContent = '0';
  totalMovesEl.textContent = (data.path ? Math.max(0, data.path.length - 1) : 0);
}

// compute total cost for the full path and update UI
function computeAndShowCosts(data){
  if(!data || !data.path || !data.grid) return;
  const cells = data.grid.cells;
  let total = 0;
  // path is list of coords from start to goal inclusive; cost sums edges (cost of entering the tile)
  for(let i=1;i<data.path.length;i++){
    const [r,c] = data.path[i];
    const tile = cells[r][c];
    total += COSTS[tile] || 1;
  }
  totalCostEl.textContent = total.toString();
  // initialize current cost to zero
  currentCostEl.textContent = '0';
  totalMovesEl.textContent = Math.max(0, data.path.length - 1);
}

// compute board top-left and cell center coordinates (pixels)
function cellCenterPosition(r, c){
  const boardRect = board.getBoundingClientRect();
  const tileSize = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--tile-size'));
  const gap = parseFloat(getComputedStyle(board).getPropertyValue('gap')) || 4;
  // compute x/y relative to board
  const x = c * (tileSize + gap) + (tileSize/2);
  const y = r * (tileSize + gap) + (tileSize/2);
  return {x, y, boardRect};
}

// place ash element at given cell center immediately (no transition)
function positionAshAtCell(ashEl, r, c){
  const {x, y} = cellCenterPosition(r, c);
  ashEl.style.transition = 'none';
  ashEl.style.left = `${x - (ashEl.offsetWidth/2)}px`;
  ashEl.style.top = `${y - (ashEl.offsetHeight/2)}px`;
  ashEl.style.transform = 'translate(0,0)';
}

// ------------------ Animation control ------------------

function resetControllerForNewGrid(){
  animationController.playing = false;
  animationController.paused = false;
  animationController.abort = false;
  if(animationController.currentFrameCycle && animationController.currentFrameCycle.stop){
    animationController.currentFrameCycle.stop();
  }
  animationController.currentFrameCycle = null;
  animationController.runnerPromise = null;
  // UI
  btnStart.disabled = false;
  btnPause.disabled = true;
}

function stopAnimation(abort = false){
  // signal to abort animation
  animationController.abort = !!abort;
  animationController.paused = false;
  animationController.playing = false;
  if(animationController.currentFrameCycle && animationController.currentFrameCycle.stop){
    animationController.currentFrameCycle.stop();
  }
  animationController.currentFrameCycle = null;
  // UI
  btnStart.disabled = false;
  btnPause.disabled = true;
}

// Pause animation (will pause before next step, and stop frame cycling immediately)
function pauseAnimation(){
  if(!animationController.playing) return;
  animationController.paused = true;
  animationController.playing = false;
  if(animationController.currentFrameCycle && animationController.currentFrameCycle.stop){
    animationController.currentFrameCycle.stop();
  }
  animationController.currentFrameCycle = null;
  btnStart.disabled = false;
  btnPause.disabled = true;
}

// Start or resume animation
function startAnimation(){
  if(!currentData || !currentData.path) {
    // nothing to play
    return;
  }
  if(animationController.playing) return; // already playing
  // if we were paused, resume
  animationController.paused = false;
  animationController.abort = false;
  animationController.playing = true;

  btnStart.disabled = true;
  btnPause.disabled = false;

  // Launch animation runner if not already launched
  if(!animationController.runnerPromise){
    animationController.runnerPromise = animatePath(currentData.path)
      .then(() => {
        // finished naturally
        animationController.playing = false;
        animationController.paused = false;
        animationController.runnerPromise = null;
        animationController.currentFrameCycle = null;
        btnStart.disabled = false;
        btnPause.disabled = true;
      })
      .catch((err) => {
        console.error('Animation error:', err);
        animationController.playing = false;
        animationController.paused = false;
        animationController.runnerPromise = null;
        btnStart.disabled = false;
        btnPause.disabled = true;
      });
  }
}

// ------------------ Animation loop ------------------

// Animate the path: move ash along coordinates with smooth transform + frame cycling
async function animatePath(path){
  if(!path || path.length === 0) return;
  const ash = document.getElementById('ash-sprite');
  if(!ash) return;

  // ensure UI fields set
  moveNumEl.textContent = '0';
  currentCostEl.textContent = '0';

  // start by positioning ash at initial cell (instant)
  const start = path[0];
  positionAshAtCell(ash, start[0], start[1]);
  // mark start as visited
  markVisited(start[0], start[1]);

  await waitMs(80); // tiny pause before moving

  let accumulatedCost = 0;

  for(let i=1;i<path.length;i++){
    // check for abort request
    if(animationController.abort){
      break;
    }
    // if paused, wait until resumed or aborted
    while(animationController.paused && !animationController.abort){
      await waitMs(120);
    }
    if(animationController.abort) break;

    const [pr, pc] = path[i-1];
    const [r, c] = path[i];

    // determine direction
    let dir = 'down';
    if(r > pr) dir = 'down';
    else if(r < pr) dir = 'up';
    else if(c > pc) dir = 'right';
    else if(c < pc) dir = 'left';

    // set final primary frame for direction
    setAshSpriteForDirection(ash, dir);

    // compute target coordinates relative to board
    const targetPos = cellCenterPosition(r, c);

    // prepare to animate: set transition duration
    ash.style.transition = `left ${stepDelay}ms linear, top ${stepDelay}ms linear`;

    // start cycling frames while moving
    const frameCycle = startWalkCycle(ash, dir, stepDelay);
    animationController.currentFrameCycle = frameCycle;

    // set target left/top (centered)
    ash.style.left = `${targetPos.x - (ash.offsetWidth/2)}px`;
    ash.style.top = `${targetPos.y - (ash.offsetHeight/2)}px`;

    // wait for the move to finish, but if paused during movement we still let the move finish
    await waitMs(stepDelay);

    // stop cycling and ensure primary frame remains
    if(frameCycle && frameCycle.stop) frameCycle.stop();
    animationController.currentFrameCycle = null;
    setAshSpriteForDirection(ash, dir);

    // after arriving: mark visited, update costs and move counters
    markVisited(r, c);

    // compute cost of entering this tile
    const tileChar = (currentData && currentData.grid && currentData.grid.cells[r]) ? currentData.grid.cells[r][c] : '.';
    const stepCost = COSTS[tileChar] || 1;
    accumulatedCost += stepCost;
    currentCostEl.textContent = accumulatedCost.toString();

    // move number (1-based)
    moveNumEl.textContent = i.toString();

    // small settle pause
    await waitMs(30);

    // if pause requested during settle, loop will pause at top
    if(animationController.abort) break;
  }

  // finished (either completed, paused, or aborted)
  animationController.playing = false;
  animationController.currentFrameCycle = null;
  // keep paused flag as-is (if user paused explicitly), otherwise ensure buttons reflect finished state
  if(!animationController.paused){
    // natural finish or abort -> enable Start button
    btnStart.disabled = false;
    btnPause.disabled = true;
  }
}

// mark a tile as visited (turn green)
function markVisited(r, c){
  const cell = document.querySelector(`div[data-r='${r}'][data-c='${c}']`);
  if(cell){
    cell.classList.add('cell-visited');
    cell.classList.remove('cell-path');
  }
}

// ------------------ sprite/frame helpers (unchanged) ------------------

// startWalkCycle: repeatedly cycles available frames for `dir` during movement; returns controller with stop()
function startWalkCycle(ashEl, dir, totalMs){
  const frames = [];
  const maxFrames = 4;
  let isStopped = false;
  let intervalId = null;

  (async () => {
    for(let i=0;i<maxFrames;i++){
      const url = `/static/sprites/ash_${dir}_${i}.png`;
      try{
        await imageExists(url);
        frames.push(url);
      }catch(e){
        // skip missing frames
      }
    }
    if(frames.length === 0){
      return;
    }
    const perFrameDelay = Math.max(60, Math.floor(totalMs / (frames.length * 1.0)));
    let idx = 0;
    ashEl.style.backgroundImage = `url('${frames[0]}')`;
    intervalId = setInterval(() => {
      if(isStopped) return;
      idx = (idx + 1) % frames.length;
      ashEl.style.backgroundImage = `url('${frames[idx]}')`;
    }, perFrameDelay);
  })();

  return {
    stop: () => {
      isStopped = true;
      if(intervalId) clearInterval(intervalId);
    }
  };
}

// set Ash sprite base image or directional fallback: prefer ash_<dir>_0.png then ash.png then block fallback
function setAshSpriteForDirection(ashEl, dir){
  const primary = `/static/sprites/ash_${dir}_0.png`;
  const singleFallback = `/static/sprites/ash.png`;

  imageExists(primary)
    .then(() => {
      ashEl.style.backgroundImage = `url('${primary}')`;
      ashEl.style.backgroundSize = 'contain';
      ashEl.textContent = '';
    })
    .catch(async () => {
      try{
        await imageExists(singleFallback);
        ashEl.style.backgroundImage = `url('${singleFallback}')`;
        ashEl.style.backgroundSize = 'contain';
        ashEl.textContent = '';
      }catch(e){
        ashEl.style.backgroundImage = '';
        ashEl.style.background = 'linear-gradient(180deg,#fff,#f0f0f0)';
        ashEl.textContent = 'A';
        ashEl.style.color = '#0b2140';
        ashEl.style.textAlign = 'center';
        ashEl.style.fontWeight = '800';
      }
    });
}

// tiny utility to check if an image URL loads
function imageExists(url){
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => reject(false);
    img.src = url + '?_=' + Math.random().toString(36).slice(2,8);
  });
}

function waitMs(ms){
  return new Promise((res) => setTimeout(res, ms));
}
