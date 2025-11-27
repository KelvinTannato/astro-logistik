import sys
import asyncio

# ==========================================
# 🛑 FIX KHUSUS WINDOWS
# ==========================================
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# --- IMPORT LIBRARY ---
import uvicorn
import datetime
import re
import urllib.parse
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from passlib.context import CryptContext
from jose import JWTError, jwt
from playwright.async_api import async_playwright

# --- KONFIGURASI KEAMANAN ---
SECRET_KEY = "astro_rahasia_super_secure_key_ganti_ini_nanti"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# --- DATABASE SETUP ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./logistik.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODEL DATABASE ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)
    shipments = relationship("Shipment", back_populates="owner")

class Shipment(Base):
    __tablename__ = "shipments"
    id = Column(Integer, primary_key=True, index=True)
    smu = Column(String, index=True)
    customer_name = Column(String)
    origin = Column(String)
    destination = Column(String)
    transit = Column(String, nullable=True)
    koli = Column(Integer, default=0)
    notes = Column(String, nullable=True)
    status = Column(String, default="Manifested")
    eta_bandara = Column(String, nullable=True)
    eta_door = Column(String, nullable=True)
    last_updated_at = Column(DateTime, default=datetime.datetime.now)
    created_at = Column(DateTime, default=datetime.datetime.now)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="shipments")

Base.metadata.create_all(bind=engine)

# --- SKEMA DATA ---
class ShipmentCreate(BaseModel):
    smu: str
    customer_name: str
    origin: str
    destination: str
    transit: Optional[str] = None
    koli: int = 0
    notes: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str

# --- AUTH UTILS ---
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise credentials_exception
    except JWTError: raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None: raise credentials_exception
    return user

# ==============================================================================
# 🚀 ROBOT GOOGLE FLIGHT (V20 - RESCUE MODE & 2ND VALUE)
# ==============================================================================
async def get_google_flight_eta(flight_no: str, flight_date_str: str):
    print(f"🌍 Google: Mencari {flight_no} tanggal {flight_date_str}...")
    
    eta_result = None
    
    # LOOPING 3 KALI
    # 1 & 2: Invisible (Cepat)
    # 3: Visible (Pop-up Minta Tolong)
    
    for attempt in range(1, 4):
        # Logic Mode: Jika attempt ke-3, TAMPILKAN BROWSER (False). Selain itu SEMBUNYIKAN (True).
        is_headless = False if attempt == 3 else True
        mode_name = "🚨 RESCUE VISIBLE" if attempt == 3 else "👻 STEALTH"
        
        print(f"🔄 Percobaan {attempt}/3 ({mode_name})...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=is_headless, # Dinamis sesuai urutan
                args=["--no-sandbox", "--disable-gpu", "--disable-blink-features=AutomationControlled"]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US"
            )
            page = await context.new_page()
            
            # Blokir gambar hanya di mode stealth biar cepat
            if is_headless:
                await page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())

            query = f"{flight_no} flight schedule {flight_date_str}"
            encoded_query = urllib.parse.quote(query)
            
            try:
                await page.goto(f"https://www.google.com/search?q={encoded_query}&hl=en", timeout=20000, wait_until="domcontentloaded")
                
                # Jika Mode Rescue (Attempt 3), Beri waktu 20 detik buat user bantu
                if attempt == 3:
                    print("\n" + "="*40)
                    print("🆘 ROBOT MINTA BANTUAN!")
                    print("👉 Jendela Browser Muncul.")
                    print("👉 Jika ada CAPTCHA, tolong centang dalam 20 detik!")
                    print("="*40 + "\n")
                    await page.wait_for_timeout(20000) # Tunggu 20 Detik Saja

                # --- 1. AMBIL TEKS BODY ---
                all_text = await page.inner_text("body")
                
                # --- 2. REGEX SCAN TIME ---
                regex_time = r"\b\d{1,2}[.:]\d{2}(?:\s?[APap]\.?[Mm]\.?)?\b"
                found_times = re.findall(regex_time, all_text)
                
                unique_times = []
                for t in found_times:
                    if t not in unique_times: unique_times.append(t)
                
                print(f"   ⏰ Angka Ditemukan: {unique_times}")

                # --- 3. AMBIL URUTAN KE-2 (INDEX 1) ---
                raw_time = None
                if len(unique_times) >= 2:
                    raw_time = unique_times[1] # TARGET: URUTAN KE-2
                    print(f"   👉 Mengambil urutan ke-2: {raw_time}")
                elif len(unique_times) == 1:
                    raw_time = unique_times[0]
                    print(f"   ⚠️ Cuma 1 angka, ambil urutan ke-1: {raw_time}")

                # --- 4. KONVERSI & BREAK ---
                if raw_time:
                    clean_time = raw_time.replace(".", ":").upper().strip()
                    if ":" not in clean_time and "M" in clean_time: clean_time = clean_time.replace(" ", ":00 ")

                    if "PM" in clean_time:
                        t = clean_time.replace("PM", "").strip().split(":")
                        h, m = int(t[0]), t[1]
                        if h != 12: h += 12
                        eta_result = f"{h}:{m}"
                    elif "AM" in clean_time:
                        t = clean_time.replace("AM", "").strip().split(":")
                        h, m = int(t[0]), t[1]
                        if h == 12: h = 0
                        eta_result = f"{h:02d}:{m}"
                    else:
                        try:
                            parts = clean_time.split(":")
                            if int(parts[0]) < 24: eta_result = f"{int(parts[0]):02d}:{parts[1]}"
                            else: eta_result = clean_time
                        except: eta_result = clean_time
                    
                    print(f"✅ BERHASIL: {eta_result}")
                    await browser.close()
                    return eta_result # Keluar dari fungsi sukses
            
            except Exception as e:
                print(f"   ❌ Gagal attempt {attempt}: {e}")
            
            await browser.close()
            
            # Jika belum berhasil, lanjut ke loop berikutnya
    
    print("❌ Gagal Total setelah 3 percobaan.")
    return None

# ==============================================================================
# 🚀 ROBOT UTAMA (GARUDA: TETAP CEPAT & INVISIBLE)
# ==============================================================================
async def run_scraper(airline: str, smu: str, origin: str, transit: str, destination: str):
    result_data = { "status": "Gagal Melacak", "eta_bandara": None, "koli": None }
    origin, transit, destination = origin.upper(), transit.upper() if transit else "", destination.upper()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"]) 
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.route("**/*.{png,jpg,jpeg,gif,webp,css,woff,woff2}", lambda route: route.abort())
        
        try:
            if airline == "GARUDA":
                print(f"🤖 Robot Garuda: {smu}...")
                await page.goto("https://icms.garuda-indonesia.com/Account/Login.cshtml", wait_until="domcontentloaded")
                
                await page.get_by_role("tab", name="Tracking").click()
                parts = smu.split("-")
                await page.locator("#Text_AirlineCode").select_option(parts[0])
                await page.locator("#AWBNo").fill(parts[1])

                async with page.expect_popup() as popup_info:
                    await page.get_by_role("button", name="Track").click()
                
                page1 = await popup_info.value
                await page1.wait_for_load_state("domcontentloaded")
                
                try:
                    await page1.wait_for_selector("text=LATEST EVENT", timeout=6000)
                    await page1.wait_for_selector("text=Pieces", timeout=2000)
                except: pass

                # --- 1. AMBIL STATUS ---
                latest_event_text = ""
                try:
                    td = page1.locator("td").filter(has_text="LATEST EVENT").first
                    latest_event_text = await td.inner_text()
                    latest_event_text = " ".join(latest_event_text.split())
                except: pass

                event_code, current_loc = "INFO", "UNKNOWN"
                if latest_event_text:
                    m_code = re.search(r"LATEST EVENT:?\s*([A-Z]{3})", latest_event_text, re.IGNORECASE)
                    if m_code: event_code = m_code.group(1).upper()
                    else:
                        try: event_code = latest_event_text.split(":")[1].strip().split(" ")[0].upper()
                        except: pass
                    
                    m_loc = re.search(r"(?:at|from)\s+([A-Z]{3})", latest_event_text, re.IGNORECASE)
                    if m_loc: current_loc = m_loc.group(1).upper()
                    else:
                        caps = re.findall(r"\b[A-Z]{3}\b", latest_event_text)
                        caps = [w for w in caps if w not in ["LATEST", "EVENT", event_code]]
                        if caps: current_loc = caps[0]

                    if current_loc == "UNKNOWN" and event_code in ["BKD", "EXE", "PRE", "MAN"]:
                        current_loc = origin
                    
                    final_status = f"Update: {event_code} at {current_loc}"
                    is_org, is_trans, is_dest = (current_loc==origin), (transit and current_loc==transit), (current_loc==destination)

                    if event_code in ["BKD", "EXE", "PRE", "MAN"] and is_org: final_status = f"MASIH DI {origin}"
                    elif event_code == "DEP" and is_org: final_status = f"{origin} > {transit if transit else destination}"
                    elif event_code in ["ARR", "RCF", "PRE", "MAN"] and is_trans: final_status = f"MASIH DI {transit}"
                    elif event_code == "DEP" and is_trans: final_status = f"{transit} > {destination}"
                    elif event_code in ["ARR", "RCF", "AWD", "DLV", "NFD"] and is_dest: final_status = f"SAMPAI DI {destination}"
                    elif event_code in ["DLV", "POD"]: final_status = "SUDAH DITERIMA"
                    elif event_code == "DEP": final_status = f"BERANGKAT DARI {current_loc}"
                    
                    result_data["status"] = final_status

                # --- 2. AMBIL KOLI ---
                try:
                    header = page1.locator("td, th").filter(has_text=re.compile("^Pieces$", re.IGNORECASE)).first
                    if await header.count() > 0:
                        header_row = header.locator("..")
                        cells = await header_row.locator("td, th").all_inner_texts()
                        pcs_idx = -1
                        for i, txt in enumerate([c.strip() for c in cells]):
                            if "Pieces" in txt or "Pcs" in txt: pcs_idx = i; break
                        if pcs_idx != -1:
                            data_row = header.locator("xpath=ancestor::table[1]").locator("tr").nth(1)
                            d_cells = await data_row.locator("td").all_inner_texts()
                            if len(d_cells) > pcs_idx:
                                result_data["koli"] = int(re.search(r"\d+", d_cells[pcs_idx]).group())
                except: pass

                # --- 3. CARI FLIGHT GOOGLE ---
                try:
                    rows = await page1.locator("tr").all_inner_texts()
                    found_no, found_date, target = None, None, f"-> {destination}"
                    for r in reversed(rows):
                        cr = " ".join(r.split())
                        if target in cr.upper():
                            mf = re.search(r"([A-Z0-9]{2}\s?-\s?\d{3,4})", cr)
                            if mf:
                                found_no, found_date = mf.group(1).replace(" ", ""), re.search(r"(\d{1,2}\s[A-Za-z]{3})", cr).group(1)
                                break
                    if not found_no:
                        for r in reversed(rows):
                            cr = " ".join(r.split())
                            mf = re.search(r"([A-Z0-9]{2}\s?-\s?\d{3,4})", cr)
                            if mf:
                                found_no, found_date = mf.group(1).replace(" ", ""), re.search(r"(\d{1,2}\s[A-Za-z]{3})", cr).group(1)
                                break

                    if found_no and found_date:
                        eta = await get_google_flight_eta(found_no, found_date)
                        if eta: result_data["eta_bandara"] = f"{eta} ({found_date})"
                except: pass

                await page1.close()

            elif airline == "LION":
                pass
                
        except Exception as e:
            print(f"❌ Robot Error: {e}")
            result_data["status"] = f"Error: {str(e)}"
        
        await browser.close()
        return result_data

# --- APP SETUP ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user: raise HTTPException(400, "Username exists")
    role = "admin" if user.username.lower() == "admin" else "customer"
    new_user = User(username=user.username, hashed_password=get_password_hash(user.password), role=role)
    db.add(new_user); db.commit(); db.refresh(new_user)
    return {"msg": "Success", "role": role}

@app.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password): raise HTTPException(400, "Invalid credentials")
    return {"access_token": create_access_token({"sub": user.username, "role": user.role}), "token_type": "bearer", "role": user.role}

@app.post("/shipments/")
def create_shipment(item: ShipmentCreate, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.add(Shipment(**item.dict(), owner_id=u.id, status=f"Masih di {item.origin}"))
    db.commit()
    return {"msg": "Created"}

@app.get("/shipments/")
def get_shipments(u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Shipment).all() if u.role == "admin" else db.query(Shipment).filter(Shipment.owner_id == u.id).all()

@app.put("/shipments/{id}")
def update_shipment(id: int, item: ShipmentCreate, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = db.query(Shipment).filter(Shipment.id == id).first()
    if not d: raise HTTPException(404, "Not found")
    if u.role != "admin" and d.owner_id != u.id: raise HTTPException(403, "Forbidden")
    d.customer_name, d.smu, d.origin, d.destination, d.transit, d.koli, d.notes = item.customer_name, item.smu, item.origin, item.destination, item.transit, item.koli, item.notes
    db.commit()
    return {"msg": "Updated"}

@app.delete("/shipments/{id}")
def delete_shipment(id: int, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = db.query(Shipment).filter(Shipment.id == id).first()
    if not d: raise HTTPException(404, "Not found")
    if u.role != "admin" and d.owner_id != u.id: raise HTTPException(403, "Forbidden")
    db.delete(d); db.commit()
    return {"msg": "Deleted"}

@app.post("/update-tracking/{smu}")
async def trigger_ai_tracking(smu: str, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    shipment = db.query(Shipment).filter(Shipment.smu == smu).first()
    if not shipment: raise HTTPException(404, "SMU Not Found")
    
    prefix = smu[:3]
    airline = "GARUDA" if prefix in ["126", "888"] else "LION" if prefix in ["990", "920", "938"] else ""
    if not airline: return {"msg": "Unknown Airline", "new_status": shipment.status}
    
    shipment.status = f"Sedang Dicek Robot di {airline}..."
    db.commit()
    
    try:
        res = await run_scraper(airline, smu, shipment.origin, shipment.transit, shipment.destination)
        shipment.status = res["status"]
        if res["eta_bandara"]: shipment.eta_bandara = res["eta_bandara"]
        if res["koli"] is not None: shipment.koli = res["koli"]
        shipment.last_updated_at = datetime.datetime.now()
        db.commit()
        return {"msg": "Success", "data": res}
    except Exception as e:
        shipment.status = "System Error"
        db.commit()
        raise HTTPException(500, str(e))

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("backend:app", host="127.0.0.1", port=8000, reload=False)