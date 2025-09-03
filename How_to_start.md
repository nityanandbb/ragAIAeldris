# 1) setup .env from .env.example and edit values
cp .env.example .env

# 2) choose environment (affects config overlay)
export ENV=dev   # or stage/prod

# 3) seed + run everything
make all
# Or individual:
make seed
make test
make k6
make ragas
make promptfoo
