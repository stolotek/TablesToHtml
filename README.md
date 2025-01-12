# TablesToHtml
Python FastApi MySQL - Create tables if not exist, download JSON to populate tables

# Data Web Application

This project is a web application built with **FastAPI**, **SQLAlchemy**, and **MySQL** to fetch and display certain data stored in a database. The data is fetched via API and stored in a MySQL database. The web application allows users to view information dynamically.

## **File Overview**

This project consists of several key files that work together to provide the functionality. Below is an overview of the major files and their roles.

### 1. **.env**
The `.env` file contains environment variables that store sensitive and configuration data for the project. This includes database credentials, API keys, and query configurations.

```ini
DB_NAME=databaseName
DB_USER=databaseUser
DB_PASSWORD=databasePw
DB_HOST=localhost
DB_PORT=3306

USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36

GET_MEETINGS_QUERY="query GetMeetingByMonthWithDetails($year: Int!, $month: Int!) {...}"

# GraphQL Headers for API requests
GET_MEETINGS_HEADERS={"Content-Type": "application/json", "user-agent": "Mozilla/5.0 ...", "x-api-key": "da2-6nsi4ztsynar3l3frgxf77q5fe"}
```

**Explanation:**
- `DB_*`: Database connection settings.
- `QUERY_URL`, `GRAPHQL_API_KEY`, `USER_AGENT`: API configuration for fetching race data.
- `GET_MEETINGS_QUERY`, `GET_MEETINGS_HEADERS`: Query and headers for fetching meeting and race data.

---

### 2. **models.py**
This file defines the SQLAlchemy models and database schema for the application.

```python
import os
from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL from .env
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Database engine
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
Base = declarative_base()

# Model Definitions
class Mtgs(Base):
    # Model for meetings data
    __tablename__ = "mtgs"
    mtgsid = Column(BigInteger, primary_key=True, autoincrement=True)
    meetCode = Column(String(25), unique=True, index=True)
    date = Column(String(15))
    venueAbbr = Column(String(15))
    meetUrl = Column(String(255))
    races = relationship("Races", back_populates="mtg", order_by="Races.raceNum")

# Define other models like Races, Fields, and Horses (similar to the Mtgs model)...
```

**Explanation:**
- SQLAlchemy models for storing meetings, races, horses, and related data.
- Uses async sessions for database operations (`AsyncSession`).
- Initializes the database engine using the connection URL stored in the `.env` file.

---

### 3. **main.py**
The main FastAPI application file, which defines the routes and logic for fetching, displaying, and storing race data.

```python
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.sql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from starlette.templating import Jinja2Templates
from models import Mtgs, Races, Horses, engine, SessionLocal, init_db
import os
import http.client
import json
from dotenv import load_dotenv

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Database dependency
async def get_db():
    async with SessionLocal() as session:
        yield session

@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request, db: AsyncSession = Depends(get_db)):
    # Fetch and display meeting and race data
    result = await db.execute(
        select(Mtgs).options(joinedload(Mtgs.races).joinedload(Races.horses)).order_by(Mtgs.date, Mtgs.meetCode)
    )
    mtgs = result.unique().scalars().all()

    return templates.TemplateResponse("home.html", {"request": request, "mtgs": mtgs})

@app.post("/fetch-data", response_class=HTMLResponse)
async def fetch_data(request: Request, db: AsyncSession = Depends(get_db)):
    # Fetch and store race data from the external API
    data = await get_mtgsracesData(2024, 11)
    if not data or "errors" in data:
        return templates.TemplateResponse("home.html", {"request": request, "mtgs": [], "error": "Failed to fetch data."})

    # Insert data into the database
    mtgs_data = []
    races_data = []
    for mtg in data["data"]["GetMeetingByMonth"]:
        mtgs_data.append({
            "meetCode": mtg["meetCode"],
            "date": mtg["date"],
            "meetUrl": mtg["meetUrl"],
            "venueAbbr": mtg["venueAbbr"]
        })
        for race in mtg["races"]:
            races_data.append({
                "meetCode": mtg["meetCode"],
                "raceNum": race["raceNumber"],
                "distance": race["distance"]
            })

    # Bulk insert data
    if mtgs_data:
        await db.execute(insert(Mtgs).values(mtgs_data))
    if races_data:
        await db.execute(insert(Races).values(races_data))
    await db.commit()

    return RedirectResponse(url="/", status_code=303)

async def get_mtgsracesData(year, month):
    # Fetch race data from the external GraphQL API
    load_dotenv()
    GET_MEETINGS_QRY = os.getenv("GET_MEETINGS_QUERY")
    GET_MEETINGS_HEADERJSON = os.getenv("GET_MEETINGS_HEADERS")
    conn = http.client.HTTPSConnection("graphql.rmdprod.racing.com")
    payload = {
        "query": GET_MEETINGS_QRY,
        "operationName": "GetMeetingByMonthWithDetails",
        "variables": {"year": year, "month": month}
    }
    headers = json.loads(GET_MEETINGS_HEADERJSON)
    conn.request("POST", "/", json.dumps(payload), headers)
    res = conn.getresponse()
    return json.loads(res.read().decode())
```

**Explanation:**
- The `read_home` route fetches and displays meetings, races, and horses.
- The `fetch_data` route fetches race data from the GraphQL API and stores it in the MySQL database.
- Utilizes `async`/`await` for asynchronous operations to avoid blocking the server during I/O operations.

---

## **Running the Application**

### Prerequisites
1. **Install Dependencies**:
   Make sure you have `python3` and `pip` installed. Install the required libraries by running:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up the Database**:
   - Make sure you have MySQL installed and running.
   - Create the database specified in your `.env` file (`DB_NAME=elderco`).
   - Update the `.env` file with your MySQL credentials.

3. **Run the FastAPI Server**:
   ```bash
   uvicorn main:app --reload
   ```

4. **Access the Application**:
   Navigate to `http://127.0.0.1:8000/` in your browser to view the application.

---

## **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

This README file gives an overview of the project structure and provides guidance for setting up and running the application. You can now document and share this with others for easy collaboration!
