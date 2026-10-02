// Procedural models at real scale, in meters. A bottle or a can is a profile
// (radius, height) spun around the vertical axis, like wood on a lathe.
import {
  BoxGeometry,
  CylinderGeometry,
  DoubleSide,
  Group,
  LatheGeometry,
  Mesh,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  SplineCurve,
  Vector2,
} from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

const LATHE_SEGMENTS = 72;

// Smooth a hand-written profile into a curve; the lathe needs r >= 0.
function lathe(profile, divisions = 160) {
  const curve = new SplineCurve(profile.map(([r, y]) => new Vector2(r, y)));
  const points = curve.getPoints(divisions).map((p) => new Vector2(Math.max(p.x, 0), p.y));
  return new LatheGeometry(points, LATHE_SEGMENTS);
}

function withShadows(object) {
  object.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = true;
      child.receiveShadow = true;
    }
  });
  return object;
}

// 500 ml PET water bottle: 205 mm tall, 65 mm across.
export function createPetBottle(textures) {
  const group = new Group();
  group.name = "pet";
  const body = new Mesh(
    lathe([
      [0, 0.001],
      [0.022, 0],
      [0.03, 0.004],
      [0.0325, 0.014],
      [0.0325, 0.05],
      [0.0308, 0.056], // grip grooves
      [0.0325, 0.062],
      [0.0325, 0.13],
      [0.0305, 0.145],
      [0.024, 0.16],
      [0.0165, 0.172],
      [0.0135, 0.18],
      [0.0135, 0.191],
    ]),
    new MeshPhysicalMaterial({
      color: "#ffffff",
      roughness: 0.04,
      transmission: 1,
      thickness: 0.012, // thin wall: little bending of what is behind
      ior: 1.57, // PET
      attenuationColor: "#d4e4ee", // the faint blue-grey of clear PET
      attenuationDistance: 0.25,
      specularIntensity: 1,
      envMapIntensity: 1.4,
    }),
  );
  const label = new Mesh(
    new CylinderGeometry(0.0329, 0.0329, 0.05, LATHE_SEGMENTS, 1, true),
    new MeshStandardMaterial({ map: textures.petLabel, roughness: 0.5, side: DoubleSide }),
  );
  label.position.y = 0.095;
  const cap = new Mesh(
    new CylinderGeometry(0.0146, 0.015, 0.017, 40),
    new MeshStandardMaterial({ color: "#1f63c7", roughness: 0.42 }),
  );
  cap.position.y = 0.199;
  group.add(body, label, cap);
  return withShadows(group);
}

// 330 ml aluminum can: 115 mm tall, 66 mm across, printed sleeve on bare metal.
export function createCan(textures) {
  const group = new Group();
  group.name = "can";
  const metal = new MeshStandardMaterial({ color: "#d8dce0", metalness: 1, roughness: 0.27 });
  const shell = new Mesh(
    lathe([
      [0, 0.004],
      [0.024, 0.0005],
      [0.0295, 0.003],
      [0.0325, 0.01],
      [0.033, 0.016],
      [0.033, 0.098],
      [0.031, 0.107],
      [0.0275, 0.1125],
      [0.027, 0.115],
      [0.025, 0.1135],
      [0, 0.1132],
    ]),
    metal,
  );
  const sleeve = new Mesh(
    new CylinderGeometry(0.0332, 0.0332, 0.08, LATHE_SEGMENTS, 1, true),
    new MeshPhysicalMaterial({
      map: textures.canPrint,
      // Paint over metal still catches some light; more than this and the
      // print mirrors the dark studio and turns muddy.
      metalness: 0.3,
      roughness: 0.32,
      clearcoat: 1,
      clearcoatRoughness: 0.12,
    }),
  );
  sleeve.position.y = 0.057;
  const tab = new Mesh(new RoundedBoxGeometry(0.018, 0.0015, 0.01, 2, 0.0007), metal);
  tab.position.set(0.004, 0.1142, 0);
  group.add(shell, sleeve, tab);
  return withShadows(group);
}

// A small shipping box, taped shut.
export function createBox(textures) {
  const group = new Group();
  group.name = "box";
  const width = 0.13;
  const height = 0.085;
  const depth = 0.095;
  const board = new Mesh(
    new RoundedBoxGeometry(width, height, depth, 3, 0.004),
    new MeshStandardMaterial({ map: textures.kraft, roughness: 0.88 }),
  );
  board.position.y = height / 2;
  const tapeMaterial = new MeshPhysicalMaterial({
    color: "#cfa874",
    roughness: 0.22,
    clearcoat: 0.6,
    transparent: true,
    opacity: 0.88,
  });
  const top = new Mesh(new BoxGeometry(width + 0.001, 0.0008, 0.034), tapeMaterial);
  top.position.y = height + 0.0004;
  const left = new Mesh(new BoxGeometry(0.0008, 0.035, 0.034), tapeMaterial);
  left.position.set(-width / 2 - 0.0004, height - 0.0175, 0);
  const right = left.clone();
  right.position.x = width / 2 + 0.0004;
  group.add(board, top, left, right);
  return withShadows(group);
}

// 330 ml green glass bottle, 230 mm tall.
export function createGlassBottle(textures) {
  const group = new Group();
  group.name = "glass";
  const body = new Mesh(
    lathe([
      [0, 0.003],
      [0.025, 0],
      [0.0295, 0.004],
      [0.0302, 0.014],
      [0.0302, 0.132],
      [0.0285, 0.148],
      [0.021, 0.168],
      [0.0138, 0.184],
      [0.0127, 0.213],
      [0.0146, 0.218],
      [0.0146, 0.226],
      [0.0118, 0.2295],
      [0, 0.229],
    ]),
    new MeshPhysicalMaterial({
      color: "#b7e0c2",
      roughness: 0.03,
      transmission: 1,
      thickness: 0.012,
      ior: 1.52, // soda-lime glass
      attenuationColor: "#1f7a4d", // thicker glass looks greener
      attenuationDistance: 0.03,
      specularIntensity: 1,
      envMapIntensity: 1.4,
    }),
  );
  const label = new Mesh(
    new CylinderGeometry(0.0306, 0.0306, 0.062, LATHE_SEGMENTS, 1, true),
    new MeshStandardMaterial({ map: textures.glassLabel, roughness: 0.75, side: DoubleSide }),
  );
  label.position.y = 0.072;
  group.add(body, label);
  return withShadows(group);
}

export const MODEL_BUILDERS = { pet: createPetBottle, can: createCan, box: createBox, glass: createGlassBottle };
