import os
import sqlite3
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

# === ΡΥΘΜΙΣΕΙΣ ===
DB_PATH      = os.getenv("DB_PATH", "kedeea.db")   # π.χ. ./data/kedeea.db
ACCESS_CODE  = os.getenv("ACCESS_CODE", "0000")    # ο κωδικός σου
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")  # π.χ. http://127.0.0.1:8000 ή https://<username>.github.io

app = FastAPI(title="KE.D.E.E.A Consent API (SQLite)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN] if ALLOWED_ORIGIN != "*" else ["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# === ΒΟΗΘΗΤΙΚΑ ===
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS participants (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      first_name TEXT NOT NULL,
      last_name  TEXT NOT NULL,
      guardian_name TEXT,
      address_line TEXT,
      city TEXT,
      postal_code TEXT,
      phone TEXT,
      email TEXT,
      sex TEXT,
      age INTEGER,
      medical_history TEXT,
      created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS consents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      participant_id INTEGER NOT NULL,
      physio INTEGER DEFAULT 0,
      ergo INTEGER DEFAULT 0,
      logo INTEGER DEFAULT 0,
      diet INTEGER DEFAULT 0,
      gait_analysis INTEGER DEFAULT 0,
      counseling INTEGER DEFAULT 0,
      video_capture INTEGER DEFAULT 0,
      data_processing INTEGER DEFAULT 0,
      data_transfer_outside_eu INTEGER DEFAULT 0,
      biomedical_capture INTEGER DEFAULT 0,
      signed_at TEXT,
      created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
      FOREIGN KEY (participant_id) REFERENCES participants(id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()

init_db()

class ConsentIn(BaseModel):
    # πρόσβαση
    access_code: str

    # στοιχεία
    first_name: str
    last_name: str
    guardian_name: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    sex: Optional[str] = None
    age: Optional[int] = None
    medical_history: Optional[str] = None

    # υπηρεσίες
    physio: bool = False
    ergo: bool = False
    logo: bool = False
    diet: bool = False
    gait_analysis: bool = False
    counseling: bool = False

    # συγκαταθέσεις
    video_capture: bool = False
    data_processing: bool = False
    data_transfer_outside_eu: bool = False
    biomedical_capture: bool = False

    # ημερομηνία
    signed_at: Optional[date] = None

def b(x: bool) -> int:
    return 1 if x else 0

@app.post("/api/consent")
def create_consent(p: ConsentIn):
    # 1) Έλεγχος κωδικού
    if not p.access_code or p.access_code != ACCESS_CODE:
        raise HTTPException(status_code=403, detail="Invalid access code")

    # 2) Default ημερομηνίας αν λείπει
    signed = str(p.signed_at or date.today())  # 'YYYY-MM-DD'

    # 3) Εισαγωγή στη SQLite
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO participants
            (first_name, last_name, guardian_name, address_line, city, postal_code,
             phone, email, sex, age, medical_history)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            p.first_name.strip(), p.last_name.strip(), p.guardian_name, p.address_line, p.city, p.postal_code,
            p.phone, p.email, p.sex, p.age, p.medical_history
        ))
        participant_id = cur.lastrowid

        cur.execute("""
            INSERT INTO consents
            (participant_id, physio, ergo, logo, diet, gait_analysis, counseling,
             video_capture, data_processing, data_transfer_outside_eu, biomedical_capture, signed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            participant_id, b(p.physio), b(p.ergo), b(p.logo), b(p.diet), b(p.gait_analysis), b(p.counseling),
            b(p.video_capture), b(p.data_processing), b(p.data_transfer_outside_eu), b(p.biomedical_capture), signed
        ))
        conn.commit()
        conn.close()
        return {"status": "ok", "participant_id": participant_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))