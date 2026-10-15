# nasa-field-shift-crop-rotation

## Repo structure

```text
nasa-field-shift-crop-rotation/
├── README.md              # what it is, how to run each part
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI routes
│   │   ├── schemas.py     # request/response models (the contract in code)
│   │   ├── engine/        # scoring, constraints, ranking
│   │   └── data/          # API clients (POWER, SMAP, SoilGrids)
│   ├── tests/
│   └── requirements.txt
├── frontend/
├── data/
│   ├── crops.json         # crop agronomic matrix
│   └── cache/             # saved API responses per demo farm
└── docs/
    ├── api-contract.md
    └── example-responses/ # sample JSON files
```

## Backend / data science: getting started

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python scripts/demo.py
```

`scripts/demo.py` fetches live NASA POWER and SoilGrids data for a test farm
near Ames, Iowa, computes FAO-56 reference ET0 and crop water demand, scores
every valid 3-year rotation from `data/crops.json` against soil, water and
resilience criteria, and prints the top 5 ranked rotations. That's the
current end-to-end slice; the FastAPI app in `backend/app/main.py` wraps the
same engine behind an HTTP endpoint for the frontend to call.

Note: on Python 3.14, `pydantic`/`pandas` wheels may not be published yet;
use Python 3.12 or 3.13 for the venv if `pip install` tries to compile from
source.
