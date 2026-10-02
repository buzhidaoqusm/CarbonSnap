// Damped springs. One force pulls the value toward its target (stiffness),
// another resists its velocity (damping). Unlike a fixed duration with an
// easing curve, a spring keeps its velocity when the target changes
// mid-flight, so interrupted motion never jumps.
//
// Damping ratio  ζ = damping / (2 · √(stiffness · mass)):
//   ζ = 1  critically damped: the fastest approach that does not overshoot
//   ζ < 1  overshoots and oscillates before it settles

// ζ = 1. Panels, menus, sheets: things that should arrive, not bounce.
export const SPRING_UI = Object.freeze({ stiffness: 400, damping: 40, mass: 1 });
// ζ ≈ 0.55, about 13% overshoot. Only for "it landed": points added, audit passed.
export const SPRING_LAND = Object.freeze({ stiffness: 300, damping: 19, mass: 1 });

// Small fixed substeps keep the integration accurate at any frame rate.
const MAX_SUBSTEP = 1 / 240;
// After a gap this long (a background tab), the motion is long over: land on the target.
const SETTLE_AFTER = 1;

export function dampingRatio({ stiffness, damping, mass = 1 }) {
  return damping / (2 * Math.sqrt(stiffness * mass));
}

export function createSpring(value = 0, config = SPRING_UI) {
  return { value, velocity: 0, target: value, config };
}

export function stepSpring(spring, dt) {
  if (dt >= SETTLE_AFTER) {
    spring.value = spring.target;
    spring.velocity = 0;
    return spring;
  }

  const { stiffness, damping, mass = 1 } = spring.config;
  const steps = Math.max(1, Math.ceil(dt / MAX_SUBSTEP));
  const h = dt / steps;
  for (let step = 0; step < steps; step++) {
    // Semi-implicit Euler: velocity from the force first, then position from the new velocity.
    const force = -stiffness * (spring.value - spring.target) - damping * spring.velocity;
    spring.velocity += (force / mass) * h;
    spring.value += spring.velocity * h;
  }
  return spring;
}

export function isAtRest(spring, epsilon = 1e-3) {
  return Math.abs(spring.value - spring.target) < epsilon && Math.abs(spring.velocity) < epsilon;
}
