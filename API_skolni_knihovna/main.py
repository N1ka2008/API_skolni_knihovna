from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse

SPEC = Path(__file__).parent / "openapi.yaml"

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

TITLE_EXAMPLE = {
    "id": "0f6d6f3a-9a7f-4e7d-b2f2-9db0d2d61c01",
    "name": "Babička",
    "author": "Božena Němcová",
    "genre": "Román",
    "year": 1855,
    "isbn": "978-80-00-00000-0",
    "copiesTotal": 3,
    "copiesAvailable": 1,
}

COPY_EXAMPLE = {
    "copyId": "K-000123",
    "titleId": TITLE_EXAMPLE["id"],
    "status": "AVAILABLE",
    "withdrawalReason": None,
}

READER_EXAMPLE = {
    "id": "7b55fd08-f8d8-4870-bd8f-0d2f0a73bbf5",
    "firstName": "Anna",
    "lastName": "Nováková",
    "email": "anna.novakova@example.edu",
    "role": "STUDENT",
    "graduate": False,
}

LOAN_EXAMPLE = {
    "id": "1b85aa3f-7251-4e1e-8b55-80f93aa708ce",
    "titleName": "Babička",
    "copyId": "K-000123",
    "borrowedAt": "2026-10-07",
    "dueDate": "2026-11-06",
    "extended": False,
    "returnedAt": None,
}

RESERVATION_EXAMPLE = {
    "id": "25f9dbdf-30e2-4cf4-a94d-6afc30df16c9",
    "titleId": TITLE_EXAMPLE["id"],
    "status": "QUEUED",
    "queuePosition": 1,
    "expiresAt": None,
    "createdAt": "2026-10-07T10:00:00+02:00",
}

@app.get("/openapi.yaml", include_in_schema=False)
def openapi_spec():
    return FileResponse(SPEC, media_type="application/yaml")

@app.get("/docs", include_in_schema=False)
def swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.yaml",
                               title="School Library API – dokumentace")


#Titles
@app.get("/titles")
def search_titles(page: int = 1, pageSize: int = 20, title: Optional[str] = None,
                  author: Optional[str] = None, genre: Optional[str] = None,
                  isbn: Optional[str] = None):
    return {"items": [TITLE_EXAMPLE], "total": 1, "page": page, "pageSize": pageSize}


@app.post("/titles", status_code=201)
def create_title():
    return TITLE_EXAMPLE


@app.get("/titles/{id}")
def get_title(id: str):
    return {**TITLE_EXAMPLE, "id": id}


@app.put("/titles/{id}")
def update_title(id: str):
    return {**TITLE_EXAMPLE, "id": id}


@app.post("/titles/{id}/copies", status_code=201)
def create_copy(id: str):
    return {**COPY_EXAMPLE, "titleId": id}


@app.post("/copies/{copyId}/withdraw")
def withdraw_copy(copyId: str):
    return {**COPY_EXAMPLE, "copyId": copyId, "status": "WITHDRAWN", "withdrawalReason": "DAMAGED"}


#Readers
@app.post("/readers", status_code=201)
def create_reader():
    return READER_EXAMPLE


#Loans
@app.get("/me/loans")
def get_my_loans():
    return []


@app.post("/loans", status_code=201)
def create_loan():
    return LOAN_EXAMPLE


@app.post("/loans/{id}/return")
def return_loan(id: str):
    return {**LOAN_EXAMPLE, "id": id, "returnedAt": "2026-10-20"}


@app.post("/loans/{id}/extend")
def extend_loan(id: str):
    return {**LOAN_EXAMPLE, "id": id, "dueDate": "2026-12-06", "extended": True}


#Reservations
@app.get("/me/reservations")
def get_my_reservations():
    return []


@app.post("/reservations", status_code=201)
def create_reservation():
    return RESERVATION_EXAMPLE


#Reports
@app.get("/reports/overdue")
def get_overdue():
    return []


@app.get("/reports/graduates-unreturned")
def get_graduates_unreturned():
    return []


@app.get("/reports/popular-titles")
def get_popular_titles():
    return []
