#!/usr/bin/python3
from flask import Flask, render_template, g
import sqlite3

app = Flask(__name__)
DATABASE = 'idrac_data.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    db = get_db()
    cursor = db.execute('SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 10')
    current_data = cursor.fetchone()

    cursor = db.execute('SELECT * FROM sensor_data ORDER BY timestamp DESC')
    history = cursor.fetchall()
    
    return render_template('index.html', current=current_data, history=history)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
