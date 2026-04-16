import sqlite3
import os



DB_PATH = os.path.join(os.path.dirname(__file__), 'causality.db')


def create_tables():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    #create cases table
    cursor.execute('''    
    CREATE TABLE IF NOT EXISTS cases(
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        drug        TEXT,
        age         TEXT,
        sex         TEXT,
        region      TEXT,
        time_onset  TEXT,
        dechallenge TEXT,
        narrative   TEXT,
        category    TEXT,
        confidence  INTEGER,
        score       INTEGER,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS decisions(
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id     INTEGER,
        assessor    TEXT,
        action      TEXT,
        final_cat   TEXT,
        reasoning   TEXT,
        decided_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def save_case(drug, age, sex, region, time_onset, dechallenge, narrative, category, confidence, score):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    #insert data into the tables
    cursor.execute('''
        INSERT INTO cases
        (drug, age, sex, region, time_onset, dechallenge, narrative, category, confidence, score)
        VALUES(?,?,?,?,?,?,?,?,?,?)
    ''',(drug, age, sex, region, time_onset, dechallenge, narrative, category, confidence, score))
    
    case_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return case_id

def save_decision(case_id, assessor, action, final_cat, reasoning):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO decisions
        (case_id, assessor, action, final_cat, reasoning)
        VALUES(?,?,?,?,?)
        ''',(case_id, assessor, action, final_cat, reasoning))
    
    conn.commit()
    conn.close()

def get_cases():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, drug, age, sex, region, time_onset, dechallenge, category, confidence, created_at
        FROM cases
        ORDER BY created_at DESC  
        ''')
    
    rows = cursor.fetchall()
    conn.close()

    cases = []
    for row in rows:
        cases.append({
            'id': row[0],
            'drug': row[1],
            'age': row[2],
            'sex': row[3],
            'region': row[4],
            'time_onset': row[5],
            'dechallenge': row[6],
            'category': row[7],
            'confidence': row[8],
            'created_at': row[9]
        })

    return cases