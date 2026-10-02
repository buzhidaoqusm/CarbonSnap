// What the viewfinder recognizes. The numbers are the ones the backend would
// produce, not decoration:
// - factor: kg CO2e saved per kg recycled, from DEFAULT_EMISSION_FACTORS in
//   backend/app/core/config.py
// - carbon: recycling_analysis_service computes co2 = round(weight × factor, 2)
//   and the audit awards round(co2 × 100) points.
// The PET bottle's weight and confidence are the AI's actual answer in the
// seeded record plastic-bottle-real-chat-record-01; the other weights are
// typical for the item.
export const VIEWFINDER_ITEMS = Object.freeze([
  { id: "pet", material: "pet", nameKey: "viewfinder.itemPet", weightKg: 0.05, factor: 1.5, confidence: 0.95 },
  { id: "can", material: "aluminum", nameKey: "viewfinder.itemCan", weightKg: 0.016, factor: 2.5 },
  { id: "box", material: "fiber", nameKey: "viewfinder.itemBox", weightKg: 0.12, factor: 0.8 },
  { id: "glass", material: "glass", nameKey: "viewfinder.itemGlass", weightKg: 0.2, factor: 0.5 },
]);

export function carbonFor(item) {
  const co2Kg = Math.round(item.weightKg * item.factor * 100) / 100;
  return { co2Kg, points: Math.round(co2Kg * 100) };
}
