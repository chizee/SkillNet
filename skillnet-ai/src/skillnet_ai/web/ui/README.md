# SkillNet browser interface

Browse local skills, their source files, and saved analysis results. The interface
uses the SDK's `compose_with` and `similar_to` relationships. It never runs a model,
evaluates a skill, or executes skill scripts.

## Use an installed release

The interface is part of the upcoming **skillnet-ai 0.1.2** release. Until it is
published on PyPI, follow [Develop and build](#develop-and-build). After release:

```bash
pip install "skillnet-ai[ui]>=0.1.2"
skillnet ui
skillnet ui --skills-dir "/absolute/path/to/skills"
```

The service listens on `127.0.0.1:8765` and opens your browser. Use `--no-browser`
to suppress opening a tab, or `--port` to change the port. Stop it with Ctrl+C.
No Node.js, database, model key, or repository checkout is needed to browse.

Select a library, then choose **Current skill files** or an available analysis
snapshot in **View**. The graph shows up to 10 neighbors at one hop or 16 at two
hops; **List** searches all relationships in the selected dataset. A two-hop
neighborhood is not an execution plan.

A skills folder directly contains one folder per skill, each with `SKILL.md`.
Opening the interface does not create folders. **Create my skill library** creates
`~/.skillnet/skills` only when clicked. **Refresh folder** rereads the files.
Removing a connection only removes its browser record.

Generate analysis separately, using the same installed SDK:

```bash
pip install "skillnet-ai[graph]"
skillnet download "<GitHub skill folder URL>" --target-dir "<skills folder>"
skillnet create --prompt "..." --output-dir "<skills folder>"
skillnet analyze "<skills folder>"
```

Create and analyze require model configuration; see the SDK README. The interface
reads `.skillnet/CURRENT`, or a custom analysis output directory. Analysis errors
leave current source browsing available. Changed, removed, and newly added skills
are reported; evidence always points to the source saved at analysis time.

## Saved data and limits

- Local imports accept complete SDK `GraphSnapshot v1` files. Parsing happens in
  the browser, without upload. Imported snapshots and directory connections are
  saved in IndexedDB; the last library, content, and selected skill are saved in
  localStorage. Storage is specific to the browser and host/port.
- Limits: 20 MB per import or source library, 5,000 skills, 20,000 relationships.
  The skill list shows the first 200 matches; search narrows the list.

## Develop and build

From `skillnet-ai/`, install the Python source and optional web dependencies:

```bash
python -m pip install -e ".[ui]"
```

From this `web/ui/` directory, using Node.js 20 or 22+:

```bash
npm ci
npm run build
skillnet ui
```

`npm run build` type-checks the source and writes the website to `../static/`.
For live development, use two terminals:

```bash
skillnet ui --dev --no-browser
npm run dev
```

Vite runs at `127.0.0.1:5173` and proxies `/api` to the Python service on port 8765.
The file APIs have one Python implementation; Vite does not read skill folders.
Use `npm run format:check` to check TypeScript/CSS formatting.

## Release

Build the UI before building the Python package. From `skillnet-ai/`:

```bash
npm --prefix src/skillnet_ai/web/ui ci
npm --prefix src/skillnet_ai/web/ui run build
python -m build
```

The wheel includes Python modules and `web/static/`, not React development
sources or `node_modules`. The source distribution includes the UI sources and
prebuilt website, so installing an sdist does not require Node. Build output is
ignored by Git; package builds fail explicitly when the website has not been built.
The SDK and website share the Python distribution version. No example libraries,
saved evaluation reports, or research datasets are shipped with the website.
