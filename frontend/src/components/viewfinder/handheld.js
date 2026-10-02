// The slight drift of a camera held in a hand. Each axis sums two sines whose
// frequencies have no common period, so the motion stays smooth but never
// visibly loops. Angles are in radians (0.0035 rad is about 0.2°),
// translations in meters.
export function handheldOffset(time, amplitude = 1) {
  const s = Math.sin;
  return {
    pitch: amplitude * (0.0022 * s(time * 0.83 + 0.4) + 0.0009 * s(time * 2.11 + 1.3)),
    yaw: amplitude * (0.0026 * s(time * 0.61 + 2.1) + 0.0008 * s(time * 1.87)),
    roll: amplitude * (0.0012 * s(time * 0.47 + 0.9) + 0.0004 * s(time * 1.53 + 2.6)),
    x: amplitude * (0.0015 * s(time * 0.71 + 1.1) + 0.0005 * s(time * 1.97 + 0.2)),
    y: amplitude * (0.0012 * s(time * 0.93 + 2.4) + 0.0004 * s(time * 2.37 + 1.7)),
  };
}

export const HANDHELD_LIMITS = Object.freeze({ pitch: 0.0031, yaw: 0.0034, roll: 0.0016, x: 0.002, y: 0.0016 });
