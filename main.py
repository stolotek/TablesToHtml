from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from sqlalchemy.sql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from starlette.templating import Jinja2Templates
from models import Mtgs, Races, Horses, engine, SessionLocal, init_db
from contextlib import asynccontextmanager
import os
import http.client
import json
from dotenv import load_dotenv

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app.router.lifespan_context = lifespan

async def get_db():
    async with SessionLocal() as session:
        yield session

@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Mtgs)
            .options(joinedload(Mtgs.races).joinedload(Races.horses))
            .order_by(Mtgs.date, Mtgs.meetCode)
        )
        mtgs = result.unique().scalars().all()

        # Ensure relationships have default empty lists
        for mtg in mtgs:
            mtg.races = mtg.races or []
            for race in mtg.races:
                race.horses = race.horses or []

        return templates.TemplateResponse("home.html", {"request": request, "mtgs": mtgs})
    except Exception as e:
        return templates.TemplateResponse("home.html", {"request": request, "mtgs": [], "error": str(e)})

@app.post("/fetch-data", response_class=HTMLResponse)
async def fetch_data(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        data = await get_mtgsracesData(2024, 11)
        if not data or "errors" in data:
            error_message = "Failed to fetch data."
            if "errors" in data:
                error_message += f" Errors: {data['errors']}"
            return templates.TemplateResponse("home.html", {"request": request, "mtgs": [], "error": error_message})

        # Fetch existing meetCodes from the database
        existing_mtgs = await db.execute(select(Mtgs.meetCode))
        existing_meet_codes = {row[0] for row in existing_mtgs.fetchall()}

        # Parse JSON and filter out already existing meetCodes
        mtgs_data = []
        races_data = []

        for mtg in data["data"]["GetMeetingByMonth"]:
            if mtg["meetCode"] not in existing_meet_codes:
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

        # Bulk append new mtgs and races
        if mtgs_data:
            await db.execute(insert(Mtgs).values(mtgs_data))
        if races_data:
            await db.execute(insert(Races).values(races_data))
        await db.commit()

        # Redirect to the home page to reload with updated data
        return RedirectResponse(url="/", status_code=303)
    
    except Exception as e:
        return templates.TemplateResponse("home.html", {"request": request, "mtgs": [], "error": str(e)})

async def get_mtgsracesData(year, month):
    # Load environment variables from .env file
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

if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
	  
