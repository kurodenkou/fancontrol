#!/usr/bin/python3
import sqlite3

def setup_database():
    conn = sqlite3.connect('idrac_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_data (
                 id INTEGER PRIMARY KEY,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                 fan_speed INTEGER,
                 inlet_temp REAL,
                 outlet_temp REAL,
                 cpu1_temp REAL,
                 cpu2_temp REAL
                 )''')
    conn.commit()
    conn.close()

setup_database()
