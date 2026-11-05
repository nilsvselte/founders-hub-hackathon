// Copies the landing pages (repo-root website/) into public/welcome so the
// deployed marketplace serves them at /welcome. The copy is committed, so a
// build that can't see website/ still ships the last synced version.
import { cpSync, existsSync, rmSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, "../../../website");
const target = join(here, "../public/welcome");
const skip = new Set(["bg-lab", "DESIGN.md", ".vercelignore", ".DS_Store"]);

if (!existsSync(source)) {
  console.log("sync-landing: website/ not found, keeping the committed copy");
  process.exit(0);
}
rmSync(target, { recursive: true, force: true });
cpSync(source, target, {
  recursive: true,
  filter: (path) => !relative(source, path).split("/").some((part) => skip.has(part)),
});
console.log("sync-landing: copied website/ to public/welcome");
