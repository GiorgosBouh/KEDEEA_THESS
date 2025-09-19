import os
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, text

# === Παραμετροποίηση περιβάλλοντος ===
DATABASE_URL   = os.getenv("DATABASE_URL")  # π.χ. postgresql+psycopg://user:pass@host:5432/db
ACCESS_CODE    = os.getenv("ACCESS_CODE", "0000")  # <-- προεπιλογή 0000

ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")  # ιδανικά βάλε π.χ. https://giorgosbouh.github.io

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = FastAPI(title="Kedeea Consent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN] if ALLOWED_ORIGIN != "*" else ["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

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


@app.post("/api/consent")
def create_consent(p: ConsentIn):
    # 1) Έλεγχος κωδικού
    if not p.access_code or p.access_code != ACCESS_CODE:
        raise HTTPException(status_code=403, detail="Invalid access code")

    # 2) Default ημερομηνίας αν λείπει
    signed = p.signed_at or date.today()

    # 3) Εισαγωγή στη βάση
    try:
        with engine.begin() as conn:
            pid = conn.execute(text("""
                insert into participants
                  (first_name, last_name, guardian_name, address_line, city, postal_code,
                   phone, email, sex, age, medical_history)
                values
                  (:first_name, :last_name, :guardian_name, :address_line, :city, :postal_code,
                   :phone, :email, :sex, :age, :medical_history)
                returning id
            """), dict(
                first_name=p.first_name.strip(),
                last_name=p.last_name.strip(),
                guardian_name=p.guardian_name,
                address_line=p.address_line,
                city=p.city,
                postal_code=p.postal_code,
                phone=p.phone,
                email=p.email,
                sex=p.sex,
                age=p.age,
                medical_history=p.medical_history
            )).scalar_one()

            conn.execute(text("""
                insert into consents
                  (participant_id, physio, ergo, logo, diet, gait_analysis, counseling,
                   video_capture, data_processing, data_transfer_outside_eu, biomedical_capture, signed_at)
                values
                  (:participant_id, :physio, :ergo, :logo, :diet, :gait_analysis, :counseling,
                   :video_capture, :data_processing, :data_transfer_outside_eu, :biomedical_capture, :signed_at)
            """), dict(
                participant_id=pid,
                physio=p.physio, ergo=p.ergo, logo=p.logo, diet=p.diet,
                gait_analysis=p.gait_analysis, counseling=p.counseling,
                video_capture=p.video_capture, data_processing=p.data_processing,
                data_transfer_outside_eu=p.data_transfer_outside_eu, biomedical_capture=p.biomedical_capture,
                signed_at=signed
            ))

        return {"status": "ok", "participant_id": str(pid)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))