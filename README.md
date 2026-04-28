# eco-webpage-analytics 🌱

This is a lightweight, framework‑agnostic library that estimates the carbon footprint of any web page. By combining network‑request data, page‑size metrics, and up‑to‑date
energy‑intensity models, eco-webpage-analytics gives developers instant insight into the environmental impact of their digital products.

# Quick Setup

## 1. Install Python
Install **Python 3.11.x**

## 2. Install Poetry

### Windows (PowerShell)
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

## 3. Install Dependencies
```bash
poetry install
```

## 4. Install Playwright Browser
```bash
poetry run playwright install chromium
```

# Run Website Data Collection Engine

## One Website
```bash
poetry run python website_data_collection_engine.py https://google.com
```

## Multiple Websites
```bash
poetry run python website_data_collection_engine.py https://google.com https://openai.com https://github.com 
```

## Save Output
```bash
poetry run python website_data_collection_engine.py https://google.com --output-file result.json
```