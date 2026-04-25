# One folder with everything to push or hand in

Run this **once** from the project root (folder that contains `api/` and `scripts/`):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_github_bundle.ps1
```

That creates **`github_upload_bundle/`** with:

- `api/`, `modeling/`, `data_processing/`, `data_ingestion/`
- `frontend1/` and `frontend/vite-project/` (no `node_modules` / `.next` / `dist`)
- `data/processed/` CSVs (if present), `data/raw/noaa/`, `data/raw/usgs/`
- `models/*.pkl` (if present), `results/*.json`
- `requirements.txt`, `run_pipeline.py`, `datasets.md`, root `README.md` (if present)

**`github_upload_bundle/` is listed in `.gitignore`** so it is not committed into your main repo (avoids duplicating the whole project).

Then choose:

1. **Zip** `github_upload_bundle` and upload it wherever your instructor asks, or  
2. **Push the full real repo** from the parent folder with `git add` / `git push` (usual workflow), or  
3. **New GitHub repo** only for the bundle: copy the *contents* of `github_upload_bundle` into a new folder, `git init` there, and push (see `README.md` inside the bundle).

Re-run the script whenever you want a fresh copy.
