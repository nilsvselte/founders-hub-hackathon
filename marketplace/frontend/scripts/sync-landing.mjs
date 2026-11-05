import { lstat, mkdir, readFile, rm, writeFile } from "node:fs/promises";

const site = new URL("../../../website/", import.meta.url);
const destination = new URL("../public/_landing/", import.meta.url);

// Publish only the site's reviewed static assets. Keep local files out of the web root.
const pages = ["index.html", "utleie.html", "ledig-moterom.html"];
const assets = new Set([
  "board-data.js", "board.css", "board.js", "bookers.css", "hero-art.js",
  "hero.css", "main.js", "renters.css", "renters.js", "spaces.css",
  "spaces.js", "styles.css",
]);

await rm(destination, { recursive: true, force: true });
await mkdir(destination, { recursive: true });

await Promise.all([...pages, ...assets].map(async (file) => {
  const source = new URL(file, site);
  if (!(await lstat(source)).isFile()) throw new Error(`Landing source must be a regular file: ${file}`);
  let contents = await readFile(source, "utf8");
  if (pages.includes(file)) {
    contents = contents
      .replace(/(href|action)="http:\/\/127\.0\.0\.1:3001(\/[^"]*)"/g, '$1="$2"')
      .replace(/(href|src)="([^"?#]+)([^"]*)"/g, (attribute, name, path, suffix) =>
        assets.has(path) ? `${name}="/_landing/${path}${suffix}"` : attribute
      )
      .replace(/href="index\.html(#[^"]*)?"/g, 'href="/$1"')
      .replace('data-marketplace-origin=""', 'data-marketplace-origin="same-origin"');
    if (/http:\/\/(?:127\.0\.0\.1|localhost):/.test(contents)) {
      throw new Error(`Local URL remains in generated landing page: ${file}`);
    }
  }
  await writeFile(new URL(file, destination), contents);
}));
