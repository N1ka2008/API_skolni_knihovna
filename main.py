"""Jednoduché REST API školní knihovny. Žádný frontend."""
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from zoneinfo import ZoneInfo

import click
from flask import Flask, g, jsonify, request
from flask_swagger_ui import get_swaggerui_blueprint
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config['DATABASE'] = os.environ.get('DATABASE', str(Path(__file__).parent / 'knihovna.db'))
app.register_blueprint(get_swaggerui_blueprint(
    '/docs', '/static/openapi.yaml', config={'app_name': 'API školní knihovny'}
))
ACTIVE = "('waiting', 'assigned')"


def today():
    return datetime.now(ZoneInfo('Europe/Prague')).date()


def db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


@app.teardown_appcontext
def close_db(error):
    if 'db' in g:
        g.db.close()


def rows(sql, args=()):
    return [dict(r) for r in db().execute(sql, args).fetchall()]


def fail(code, message, status=409):
    return jsonify(error={'code': code, 'message': message}), status


def data(*required):
    value = request.get_json(silent=True)
    if not isinstance(value, dict) or any(k not in value for k in required):
        raise ValueError('Požadavek musí obsahovat JSON a pole: ' + ', '.join(required))
    for key in required:
        if isinstance(value[key], (dict, list)):
            raise ValueError('Pole musí obsahovat jednoduchou hodnotu: ' + key)
        if key in ('book_id', 'user_id', 'year') and type(value[key]) is not int:
            raise ValueError('Pole musí obsahovat celé číslo: ' + key)
        if key not in ('book_id', 'user_id', 'year') and not isinstance(value[key], str):
            raise ValueError('Pole musí obsahovat text: ' + key)
        if value[key] is None or value[key] == '':
            raise ValueError('Prázdné pole: ' + key)
    return value


@app.errorhandler(ValueError)
def invalid(error):
    db().rollback()
    return fail('INVALID_INPUT', str(error), 400)


@app.errorhandler(sqlite3.IntegrityError)
def conflict(error):
    db().rollback()
    return fail('CONFLICT', 'Duplicitní hodnota nebo neexistující odkaz.', 409)


@app.errorhandler(404)
def not_found(error):
    return fail('NOT_FOUND', 'Záznam nebo endpoint neexistuje.', 404)


@app.errorhandler(500)
def server_error(error):
    db().rollback()
    return fail('INTERNAL_ERROR', 'Neočekávaná chyba serveru.', 500)


@app.errorhandler(405)
def wrong_method(error):
    return fail('METHOD_NOT_ALLOWED', 'Nepovolená HTTP metoda.', 405)


def auth(*roles):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            credentials = request.authorization
            user = None
            if credentials and credentials.type.lower() == 'basic':
                user = db().execute('SELECT * FROM users WHERE email=?',
                                    (credentials.username,)).fetchone()
            if not user or not check_password_hash(user['password'], credentials.password or ''):
                response, status = fail('UNAUTHORIZED', 'Vyžadováno HTTP Basic přihlášení.', 401)
                response.headers['WWW-Authenticate'] = 'Basic realm="Knihovna"'
                return response, status
            if roles and user['role'] not in roles:
                return fail('FORBIDDEN', 'Tato role nemá oprávnění.', 403)
            g.user = dict(user)
            # BEGIN IMMEDIATE serializuje zápisy: dva požadavky nepůjčí stejný výtisk.
            if request.method != 'GET':
                db().execute('BEGIN IMMEDIATE')
            expire_reservations()
            if request.method == 'GET':
                db().commit()
            return fn(*args, **kwargs)
        return wrapped
    return decorate


def assign_waiting():
    waiting = rows("SELECT * FROM reservations WHERE status='waiting' ORDER BY id")
    for reservation in waiting:
        copy = db().execute('''SELECT c.id FROM copies c WHERE c.book_id=?
            AND c.retired IS NULL
            AND NOT EXISTS (SELECT 1 FROM loans l WHERE l.copy_id=c.id AND l.returned_at IS NULL)
            AND NOT EXISTS (SELECT 1 FROM reservations r WHERE r.copy_id=c.id AND r.status='assigned')
            ORDER BY c.id LIMIT 1''', (reservation['book_id'],)).fetchone()
        if copy:
            db().execute("UPDATE reservations SET status='assigned', copy_id=?, expires_at=? WHERE id=?",
                         (copy['id'], (today() + timedelta(days=3)).isoformat(), reservation['id']))


def expire_reservations():
    db().execute("UPDATE reservations SET status='expired' WHERE status='assigned' AND expires_at < ?",
                 (today().isoformat(),))
    assign_waiting()


def blocked(user):
    return user['role'] == 'student' and db().execute('''SELECT 1 FROM loans
        WHERE user_id=? AND returned_at IS NULL AND due_at < ?''',
        (user['id'], (today() - timedelta(days=30)).isoformat())).fetchone() is not None


def save(value, status=200):
    db().commit()
    return jsonify(value), status


@app.get('/api/books')
@auth('student', 'employee', 'librarian')
def books():
    q = '%' + request.args.get('q', '') + '%'
    return jsonify(rows('''SELECT b.*,
        (SELECT COUNT(*) FROM copies c WHERE c.book_id=b.id) AS total_copies,
        (SELECT COUNT(*) FROM copies c WHERE c.book_id=b.id AND c.retired IS NULL
         AND NOT EXISTS (SELECT 1 FROM loans l WHERE l.copy_id=c.id AND l.returned_at IS NULL)
         AND NOT EXISTS (SELECT 1 FROM reservations r WHERE r.copy_id=c.id AND r.status='assigned')) AS available_copies
        FROM books b WHERE b.title LIKE ? OR b.author LIKE ? OR b.genre LIKE ? OR b.isbn LIKE ?''',
        (q, q, q, q)))


@app.post('/api/books')
@auth('librarian')
def create_book():
    d = data('title', 'author', 'genre', 'year', 'isbn')
    if type(d['year']) is not int or not 1 <= d['year'] <= today().year + 1:
        raise ValueError('year musí být platný rok jako celé číslo.')
    cur = db().execute('INSERT INTO books(title,author,genre,year,isbn) VALUES(?,?,?,?,?)',
                       tuple(d[k] for k in ('title', 'author', 'genre', 'year', 'isbn')))
    return save({'id': cur.lastrowid, **{k: d[k] for k in ('title', 'author', 'genre', 'year', 'isbn')}}, 201)


@app.put('/api/books/<int:book_id>')
@auth('librarian')
def update_book(book_id):
    d = data('title', 'author', 'genre', 'year', 'isbn')
    if type(d['year']) is not int or not 1 <= d['year'] <= today().year + 1:
        raise ValueError('year musí být platný rok jako celé číslo.')
    cur = db().execute('UPDATE books SET title=?,author=?,genre=?,year=?,isbn=? WHERE id=?',
                       tuple(d[k] for k in ('title', 'author', 'genre', 'year', 'isbn')) + (book_id,))
    if not cur.rowcount:
        return fail('NOT_FOUND', 'Titul neexistuje.', 404)
    return save({'id': book_id, **d})


@app.post('/api/books/<int:book_id>/copies')
@auth('librarian')
def create_copy(book_id):
    d = data('id')
    if not isinstance(d['id'], str):
        raise ValueError('id výtisku musí být text.')
    db().execute('INSERT INTO copies(id,book_id) VALUES(?,?)', (d['id'], book_id))
    assign_waiting()
    return save({'id': d['id'], 'book_id': book_id}, 201)


@app.patch('/api/copies/<copy_id>/retire')
@auth('librarian')
def retire(copy_id):
    d = data('reason')
    if d['reason'] not in ('damaged', 'lost'):
        raise ValueError('reason: damaged nebo lost.')
    cur = db().execute('UPDATE copies SET retired=? WHERE id=?', (d['reason'], copy_id))
    if not cur.rowcount:
        return fail('NOT_FOUND', 'Výtisk neexistuje.', 404)
    db().execute('UPDATE loans SET returned_at=? WHERE copy_id=? AND returned_at IS NULL',
                 (today().isoformat(), copy_id))
    db().execute("UPDATE reservations SET status='waiting',copy_id=NULL,expires_at=NULL WHERE copy_id=? AND status='assigned'", (copy_id,))
    assign_waiting()
    return save({'id': copy_id, 'retired': d['reason']})


@app.get('/api/readers')
@auth('librarian')
def readers():
    return jsonify(rows("SELECT id,first_name,last_name,email,role,graduate FROM users WHERE role IN ('student','employee')"))


@app.post('/api/readers')
@auth('librarian')
def create_reader():
    d = data('first_name', 'last_name', 'email', 'role', 'password')
    if d['role'] not in ('student', 'employee'):
        raise ValueError('role: student nebo employee.')
    if not isinstance(d['password'], str) or len(d['password']) < 8:
        raise ValueError('Heslo musí mít alespoň 8 znaků.')
    if not isinstance(d['email'], str) or '@' not in d['email']:
        raise ValueError('Neplatný e-mail.')
    if type(d.get('graduate', False)) is not bool:
        raise ValueError('graduate musí být true nebo false.')
    cur = db().execute('INSERT INTO users(first_name,last_name,email,role,graduate,password) VALUES(?,?,?,?,?,?)',
        (d['first_name'], d['last_name'], d['email'], d['role'],
         int(d.get('graduate', False) and d['role'] == 'student'), generate_password_hash(d['password'], method='pbkdf2:sha256:600000')))
    return save({'id': cur.lastrowid}, 201)


@app.get('/api/me/loans')
@auth('student', 'employee')
def my_loans():
    return jsonify(rows('''SELECT l.*,b.title FROM loans l JOIN copies c ON c.id=l.copy_id
        JOIN books b ON b.id=c.book_id WHERE l.user_id=? AND l.returned_at IS NULL''', (g.user['id'],)))


@app.get('/api/me/reservations')
@auth('student', 'employee')
def my_reservations():
    return jsonify(rows(f'''SELECT r.*,b.title FROM reservations r JOIN books b ON b.id=r.book_id
        WHERE user_id=? AND status IN {ACTIVE}''', (g.user['id'],)))


@app.post('/api/loans')
@auth('librarian')
def create_loan():
    d = data('user_id', 'copy_id')
    user = db().execute("SELECT * FROM users WHERE id=? AND role IN ('student','employee')", (d['user_id'],)).fetchone()
    copy = db().execute('SELECT * FROM copies WHERE id=?', (d['copy_id'],)).fetchone()
    if not user or not copy:
        return fail('NOT_FOUND', 'Čtenář nebo výtisk neexistuje.', 404)
    if copy['retired'] or db().execute('SELECT 1 FROM loans WHERE copy_id=? AND returned_at IS NULL', (copy['id'],)).fetchone():
        return fail('COPY_UNAVAILABLE', 'Výtisk je půjčený nebo vyřazený.')
    reservation = db().execute("SELECT * FROM reservations WHERE copy_id=? AND status='assigned'", (copy['id'],)).fetchone()
    if reservation and reservation['user_id'] != user['id']:
        return fail('COPY_RESERVED', 'Výtisk je rezervovaný do ' + reservation['expires_at'])
    if blocked(user):
        return fail('READER_BLOCKED', 'Žák má výpůjčku více než 30 dní po termínu.')
    count = db().execute('SELECT COUNT(*) FROM loans WHERE user_id=? AND returned_at IS NULL', (user['id'],)).fetchone()[0]
    if user['role'] == 'student' and count >= 3:
        return fail('LOAN_LIMIT', 'Žák může mít nejvýše 3 výpůjčky.')
    due = (today() + timedelta(days=30)).isoformat()
    cur = db().execute('INSERT INTO loans(user_id,copy_id,borrowed_at,due_at) VALUES(?,?,?,?)',
                       (user['id'], copy['id'], today().isoformat(), due))
    if reservation:
        db().execute("UPDATE reservations SET status='fulfilled' WHERE id=?", (reservation['id'],))
    return save({'id': cur.lastrowid, 'due_at': due}, 201)


@app.post('/api/copies/<copy_id>/return')
@auth('librarian')
def return_copy(copy_id):
    cur = db().execute('UPDATE loans SET returned_at=? WHERE copy_id=? AND returned_at IS NULL',
                       (today().isoformat(), copy_id))
    if not cur.rowcount:
        return fail('NO_ACTIVE_LOAN', 'Výtisk nemá aktivní výpůjčku.', 404)
    assign_waiting()
    return save({'copy_id': copy_id, 'returned_at': today().isoformat()})


@app.post('/api/loans/<int:loan_id>/extend')
@auth('student', 'employee')
def extend(loan_id):
    loan = db().execute('''SELECT l.*,c.book_id FROM loans l JOIN copies c ON c.id=l.copy_id
        WHERE l.id=? AND l.user_id=? AND l.returned_at IS NULL''', (loan_id, g.user['id'])).fetchone()
    if not loan:
        return fail('NOT_FOUND', 'Vlastní aktivní výpůjčka neexistuje.', 404)
    if loan['due_at'] < today().isoformat():
        return fail('LOAN_OVERDUE', 'Výpůjčka je po termínu.')
    if loan['extended']:
        return fail('ALREADY_EXTENDED', 'Výpůjčku lze prodloužit jen jednou.')
    if db().execute(f'SELECT 1 FROM reservations WHERE book_id=? AND user_id!=? AND status IN {ACTIVE}', (loan['book_id'], g.user['id'])).fetchone():
        return fail('BOOK_RESERVED', 'Titul rezervoval jiný čtenář.')
    due = (datetime.fromisoformat(loan['due_at']).date() + timedelta(days=30)).isoformat()
    db().execute('UPDATE loans SET due_at=?,extended=1 WHERE id=?', (due, loan_id))
    return save({'id': loan_id, 'due_at': due, 'extended': True})


@app.post('/api/reservations')
@auth('student')
def reserve():
    d = data('book_id')
    if not db().execute('SELECT 1 FROM books WHERE id=?', (d['book_id'],)).fetchone():
        return fail('NOT_FOUND', 'Titul neexistuje.', 404)
    if blocked(g.user):
        return fail('READER_BLOCKED', 'Žák je blokován.')
    if db().execute(f'SELECT 1 FROM reservations WHERE user_id=? AND book_id=? AND status IN {ACTIVE}', (g.user['id'], d['book_id'])).fetchone():
        return fail('DUPLICATE_RESERVATION', 'Rezervace již existuje.')
    cur = db().execute("INSERT INTO reservations(user_id,book_id,status) VALUES(?,?,'waiting')", (g.user['id'], d['book_id']))
    assign_waiting()
    result = dict(db().execute('SELECT * FROM reservations WHERE id=?', (cur.lastrowid,)).fetchone())
    if result['status'] == 'waiting':
        result['queue_position'] = db().execute("SELECT COUNT(*) FROM reservations WHERE book_id=? AND status='waiting' AND id<=?", (d['book_id'], cur.lastrowid)).fetchone()[0]
    return save(result, 201)


@app.get('/api/reports/debtors')
@auth('librarian')
def debtors():
    return jsonify(rows('''SELECT u.first_name,u.last_name,u.email,b.title,l.copy_id,l.due_at,
        CAST(julianday(?) - julianday(l.due_at) AS INTEGER) AS days_overdue
        FROM loans l JOIN users u ON u.id=l.user_id JOIN copies c ON c.id=l.copy_id
        JOIN books b ON b.id=c.book_id WHERE l.returned_at IS NULL AND l.due_at < ?''',
        (today().isoformat(), today().isoformat())))


@app.get('/api/reports/graduates')
@auth('librarian')
def graduates():
    return jsonify(rows('''SELECT u.first_name,u.last_name,b.title,l.copy_id,l.due_at
        FROM loans l JOIN users u ON u.id=l.user_id JOIN copies c ON c.id=l.copy_id
        JOIN books b ON b.id=c.book_id WHERE u.graduate=1 AND l.returned_at IS NULL'''))


@app.get('/api/reports/popularity')
@auth('librarian', 'management')
def popularity():
    start = request.args.get('from', '2000-01-01')
    end = request.args.get('to', today().isoformat())
    if datetime.fromisoformat(start).date() > datetime.fromisoformat(end).date():
        raise ValueError('Datum from musí být před to.')
    return jsonify(rows('''SELECT b.id,b.title,COUNT(l.id) AS loan_count FROM books b
        JOIN copies c ON c.book_id=b.id JOIN loans l ON l.copy_id=c.id
        WHERE l.borrowed_at BETWEEN ? AND ? GROUP BY b.id ORDER BY loan_count DESC,b.id''', (start, end)))


def initialize_database(demo=False):
    with app.open_resource('schema.sql') as f:
        db().executescript(f.read().decode())
    if demo and not db().execute('SELECT 1 FROM users').fetchone():
        for first, role, email, graduate in [('Eva','librarian','knihovnice@example.cz',0),
                ('Jan','student','zak@example.cz',1), ('Petr','employee','ucitel@example.cz',0),
                ('Marie','management','vedeni@example.cz',0)]:
            db().execute('INSERT INTO users(first_name,last_name,email,role,graduate,password) VALUES(?,?,?,?,?,?)',
                         (first, 'Test', email, role, graduate, generate_password_hash('Demo12345!', method='pbkdf2:sha256:600000')))
        db().execute("INSERT INTO books(title,author,genre,year,isbn) VALUES('Malý princ','Antoine de Saint-Exupéry','Povídka',1943,'9788000000001')")
        db().execute("INSERT INTO copies(id,book_id) VALUES('K001',1)")
    db().commit()


@app.cli.command('init-db')
@click.option('--demo', is_flag=True, help='Vytvoří ukázkové účty a knihu.')
def init_db(demo):
    initialize_database(demo)
    click.echo('Databáze připravena.')


@app.cli.command('maintenance')
def maintenance():
    """Kontrola propadlých rezervací; spouštějte denně plánovačem."""
    db().execute('BEGIN IMMEDIATE')
    expire_reservations()
    db().commit()
    click.echo('Rezervace zkontrolovány. E-mailové upomínky tato školní verze neodesílá.')


if __name__ == '__main__':
    with app.app_context():
        initialize_database(demo=True)
    print('Swagger dokumentace: http://127.0.0.1:8082/docs/')
    app.run(host='127.0.0.1', port=8082)
