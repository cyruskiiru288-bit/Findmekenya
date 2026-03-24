from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel
from passlib.context import CryptContext
import cloudinary
import cloudinary.uploader
import requests
import base64
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

cloudinary.config(
    cloud_name = "deeiprl8e",
    api_key = "568122111187254",
    api_secret = "P9pUmuY9hxqLpdgQ353RlaJ1bKM"
)

DATABASE_URL = "postgresql://postgres:findme123mahugu@localhost:5432/findmekenya"
engine = create_engine(DATABASE_URL)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MPESA_CONSUMER_KEY = "02ZctAYIcpVOp97w0cKonwNdQyxuMBxr792ZSvMvquuUbjnB"
MPESA_CONSUMER_SECRET = "Of9bMndL4Bl1D4NYDKHPjTLZBXIbbKAJQWUPBbzAyc7mQtKCroGeJNzIqBFQ7wXA"
MPESA_SHORTCODE = "174379"
MPESA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
MPESA_CALLBACK_URL = "https://findmekenya.com/mpesa/callback"

# ===== MODELS =====
class RegisterData(BaseModel):
    name: str
    email: str
    password: str
    phone: str

class LoginData(BaseModel):
    email: str
    password: str

class ProfileData(BaseModel):
    user_id: int
    skill: str
    location: str
    bio: str
    whatsapp: str
    facebook: str

class PaymentData(BaseModel):
    phone: str
    amount: int
    user_id: int
    plan: str

class FreeSubData(BaseModel):
    user_id: int

# ===== ROUTES =====
@app.get("/")
def home():
    return {"message": "Welcome to FindMe Kenya API!"}

@app.post("/register")
def register(data: RegisterData):
    hashed_password = pwd_context.hash(data.password)
    try:
        with engine.connect() as conn:
            existing = conn.execute(text(
                "SELECT id FROM users WHERE email = :email"
            ), {"email": data.email}).fetchone()

            if existing:
                return {"error": "Email already registered!"}

            conn.execute(text(
                "INSERT INTO users (name, email, password, phone) VALUES (:name, :email, :password, :phone)"
            ), {
                "name": data.name,
                "email": data.email,
                "password": hashed_password,
                "phone": data.phone
            })
            conn.commit()

            user = conn.execute(text(
                "SELECT id FROM users WHERE email = :email"
            ), {"email": data.email}).fetchone()

            return {"message": "Registration successful!", "user_id": user.id}
    except Exception as e:
        return {"error": str(e)}

@app.post("/login")
def login(data: LoginData):
    try:
        with engine.connect() as conn:
            user = conn.execute(text(
                "SELECT * FROM users WHERE email = :email"
            ), {"email": data.email}).fetchone()

            if not user:
                return {"error": "Email not found!"}

            if not pwd_context.verify(data.password, user.password):
                return {"error": "Wrong password!"}

            return {
                "message": "Login successful!",
                "user_id": user.id,
                "name": user.name,
                "email": user.email
            }
    except Exception as e:
        return {"error": str(e)}

@app.post("/profile")
def save_profile(data: ProfileData):
    try:
        with engine.connect() as conn:
            existing = conn.execute(text(
                "SELECT id FROM fundi_profiles WHERE user_id = :user_id"
            ), {"user_id": data.user_id}).fetchone()

            if existing:
                conn.execute(text(
                    "UPDATE fundi_profiles SET skill=:skill, location=:location, bio=:bio, whatsapp=:whatsapp, facebook=:facebook, is_active=true WHERE user_id=:user_id"
                ), {
                    "skill": data.skill,
                    "location": data.location,
                    "bio": data.bio,
                    "whatsapp": data.whatsapp,
                    "facebook": data.facebook,
                    "user_id": data.user_id
                })
            else:
                conn.execute(text(
                    "INSERT INTO fundi_profiles (user_id, skill, location, bio, whatsapp, facebook, is_active) VALUES (:user_id, :skill, :location, :bio, :whatsapp, :facebook, true)"
                ), {
                    "user_id": data.user_id,
                    "skill": data.skill,
                    "location": data.location,
                    "bio": data.bio,
                    "whatsapp": data.whatsapp,
                    "facebook": data.facebook
                })
            conn.commit()
            return {"message": "Profile saved successfully! ✅"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/profile/{user_id}")
def get_profile(user_id: int):
    try:
        with engine.connect() as conn:
            profile = conn.execute(text(
                "SELECT * FROM fundi_profiles WHERE user_id = :user_id"
            ), {"user_id": user_id}).fetchone()

            if not profile:
                return {"error": "Profile not found!"}

            return {
                "user_id": profile.user_id,
                "skill": profile.skill,
                "location": profile.location,
                "bio": profile.bio,
                "whatsapp": profile.whatsapp,
                "facebook": profile.facebook,
                "is_active": profile.is_active,
                "is_verified": profile.is_verified,
                "photo_url": profile.photo_url
            }
    except Exception as e:
        return {"error": str(e)}

@app.get("/fundis")
def search_fundis(skill: str = None, location: str = None, name: str = None):
    try:
        with engine.connect() as conn:
            query = """
                SELECT u.name, u.phone, fp.skill, fp.location,
                       fp.bio, fp.whatsapp, fp.facebook, fp.is_verified, fp.photo_url
                FROM fundi_profiles fp
                JOIN users u ON fp.user_id = u.id
                WHERE fp.is_active = true
            """
            params = {}

            if skill:
                query += " AND LOWER(fp.skill) LIKE :skill"
                params["skill"] = f"%{skill.lower()}%"

            if location:
                query += " AND LOWER(fp.location) LIKE :location"
                params["location"] = f"%{location.lower()}%"

            if name:
                query += " AND LOWER(u.name) LIKE :name"
                params["name"] = f"%{name.lower()}%"

            results = conn.execute(text(query), params).fetchall()

            fundis = []
            for f in results:
                fundis.append({
                    "name": f.name,
                    "phone": f.phone,
                    "skill": f.skill,
                    "location": f.location,
                    "bio": f.bio,
                    "whatsapp": f.whatsapp,
                    "facebook": f.facebook,
                    "is_verified": f.is_verified,
                    "photo_url": f.photo_url
                })

            return {"fundis": fundis}
    except Exception as e:
        return {"error": str(e)}

@app.post("/upload-photo/{user_id}")
async def upload_photo(user_id: int, file: UploadFile = File(...)):
    try:
        contents = await file.read()
        result = cloudinary.uploader.upload(contents)
        photo_url = result["secure_url"]

        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE fundi_profiles SET photo_url = :photo_url WHERE user_id = :user_id"
            ), {"photo_url": photo_url, "user_id": user_id})
            conn.commit()

        return {"message": "Photo uploaded successfully!", "photo_url": photo_url}
    except Exception as e:
        return {"error": str(e)}

def get_mpesa_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
    return response.json()["access_token"]

@app.post("/mpesa/stk-push")
def stk_push(data: PaymentData):
    try:
        token = get_mpesa_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()
        ).decode()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": data.amount,
            "PartyA": data.phone,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": data.phone,
            "CallBackURL": MPESA_CALLBACK_URL,
            "AccountReference": "FindMeKenya",
            "TransactionDesc": f"FindMe Kenya {data.plan} subscription"
        }

        response = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers
        )

        result = response.json()

        if result.get("ResponseCode") == "0":
            return {"message": "M-Pesa prompt sent! Check your phone and enter PIN."}
        else:
            return {"error": result.get("errorMessage", "Payment failed!")}

    except Exception as e:
        return {"error": str(e)}

@app.post("/mpesa/callback")
async def mpesa_callback(request: Request):
    try:
        data = await request.json()
        result = data["Body"]["stkCallback"]

        if result["ResultCode"] == 0:
            phone = result["CallbackMetadata"]["Item"][4]["Value"]
            amount = result["CallbackMetadata"]["Item"][0]["Value"]
            mpesa_code = result["CallbackMetadata"]["Item"][1]["Value"]

            with engine.connect() as conn:
                user = conn.execute(text(
                    "SELECT id FROM users WHERE phone = :phone"
                ), {"phone": phone}).fetchone()

                if user:
                    conn.execute(text(
                        "INSERT INTO subscriptions (user_id, amount, is_paid, mpesa_code, start_date, expiry_date) VALUES (:user_id, :amount, true, :mpesa_code, NOW(), NOW() + INTERVAL '30 days')"
                    ), {
                        "user_id": user.id,
                        "amount": amount,
                        "mpesa_code": mpesa_code
                    })
                    conn.execute(text(
                        "UPDATE fundi_profiles SET is_active = true WHERE user_id = :user_id"
                    ), {"user_id": user.id})
                    conn.commit()

        return {"ResultCode": 0, "ResultDesc": "Success"}
    except Exception as e:
        return {"ResultCode": 1, "ResultDesc": str(e)}

@app.get("/spots-remaining")
def spots_remaining():
    try:
        with engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM users"
            )).fetchone()[0]

            remaining = max(0, 500 - count)
            free_available = count < 500

            return {
                "total_registered": count,
                "spots_remaining": remaining,
                "free_available": free_available
            }
    except Exception as e:
        return {"error": str(e)}

@app.post("/free-subscription")
def free_subscription(data: FreeSubData):
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO subscriptions (user_id, plan, amount, is_paid, start_date, expiry_date) VALUES (:user_id, 'free500', 32, true, NOW(), NOW() + INTERVAL '7 months')"
            ), {"user_id": data.user_id})

            conn.execute(text(
                "UPDATE fundi_profiles SET is_active = true WHERE user_id = :user_id"
            ), {"user_id": data.user_id})

            conn.commit()
            return {"message": "7 months subscription activated! ✅"}
    except Exception as e:
        return {"error": str(e)}