// Keep the committed welcome files as a fallback for builds scoped to frontend/.
import { existsSync } from "node:fs";
import { lstat, mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";

const source = new URL("../../../website/", import.meta.url);
const target = new URL("../public/welcome/", import.meta.url);
const files = new Set([
  "index.html", "utleie.html", "ledig-moterom.html", "board-data.js",
  "board.css", "board.js", "bookers.css", "hero-art.js", "hero.css",
  "main.js", "renters.css", "renters.js", "spaces.css", "spaces.js", "styles.css",
]);

function sameOriginPage(contents) {
  return contents
    .replace(/<(?:a|form)\b[^>]*\bdata-marketplace\b[^>]*>/g, (tag) =>
      tag.replace(/\b(href|action)="([^"]*)"/, (_, attribute, value) => {
        const url = new URL(value, "https://standbyroom.invalid");
        if (!["http:", "https:"].includes(url.protocol) || url.pathname.startsWith("//")) {
          throw new Error(`Unexpected marketplace destination: ${value}`);
        }
        return `${attribute}="${url.pathname}${url.search}${url.hash}"`;
      })
    )
    .replace(/data-marketplace-origin="[^"]*"/, 'data-marketplace-origin="same-origin"');
}

const hasSource = existsSync(source);
const input = hasSource ? source : target;
const assets = await Promise.all([...files].map(async (file) => {
  const path = new URL(file, input);
  if (!(await lstat(path)).isFile()) throw new Error(`Welcome asset must be a regular file: ${file}`);
  const contents = await readFile(path, "utf8");
  return [file, file.endsWith(".html") ? sameOriginPage(contents) : contents];
}));

if (hasSource) {
  await rm(target, { recursive: true, force: true });
  await mkdir(target, { recursive: true });
  await Promise.all(assets.map(([file, contents]) => writeFile(new URL(file, target), contents)));
} else {
  const unexpected = (await readdir(target)).find((file) => !files.has(file));
  if (unexpected) throw new Error(`Unexpected file in the bundled welcome page: ${unexpected}`);
  for (const [file, contents] of assets) {
    if (file.endsWith(".html") && contents !== await readFile(new URL(file, target), "utf8")) {
      throw new Error(`Regenerate bundled welcome assets from the repository root: ${file}`);
    }
  }
}
