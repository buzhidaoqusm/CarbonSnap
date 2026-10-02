// Frame-time statistics for ?perf. It records the raw time between frames
// (the frame loop's dt is clamped and would hide a stutter) and the CPU time
// spent inside each frame.
const BUDGET_MS = 1000 / 60;

function percentile(values, fraction) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor(fraction * sorted.length))];
}

export function createPerfProbe({ capacity = 600 } = {}) {
  const intervals = [];
  const cpu = [];
  let lastTime = null;

  const push = (list, value) => {
    list.push(value);
    if (list.length > capacity) list.shift();
  };

  return {
    record(frameTime, cpuMs) {
      if (lastTime !== null) push(intervals, frameTime - lastTime);
      lastTime = frameTime;
      push(cpu, cpuMs);
    },
    // Call when the loop pauses, so the pause is not counted as one long frame.
    pause() {
      lastTime = null;
    },
    stats() {
      const round = (value) => Math.round(value * 10) / 10;
      return {
        frames: intervals.length,
        intervalP50: round(percentile(intervals, 0.5)),
        intervalP95: round(percentile(intervals, 0.95)),
        cpuP50: round(percentile(cpu, 0.5)),
        cpuP95: round(percentile(cpu, 0.95)),
        // Frames that took longer than 1.5 budgets: visible stutter.
        longFrames: intervals.filter((value) => value > BUDGET_MS * 1.5).length,
      };
    },
  };
}
