# SkillNet local frontend

## Run

Install Node.js 18, 20, or 22+ and Python 3.10+. From `frontend/`, run:

```bash
npm ci
npm run dev
```

Open the local URL printed by Vite. Run `npm run build` for a production build.

## Use a skill library

The personal library starts empty. Click **Create my skill library** to create `~/.skillnet/skills` in your home folder, or connect an existing skills folder. Opening the page alone does not create the folder. A skills folder directly contains one subfolder per skill, each with a `SKILL.md` file. Add skills there and click **Refresh folder**.

Repository examples (WebShop, ALFWorld, and ScienceWorld) are separate from the personal library. Select a skill library first, then choose its `SKILL.md` source or an available analysis snapshot. A document reference means one source file explicitly mentions another skill; it is not a model-inferred relationship.

To download or create skills, install the SDK from the repository root:

```bash
python -m pip install -e "./skillnet-ai[graph]"
skillnet download "<GitHub skill folder URL>" --target-dir "<skills folder>"
skillnet create --prompt "..." --output-dir "<skills folder>"
skillnet analyze "<skills folder>"
```

The `create` and `analyze` commands need model configuration. `analyze` writes to `<skills folder>/.skillnet` by default. The frontend reads the snapshot selected by `CURRENT` and warns when the current skill source differs from the source stored in that snapshot. If you used `--output-dir`, connect that analysis folder in the **Local folders** menu.

## Data and limits

- The bundled analysis snapshots are examples generated from repository skills. A label such as `5/37` means the snapshot covers 5 of that library's 37 skills. They are separate from the public online SkillNet library and from the paper's scale claims.
- Two completed skill-file evaluations are bundled as examples. The frontend displays their saved reports; it does not evaluate skills live.
- **Import graph.json** accepts a local `GraphSnapshot v1` file with `compose_with` and `similar_to` relationships. The file is parsed in the browser and is not uploaded. The browser stores imported snapshots and connected folder records in IndexedDB and remembers the last view. Removing a folder record does not delete files on disk.
- Local folder access requires `npm run dev` or `npm run preview` on the same machine. A static deployment can still browse bundled data and import snapshots, but cannot read local folders.
- Imports are limited to 20 MB, 5,000 skills, and 20,000 relationships. The skill list initially shows up to 200 matches; search narrows it down.

## Refresh bundled data

`npm run dev` and `npm run build` rebuild `src/demo.json` from the repository's `SKILL.md` files and rebuild `src/catalog.json` from `public/data/`. Run `npm run demo:data` to regenerate the source examples separately. Use `python scripts/bundle_analysis.py COLLECTION PATH/TO/graph.json` to add a snapshot from a matching repository collection. Run `python scripts/bundle_evaluations.py` to regenerate `src/evaluations.json` from the two source reports in `data/evaluations/`.
