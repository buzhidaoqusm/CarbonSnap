import aluminumCanAsset from "../../assets/landing/user-aluminum-can.png";
import cameraFrameAsset from "../../assets/landing/user-camera-frame.png";
import cardboardBoxAsset from "../../assets/landing/user-cardboard-box.png";
import glassBottleAsset from "../../assets/landing/user-glass-bottle.png";
import heroBackgroundAsset from "../../assets/landing/user-hero-background.png";
import plasticBottleAsset from "../../assets/landing/user-plastic-bottle.png";
import recycleBinBaseAsset from "../../assets/landing/user-recycle-bin-base.png";
import recycleBinFrontAsset from "../../assets/landing/user-recycle-bin-front.png";

export { cameraFrameAsset, heroBackgroundAsset, recycleBinBaseAsset, recycleBinFrontAsset };

export function getWasteItems(t) {
  return [
  {
    id: "plastic",
    name: t("home.itemPlasticBottle"),
    material: "PET",
    weight: "25g",
    carbonSaved: "0.08 kg",
    cardValue: "-0.08 kg CO2e",
    points: "+8 pts",
    asset: plasticBottleAsset,
    objectClass: "waste-object--plastic",
    cardClass: "capture-card--plastic",
  },
  {
    id: "can",
    name: t("home.itemAluminumCan"),
    material: "Aluminum",
    weight: "15g",
    carbonSaved: "0.09 kg",
    cardValue: "-0.09 kg CO2e",
    points: "+9 pts",
    asset: aluminumCanAsset,
    objectClass: "waste-object--can",
    cardClass: "capture-card--can",
  },
  {
    id: "cardboard",
    name: t("home.itemCardboardBox"),
    material: "Paper Fiber",
    weight: "120g",
    carbonSaved: "0.08 kg",
    cardValue: "-0.08 kg CO2e",
    points: "+6 pts",
    asset: cardboardBoxAsset,
    objectClass: "waste-object--cardboard",
    cardClass: "capture-card--cardboard",
  },
  {
    id: "glass",
    name: t("home.itemGlassBottle"),
    material: "Green Glass",
    weight: "400g",
    carbonSaved: "0.00 kg",
    cardValue: "-0.00 kg CO2e",
    points: "+3 pts",
    asset: glassBottleAsset,
    objectClass: "waste-object--glass",
    cardClass: "capture-card--glass",
  },
  ];
}

export const wasteItems = getWasteItems((key) => ({
  "home.itemPlasticBottle": "Plastic Bottle",
  "home.itemAluminumCan": "Aluminum Can",
  "home.itemCardboardBox": "Cardboard Box",
  "home.itemGlassBottle": "Glass Bottle",
}[key] ?? key));

export function getPlasticBottleAnalysis(t) {
  return [
    { label: t("home.estimatedWeight"), value: "25g", meta: t("home.metricMetaWeight") },
    { label: t("home.carbonReduction"), value: "0.08 kg", meta: t("home.metricMetaCarbon") },
    { label: t("home.carbonPoints"), value: "+8 pts", meta: t("home.metricMetaPoints") },
  ];
}

export const plasticBottleAnalysis = getPlasticBottleAnalysis((key) => ({
  "home.estimatedWeight": "Estimated Weight",
  "home.carbonReduction": "Carbon Reduction",
  "home.carbonPoints": "Carbon Points",
  "home.metricMetaWeight": "PET single-use bottle",
  "home.metricMetaCarbon": "CO2e saved by recycling",
  "home.metricMetaPoints": "Ready for ledger reward",
}[key] ?? key));

export function getPlasticBottleGuidance(t) {
  return {
    title: t("home.disposalGuidance"),
    body: t("home.disposalBody"),
  };
}

export const plasticBottleGuidance = getPlasticBottleGuidance((key) => ({
  "home.disposalGuidance": "Disposal Guidance",
  "home.disposalBody": "Empty the bottle, keep it dry, and place it in a plastic recycling stream. Remove heavy contamination before audit submission.",
}[key] ?? key));

export function getNearbyLocations(t) {
  return [
    { name: t("home.mapCampus"), distance: "0.4 km", x: 36, y: 42 },
    { name: t("home.mapNorthGate"), distance: "0.8 km", x: 62, y: 28 },
    { name: t("home.mapLibrary"), distance: "1.1 km", x: 72, y: 66 },
  ];
}

export const nearbyLocations = getNearbyLocations((key) => ({
  "home.mapCampus": "Campus Green Hub",
  "home.mapNorthGate": "North Gate Recycling",
  "home.mapLibrary": "Library Return Point",
}[key] ?? key));

export function getAuditFeatures(t) {
  return [
    t("home.auditFeature1"),
    t("home.auditFeature2"),
    t("home.auditFeature3"),
    t("home.auditFeature4"),
  ];
}

export const auditFeatures = getAuditFeatures((key) => ({
  "home.auditFeature1": "Verifies the item is sorted into the correct recycling stream.",
  "home.auditFeature2": "Checks whether the submitted recycling action is valid.",
  "home.auditFeature3": "Records verified impact into the user carbon ledger.",
  "home.auditFeature4": "Improves trust and accuracy for carbon reduction tracking.",
}[key] ?? key));
