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

### Command
```bash
poetry run python website_data_collection_engine.py https://google.com
```

### Output
```json
[
  {
    "url": "https://google.com",
    "total_bytes": 768351,
    "requests": 35,
    "images_bytes": 1024,
    "js_bytes": 674936,
    "css_bytes": 3678,
    "load_time": 3.569
  }
]
```

## Multiple Websites

### Command
```bash
poetry run python website_data_collection_engine.py https://google.com https://openai.com https://github.com
```

### Output
```json
[
  {
    "url": "https://google.com",
    "total_bytes": 770229,
    "requests": 34,
    "images_bytes": 990,
    "js_bytes": 674985,
    "css_bytes": 3678,
    "load_time": 0.577
  },
  {
    "url": "https://openai.com",
    "total_bytes": 221796,
    "requests": 15,
    "images_bytes": 5867,
    "js_bytes": 83465,
    "css_bytes": 0,
    "load_time": 0.625
  },
  {
    "url": "https://github.com",
    "total_bytes": 5570887,
    "requests": 141,
    "images_bytes": 1284246,
    "js_bytes": 1706617,
    "css_bytes": 282436,
    "load_time": 0.632
  }
]
```

## Save Output
```bash
poetry run python website_data_collection_engine.py https://google.com --output-file result.json
```