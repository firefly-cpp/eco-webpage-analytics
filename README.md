# Eco Webpage Analytics 🌱

Eco Webpage Analytics is a simple web application for analyzing website performance and estimating the carbon footprint of web pages.

The application analyzes a given URL, collects resource and performance metrics, estimates CO₂ emissions per visit, and displays optimization recommendations in a dashboard interface.

---

# Project Structure

```txt
frontend/   → Vue.js dashboard application
backend/    → Python FastAPI backend
```

---

# Technologies

## Frontend
- Vue.js
- Chart.js
- Node.js

## Backend
- Python 3.11+
- FastAPI
- Playwright

---

# Prerequisites

Before running the project, make sure you have installed:

- Node.js + npm
- Python 3.11+
- Git


---

# Run Frontend

Open terminal inside the `frontend` folder:

```bash
cd frontend
```

Install frontend dependencies:

```bash
npm install
```

Start the Vue development server:

```bash
npm run serve
```

Frontend runs on:

```txt
http://localhost:8080
```

---

# Run Backend

Open terminal inside the `backend` folder:

```bash
cd backend
```

Create virtual environment:

```bash
python3 -m venv .venv
```

Activate virtual environment:

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

```bash
.venv\Scripts\activate
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

Install Playwright Chromium browser:

```bash
playwright install chromium
```

Start FastAPI backend server:

```bash
uvicorn app:app --reload
```

Backend runs on:

```txt
http://127.0.0.1:8000
```
---

# Run Tests

Backend unit tests are written with pytest. Test dependencies are included in `requirements.txt`.

Run the tests from the project root folder (with the virtual environment activated):

```bash
pytest
```

This also prints a test coverage report for the backend.

