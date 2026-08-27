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
        dechallenge_resolved TEXT,
        rechallenge TEXT,
        alternative TEXT,
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


def save_case(drug, age, sex, region, time_onset, dechallenge, dechallenge_resolved,rechallenge, alternative, narrative, category, confidence, score):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    #insert data into the tables
    cursor.execute('''
        INSERT INTO cases
        (drug, age, sex, region, time_onset, dechallenge, dechallenge_resolved,rechallenge, alternative, narrative, category, confidence, score)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''',(drug, age, sex, region, time_onset, dechallenge, dechallenge_resolved,rechallenge, alternative, narrative, category, confidence, score))
    
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

#fetches the case regardless of how wit entered the system 
def get_case_by_id(case_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, drug, age, sex, region, time_onset,
               dechallenge, dechallenge_resolved, rechallenge, alternative, narrative,
               category, confidence, score, created_at
        FROM cases WHERE id = ?
    ''', (case_id,))

    #fetchone() gets one row from the query result
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        'id':                   row[0],
        'drug':                 row[1],
        'age':                  row[2],
        'sex':                  row[3],
        'region':               row[4],
        'time_onset':           row[5],
        'dechallenge':          row[6],
        'dechallenge_resolved': row[7],
        'rechallenge':          row[8],
        'alternative':          row[9],
        'narrative':            row[10],
        'category':             row[11],
        'confidence':           row[12],
        'score':                row[13],
        'created_at':           row[14]
    }