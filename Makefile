.PHONY: help venv install env db seed reset run demo test docker docker-down clean

PY      := .venv/bin/python
PIP     := .venv/bin/pip
UVICORN := .venv/bin/uvicorn

help:  ## Tampilkan daftar perintah
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	 | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

venv:  ## Buat virtualenv
	python3 -m venv .venv && $(PIP) install --upgrade pip

install: venv  ## Pasang seluruh dependensi
	$(PIP) install -r requirements.txt

env:  ## Salin .env.example menjadi .env berikut SECRET_KEY acak
	@test -f .env || (cp .env.example .env && \
	 $(PY) -c "import secrets,pathlib; p=pathlib.Path('.env'); \
	 p.write_text(p.read_text().replace('ganti-dengan-string-acak-panjang-min-32-karakter', secrets.token_urlsafe(48)))" && \
	 echo "✅ .env dibuat dengan SECRET_KEY acak")

db:  ## Buat role & database PostgreSQL lokal
	-createuser bkk --login 2>/dev/null || true
	-psql -d postgres -c "ALTER ROLE bkk WITH PASSWORD 'bkk';"
	-createdb bkk_smkn1pati -O bkk
	@echo "✅ Database siap"

seed:  ## Isi data contoh (aman bila sudah ada isi)
	$(PY) -m app.seed

reset:  ## Kosongkan lalu isi ulang database
	$(PY) -m app.seed --reset

run:  ## Jalankan server pengembangan di :8000
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

demo:  ## Jalankan demo statis GitHub Pages di :8080
	$(PY) -m http.server 8080 --directory docs

test:  ## Uji asap seluruh rute
	$(PY) scripts/smoke_test.py

docker:  ## Bangun & jalankan lewat Docker Compose
	docker compose up -d --build

docker-down:  ## Hentikan Docker Compose
	docker compose down

clean:  ## Hapus cache Python
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
