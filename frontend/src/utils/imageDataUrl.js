const DEFAULT_MAX_DIMENSION = 1600;
const DEFAULT_QUALITY = 0.82;
const DEFAULT_OUTPUT_TYPE = "image/jpeg";

function readBlobAsDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Failed to read image file."));
    reader.readAsDataURL(blob);
  });
}

function loadImageFromObjectUrl(objectUrl) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Failed to decode image file."));
    image.src = objectUrl;
  });
}

function canvasToBlob(canvas, type, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) {
          resolve(blob);
          return;
        }
        reject(new Error("Failed to compress image file."));
      },
      type,
      quality,
    );
  });
}

function getScaledSize(width, height, maxDimension) {
  if (!width || !height || Math.max(width, height) <= maxDimension) {
    return { width, height };
  }

  const scale = maxDimension / Math.max(width, height);
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  };
}

export async function readCompressedImageDataUrl(
  file,
  {
    maxDimension = DEFAULT_MAX_DIMENSION,
    quality = DEFAULT_QUALITY,
    outputType = DEFAULT_OUTPUT_TYPE,
  } = {},
) {
  if (!file || !file.type?.startsWith("image/")) {
    throw new Error("Please upload an image file.");
  }

  if (typeof document === "undefined" || typeof URL === "undefined") {
    return readBlobAsDataUrl(file);
  }

  const objectUrl = URL.createObjectURL(file);
  let bitmap = null;

  try {
    const source =
      typeof createImageBitmap === "function"
        ? await createImageBitmap(file)
        : await loadImageFromObjectUrl(objectUrl);

    bitmap = typeof source.close === "function" ? source : null;
    const sourceWidth = source.width || source.naturalWidth;
    const sourceHeight = source.height || source.naturalHeight;
    const scaledSize = getScaledSize(sourceWidth, sourceHeight, maxDimension);

    const canvas = document.createElement("canvas");
    canvas.width = scaledSize.width;
    canvas.height = scaledSize.height;

    const context = canvas.getContext("2d");
    if (!context) {
      return readBlobAsDataUrl(file);
    }

    if (outputType === "image/jpeg") {
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, canvas.width, canvas.height);
    }
    context.drawImage(source, 0, 0, canvas.width, canvas.height);

    const compressedBlob = await canvasToBlob(canvas, outputType, quality);
    return readBlobAsDataUrl(compressedBlob);
  } finally {
    if (bitmap) {
      bitmap.close();
    }
    URL.revokeObjectURL(objectUrl);
  }
}
