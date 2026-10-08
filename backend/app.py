"""EasyExpenso backend — Flask + SQLite REST API."""
import os
import sqlite3
from datetime import datetime
from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS

BASE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(os.path.dirname(BASE), 'www')
DB = os.path.join(BASE, 'easyexpenso.db')

app = Flask(__name__, static_folder=WEB, static_url_path='')
CORS(app)


def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    d = g.pop('db', None)
    if d:
        d.close()


def init_db():
    with sqlite3.connect(DB) as c:
        c.execute('''CREATE TABLE IF NOT EXISTS invoices(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            no TEXT, date TEXT, desc TEXT, amount REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, amount REAL, cat TEXT, time TEXT, date TEXT, auto INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY, value TEXT)''')
    # seed budget
    with sqlite3.connect(DB) as c:
        c.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)', ('budget', '0'))


def row(r):
    return dict(r) if r else None


def get_setting(key, default='0'):
    r = db().execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    return float(r['value']) if r else float(default)


def set_setting(key, value):
    db().execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)', (key, str(value)))
    db().commit()


@app.route('/')
def index():
    return send_from_directory(WEB, 'index.html')


@app.route('/<path:path>')
def web(path):
    return send_from_directory(WEB, path)


# ---------- INVOICES ----------
@app.route('/api/invoices', methods=['GET', 'POST'])
def invoices():
    if request.method == 'GET':
        rows = db().execute('SELECT * FROM invoices ORDER BY id DESC').fetchall()
        return jsonify([row(r) for r in rows])
    d = request.get_json(force=True)
    cur = db().execute(
        'INSERT INTO invoices(no,date,desc,amount) VALUES(?,?,?,?)',
        (d.get('no', ''), d.get('date', ''), d.get('desc', ''), float(d.get('amount', 0))))
    db().commit()
    return jsonify({'id': cur.lastrowid}), 201


@app.route('/api/invoices/<int:iid>', methods=['DELETE'])
def del_invoice(iid):
    db().execute('DELETE FROM invoices WHERE id=?', (iid,))
    db().commit()
    return ('', 204)


# ---------- EXPENSES ----------
@app.route('/api/expenses', methods=['GET', 'POST'])
def expenses():
    if request.method == 'GET':
        rows = db().execute('SELECT * FROM expenses ORDER BY id DESC').fetchall()
        return jsonify([row(r) for r in rows])
    d = request.get_json(force=True)
    cur = db().execute(
        'INSERT INTO expenses(name,amount,cat,time,date,auto) VALUES(?,?,?,?,?,?)',
        (d.get('name', ''), float(d.get('amount', 0)), d.get('cat', 'Other'),
         d.get('time', ''), d.get('date', ''), int(d.get('auto', 0) or 0)))
    db().commit()
    return jsonify({'id': cur.lastrowid}), 201


@app.route('/api/expenses/<int:eid>', methods=['DELETE'])
def del_expense(eid):
    db().execute('DELETE FROM expenses WHERE id=?', (eid,))
    db().commit()
    return ('', 204)


# ---------- BUDGET ----------
@app.route('/api/budget', methods=['GET', 'POST'])
def budget():
    if request.method == 'GET':
        return jsonify({'budget': get_setting('budget')})
    v = float(request.get_json(force=True).get('budget', 0))
    set_setting('budget', v)
    return jsonify({'budget': v})


# ---------- DASHBOARD ----------
@app.route('/api/dashboard')
def dashboard():
    now = datetime.now()
    m, y = now.month, now.year
    inv = db().execute('SELECT * FROM invoices').fetchall()
    exp = db().execute('SELECT * FROM expenses').fetchall()

    def in_month(ds):
        try:
            d = datetime.strptime(ds, '%a %b %d %Y')
            return d.month == m and d.year == y
        except Exception:
            return False

    month_inv = [r for r in inv if (r['date'] or '')[:7] == now.strftime('%Y-%m')]
    month_exp = [r for r in exp if in_month(r['date'])]
    biz_t = sum(r['amount'] for r in month_inv)
    cas_t = sum(r['amount'] for r in month_exp)
    return jsonify({
        'month': now.strftime('%Y-%m'),
        'business': round(biz_t, 2),
        'casual': round(cas_t, 2),
        'total': round(biz_t + cas_t, 2),
        'budget': get_setting('budget'),
        'transactions': len(month_inv) + len(month_exp),
    })


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
