// One requestAnimationFrame loop that hands every frame the elapsed time in
// seconds. Motion multiplied by dt moves at the same speed on 60 Hz and
// 120 Hz screens.
//
// dt is clamped: when a tab comes back from the background the first gap can
// be minutes long, and integrating that in one step would teleport everything.
export function createFrameLoop(
  onFrame,
  {
    maxDt = 1 / 30,
    raf = (callback) => requestAnimationFrame(callback),
    caf = (id) => cancelAnimationFrame(id),
  } = {},
) {
  let frameId = null;
  let lastTime = null;

  const loop = {
    running: false,
    start() {
      if (loop.running) return;
      loop.running = true;
      lastTime = null; // time spent stopped is not motion
      frameId = raf(tick);
    },
    stop() {
      loop.running = false;
      if (frameId !== null) caf(frameId);
      frameId = null;
    },
  };

  function tick(time) {
    frameId = null;
    const dt = lastTime === null ? 0 : Math.min((time - lastTime) / 1000, maxDt);
    lastTime = time;
    onFrame(dt, time);
    if (loop.running) frameId = raf(tick);
  }

  return loop;
}
