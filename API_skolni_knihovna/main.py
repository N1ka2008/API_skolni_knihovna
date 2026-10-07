from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse

SPEC = Path(__file__).parent / "openapi.yaml"

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

@app.get("/openapi.yaml", include_in_schema=False)
def openapi_spec():
    return FileResponse(SPEC, media_type="application/yaml")

@app.get("/docs", include_in_schema=False)
def swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.yaml",
                               title="School Library API – dokumentace")


#Titles
@app.get("/titles")
def search_titles(page: int = 1, pageSize: int = 20, title: str | None = None,
                  author: str | None = None, genre: str | None = None,
                  isbn: str | None = None):
    return {"items": [], "total": 0}


@app.post("/titles", status_code=201)
def create_title():
    return {}


@app.get("/titles/{id}")
def get_title(id: str):
    return {}


@app.put("/titles/{id}")
def update_title(id: str):
    return {}


@app.post("/titles/{id}/copies", status_code=201)
def create_copy(id: str):
    return {}


@app.post("/copies/{copyId}/withdraw")
def withdraw_copy(copyId: str):
    return {}


#Readers
@app.post("/readers", status_code=201)
def create_reader():
    return {}


#Loans
@app.get("/me/loans")
def get_my_loans():
    return []


@app.post("/loans", status_code=201)
def create_loan():
    return {}


@app.post("/loans/{id}/return")
def return_loan(id: str):
    return {}


@app.post("/loans/{id}/extend")
def extend_loan(id: str):
    return {}


#Reservations
@app.get("/me/reservations")
def get_my_reservations():
    return []


@app.post("/reservations", status_code=201)
def create_reservation():
    return {}


#Reports
@app.get("/reports/overdue")
def get_overdue():
    return []


@app.get("/reports/graduates-unreturned")
def get_graduates_unreturned():
    return []

