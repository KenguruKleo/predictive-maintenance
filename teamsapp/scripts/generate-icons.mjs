import { existsSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { deflateSync } from "node:zlib";

const here = dirname(fileURLToPath(import.meta.url));
const appRoot = join(here, "..");
const workspaceRoot = join(appRoot, "..");
const colorIconPath = join(appRoot, "color.png");
const sourceAppIconPath = join(workspaceRoot, "frontend", "electron", "assets", "icon.png");

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const typeBuffer = Buffer.from(type, "ascii");
  const length = Buffer.alloc(4);
  const checksum = Buffer.alloc(4);
  length.writeUInt32BE(data.length, 0);
  checksum.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])), 0);
  return Buffer.concat([length, typeBuffer, data, checksum]);
}

function writePng(path, width, height, pixelAt) {
  const raw = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y += 1) {
    const rowOffset = y * (width * 4 + 1);
    raw[rowOffset] = 0;
    for (let x = 0; x < width; x += 1) {
      const [red, green, blue, alpha] = pixelAt(x, y, width, height);
      const offset = rowOffset + 1 + x * 4;
      raw[offset] = red;
      raw[offset + 1] = green;
      raw[offset + 2] = blue;
      raw[offset + 3] = alpha;
    }
  }

  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header[8] = 8;
  header[9] = 6;
  header[10] = 0;
  header[11] = 0;
  header[12] = 0;

  const png = Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", header),
    chunk("IDAT", deflateSync(raw)),
    chunk("IEND", Buffer.alloc(0)),
  ]);

  writeFileSync(path, png);
}

function insideRoundedRect(x, y, width, height, radius) {
  const left = x < radius;
  const right = x >= width - radius;
  const top = y < radius;
  const bottom = y >= height - radius;
  const cornerX = left ? radius : right ? width - radius - 1 : x;
  const cornerY = top ? radius : bottom ? height - radius - 1 : y;
  return (x - cornerX) ** 2 + (y - cornerY) ** 2 <= radius ** 2;
}

function nearLine(x, y, points, thickness) {
  for (let index = 0; index < points.length - 1; index += 1) {
    const [x1, y1] = points[index];
    const [x2, y2] = points[index + 1];
    const dx = x2 - x1;
    const dy = y2 - y1;
    const lengthSquared = dx * dx + dy * dy;
    const t = Math.max(0, Math.min(1, ((x - x1) * dx + (y - y1) * dy) / lengthSquared));
    const projectedX = x1 + t * dx;
    const projectedY = y1 + t * dy;
    if ((x - projectedX) ** 2 + (y - projectedY) ** 2 <= thickness ** 2) {
      return true;
    }
  }
  return false;
}

function writeFallbackColorIcon() {
  writePng(colorIconPath, 192, 192, (x, y) => {
  if (!insideRoundedRect(x, y, 192, 192, 34)) {
    return [0, 0, 0, 0];
  }

  const background = y < 96 ? [37, 99, 235, 255] : [30, 64, 175, 255];
  const frame = x >= 38 && x <= 154 && y >= 48 && y <= 142;
  const inner = x >= 50 && x <= 142 && y >= 60 && y <= 130;
  const pulse = nearLine(
    x,
    y,
    [
      [54, 104],
      [76, 104],
      [88, 80],
      [108, 122],
      [122, 94],
      [140, 94],
    ],
    5,
  );
  const base = y >= 142 && y <= 150 && x >= 74 && x <= 118;
  const stand = y >= 132 && y <= 148 && x >= 88 && x <= 104;

  if ((frame && !inner) || pulse || base || stand) {
    return [255, 255, 255, 255];
  }
  return background;
  });
}

function writeColorIcon() {
  if (!existsSync(sourceAppIconPath)) {
    writeFallbackColorIcon();
    return;
  }

  try {
    execFileSync("sips", ["-z", "192", "192", sourceAppIconPath, "--out", colorIconPath], {
      stdio: "ignore",
    });
  } catch {
    writeFallbackColorIcon();
  }
}

writeColorIcon();

writePng(join(appRoot, "outline.png"), 32, 32, (x, y) => {
  const frame = x >= 5 && x <= 26 && y >= 7 && y <= 23;
  const inner = x >= 7 && x <= 24 && y >= 9 && y <= 21;
  const pulse = nearLine(
    x,
    y,
    [
      [8, 16],
      [12, 16],
      [15, 11],
      [19, 21],
      [22, 15],
      [25, 15],
    ],
    1.4,
  );
  const base = y >= 24 && y <= 25 && x >= 12 && x <= 20;
  const stand = y >= 22 && y <= 25 && x >= 15 && x <= 17;

  if ((frame && !inner) || pulse || base || stand) {
    return [255, 255, 255, 255];
  }
  return [0, 0, 0, 0];
});