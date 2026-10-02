// Falling and thrown objects: gravity, a floor to bounce on, and spin.
// Units are meters and seconds, so gravity is the real 9.81 m/s² and a scene
// modeled at real scale falls at a speed the eye believes.

export const GRAVITY = 9.81;

const MAX_SUBSTEP = 1 / 240;
// A rebound slower than this (m/s) would be an invisible jitter: the body rests instead.
const REST_SPEED = 0.05;

const ZERO = () => ({ x: 0, y: 0, z: 0 });

export function createBody({
  position,
  velocity = ZERO(),
  rotation = ZERO(),
  angularVelocity = ZERO(),
  restitution = 0.3, // share of vertical speed kept after a bounce
  friction = 0.5, // share of horizontal speed lost per bounce
  spinDamping = 0.5, // share of spin lost per bounce
  floorY = 0,
}) {
  return {
    position: { ...position },
    velocity: { ...velocity },
    rotation: { ...rotation },
    angularVelocity: { ...angularVelocity },
    restitution,
    friction,
    spinDamping,
    floorY,
    resting: false,
  };
}

export function stepBody(body, dt, gravity = GRAVITY) {
  if (body.resting) {
    return body;
  }

  const steps = Math.max(1, Math.ceil(dt / MAX_SUBSTEP));
  const h = dt / steps;
  const { position, velocity, rotation, angularVelocity } = body;

  for (let step = 0; step < steps; step++) {
    // Constant acceleration has an exact update, so the arc does not drift with frame rate.
    position.x += velocity.x * h;
    position.y += velocity.y * h - 0.5 * gravity * h * h;
    position.z += velocity.z * h;
    velocity.y -= gravity * h;
    rotation.x += angularVelocity.x * h;
    rotation.y += angularVelocity.y * h;
    rotation.z += angularVelocity.z * h;

    if (position.y <= body.floorY && velocity.y < 0) {
      position.y = body.floorY;
      const rebound = -velocity.y * body.restitution;
      if (rebound < REST_SPEED) {
        body.resting = true;
        body.velocity = ZERO();
        body.angularVelocity = ZERO();
        return body;
      }
      velocity.y = rebound;
      velocity.x *= 1 - body.friction;
      velocity.z *= 1 - body.friction;
      angularVelocity.x *= 1 - body.spinDamping;
      angularVelocity.y *= 1 - body.spinDamping;
      angularVelocity.z *= 1 - body.spinDamping;
    }
  }
  return body;
}

// The launch velocity that carries a body from `from` to `to` in `time` seconds.
// Throws then land in the bin on every screen size instead of being hand-tuned.
export function solveLaunchVelocity(from, to, time, gravity = GRAVITY) {
  return {
    x: (to.x - from.x) / time,
    // to.y = from.y + vy·t − ½·g·t²
    y: (to.y - from.y + 0.5 * gravity * time * time) / time,
    z: (to.z - from.z) / time,
  };
}
