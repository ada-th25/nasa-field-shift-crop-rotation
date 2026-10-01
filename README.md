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
