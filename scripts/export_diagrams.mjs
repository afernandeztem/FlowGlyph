// Renders docs/assets/*.excalidraw to <name>-light.svg and <name>-dark.svg with the official
// Excalidraw exporter running in headless Chromium. Fonts are served from node_modules so the
// output does not depend on a CDN and is identical on every machine.
import { readFile, readdir, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";

import { build } from "esbuild";
import { chromium } from "playwright";

const here = import.meta.dirname;
const assets = path.resolve(here, "../docs/assets");
const excalidrawDist = path.join(here, "node_modules/@excalidraw/excalidraw/dist/prod");
const bundlePath = path.join(here, "dist/diagrams.js");

const contentTypes = { ".js": "text/javascript", ".woff2": "font/woff2", ".html": "text/html" };
const page = `<!doctype html><meta charset="utf-8">
<script>
  window.EXCALIDRAW_ASSET_PATH = location.origin + "/excalidraw/";
  window.EXCALIDRAW_EXPORT_SOURCE = "https://excalidraw.com";
</script>
<script src="/diagrams.js"></script>`;

export async function openRenderer() {
  await build({
    entryPoints: [path.join(here, "diagram-entry.mjs")],
    bundle: true,
    format: "iife",
    minify: true,
    outfile: bundlePath,
    loader: { ".css": "empty" },
    define: { "process.env.NODE_ENV": '"production"', "process.env.IS_PREACT": '"false"' },
    logLevel: "warning",
  });
  const server = createServer(async (request, response) => {
    const url = new URL(request.url, "http://localhost");
    const file =
      url.pathname === "/" ? null
      : url.pathname === "/diagrams.js" ? bundlePath
      : url.pathname.startsWith("/excalidraw/")
        ? path.join(excalidrawDist, decodeURIComponent(url.pathname.slice("/excalidraw/".length)))
        : undefined;
    if (file && !file.startsWith(excalidrawDist) && file !== bundlePath) {
      response.writeHead(403).end();
      return;
    }
    try {
      const body = file === null ? page : await readFile(file);
      const type = file === null ? contentTypes[".html"] : contentTypes[path.extname(file)];
      response.writeHead(200, { "content-type": type ?? "application/octet-stream" });
      response.end(body);
    } catch {
      response.writeHead(404).end();
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const browser = await chromium.launch();
  const tab = await browser.newPage();
  await tab.goto(`http://127.0.0.1:${server.address().port}/`);
  await tab.waitForFunction(() => window.flowglyphDiagrams !== undefined);
  return {
    tab,
    async close() {
      await browser.close();
      server.close();
    },
  };
}

async function renderSvg(tab, scene, dark) {
  return tab.evaluate(
    async ({ scene, dark }) => {
      const svg = await window.flowglyphDiagrams.exportToSvg({
        elements: scene.elements,
        files: scene.files ?? {},
        appState: {
          ...scene.appState,
          exportBackground: true,
          exportWithDarkMode: dark,
          exportEmbedScene: true,
        },
        exportPadding: 24,
      });
      return svg.outerHTML;
    },
    { scene, dark },
  );
}

async function main() {
  const renderer = await openRenderer();
  try {
    const sources = (await readdir(assets)).filter((name) => name.endsWith(".excalidraw")).sort();
    for (const source of sources) {
      const scene = JSON.parse(await readFile(path.join(assets, source), "utf8"));
      const name = source.replace(/\.excalidraw$/, "");
      for (const [suffix, dark] of [["light", false], ["dark", true]]) {
        const svg = await renderSvg(renderer.tab, scene, dark);
        await writeFile(path.join(assets, `${name}-${suffix}.svg`), svg + "\n");
      }
      console.log(`rendered ${source}`);
    }
  } finally {
    await renderer.close();
  }
}

if (process.argv[1] === import.meta.filename) {
  await main();
}
