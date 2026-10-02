import { Vector3 } from "three";

const scratch = new Vector3();

// Up to maxPoints world-space points spread over an object's meshes. Projecting
// these fits a focus box to the object itself; the 8 corners of an axis-aligned
// bounding box would leave a tilted bottle swimming in empty space.
export function samplePoints(object, maxPoints = 96) {
  object.updateWorldMatrix(true, true);
  const all = [];
  object.traverse((child) => {
    const position = child.isMesh ? child.geometry?.attributes?.position : null;
    if (!position) return;
    for (let index = 0; index < position.count; index++) {
      all.push(new Vector3().fromBufferAttribute(position, index).applyMatrix4(child.matrixWorld));
    }
  });
  if (all.length <= maxPoints) return all;
  const stride = all.length / maxPoints;
  return Array.from({ length: maxPoints }, (_, index) => all[Math.floor(index * stride)]);
}

// The screen rectangle (CSS pixels, origin top-left) covering the points as the
// camera sees them.
export function projectPoints(points, camera, width, height) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const point of points) {
    scratch.copy(point).project(camera); // to normalized device coordinates, -1..1
    const x = ((scratch.x + 1) / 2) * width;
    const y = ((1 - scratch.y) / 2) * height;
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  }
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}
