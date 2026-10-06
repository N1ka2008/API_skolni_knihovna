# Inventura API školní knihovny

Podle implementace `app.py` připravené k PDF RestApiMR_Vacek_Veber.pdf.

| Metoda | URL | Popis | Parametry | requestBody | Odpověď JSON | HTTP kódy | Role (Basic Auth) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GET | /api/books | Vyhledání titulů | query: q | — | BookAvailability[] | 200, 401, 403, 500 | student, employee, librarian |
| POST | /api/books | Založení titulu | — | BookInput | Book | 201, 400, 401, 403, 409, 500 | librarian |
| PUT | /api/books/{book_id} | Úprava titulu | path: book_id | BookInput | Book | 200, 400, 401, 403, 404, 409, 500 | librarian |
| POST | /api/books/{book_id}/copies | Přidání výtisku | path: book_id | CopyInput | CopyCreated | 201, 400, 401, 403, 409, 500 | librarian |
| PATCH | /api/copies/{copy_id}/retire | Vyřazení výtisku | path: copy_id | RetireInput | RetiredCopy | 200, 400, 401, 403, 404, 500 | librarian |
| GET | /api/readers | Seznam čtenářů | — | — | Reader[] | 200, 401, 403, 500 | librarian |
| POST | /api/readers | Založení čtenáře | — | ReaderInput | IdResponse | 201, 400, 401, 403, 409, 500 | librarian |
| GET | /api/me/loans | Vlastní aktivní výpůjčky | — | — | Loan[] | 200, 401, 403, 500 | student, employee |
| GET | /api/me/reservations | Vlastní aktivní rezervace | — | — | Reservation[] | 200, 401, 403, 500 | student, employee |
| POST | /api/loans | Zapůjčení výtisku | — | LoanInput | LoanCreated | 201, 400, 401, 403, 404, 409, 500 | librarian |
| POST | /api/copies/{copy_id}/return | Vrácení výtisku | path: copy_id | — | ReturnResult | 200, 401, 403, 404, 500 | librarian |
| POST | /api/loans/{loan_id}/extend | Prodloužení vlastní výpůjčky | path: loan_id | — | LoanExtended | 200, 401, 403, 404, 409, 500 | student, employee |
| POST | /api/reservations | Rezervace titulu | — | ReservationInput | ReservationCreated | 201, 400, 401, 403, 404, 409, 500 | student |
| GET | /api/reports/debtors | Seznam dlužníků | — | — | Debtor[] | 200, 401, 403, 500 | librarian |
| GET | /api/reports/graduates | Maturanti s nevrácenou knihou | — | — | GraduateLoan[] | 200, 401, 403, 500 | librarian |
| GET | /api/reports/popularity | Pořadí titulů podle počtu výpůjček | query: from, query: to | — | Popularity[] | 200, 400, 401, 403, 500 | librarian, management |

Všechny obchodní endpointy vyžadují HTTP Basic Auth (hlavička Authorization); GET nemá requestBody. JSON chyba má tvar `{"error":{"code":"…","message":"…"}}`. Nečekané chyby 500 vrací původní Flask API jako HTML. Kód 204 API nepoužívá; není do dokumentace vymyšlen. Nepodporovaná HTTP metoda vrací obecný kód 405 s JSON chybou METHOD_NOT_ALLOWED.

Entity: Book, Copy, Reader, Loan, Reservation. Pole extended a graduate v databázových přehledech jsou celá čísla 0/1; extended při prodloužení je boolean true.

Pomocné veřejné cesty dokumentace: GET /docs/ (HTML Swagger UI), GET /static/openapi.yaml (specifikace YAML). Nevyžadují přihlášení. Statické soubory Swagger UI slouží zobrazení dokumentace.
