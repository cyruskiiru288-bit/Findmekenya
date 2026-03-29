import os
import requests
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel
from passlib.context import CryptContext

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
)

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    email: str

class FreeSubData(BaseModel):
    user_id: int

class VerifyPaymentData(BaseModel):
    reference: str
    user_id: int
    plan: str

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

# ===== PAYSTACK PAYMENT =====
@app.post("/payment/initialize")
def initialize_payment(data: PaymentData):
    try:
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "email": data.email,
            "amount": data.amount * 100,  # Paystack uses kobo/cents
            "currency": "KES",
            "metadata": {
                "user_id": data.user_id,
                "plan": data.plan,
                "phone": data.phone
            }
        }

        response = requests.post(
            "https://api.paystack.co/transaction/initialize",
            json=payload,
            headers=headers
        )

        result = response.json()

        if result.get("status"):
            return {
                "message": "Payment initialized!",
                "payment_url": result["data"]["authorization_url"],
                "reference": result["data"]["reference"]
            }
        else:
            return {"error": result.get("message", "Payment failed!")}

    except Exception as e:
        return {"error": str(e)}

@app.post("/payment/verify")
def verify_payment(data: VerifyPaymentData):
    try:
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
        }

        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{data.reference}",
            headers=headers
        )

        result = response.json()

        if result.get("status") and result["data"]["status"] == "success":
            with engine.connect() as conn:
                conn.execute(text(
                    "INSERT INTO subscriptions (user_id, plan, amount, is_paid, start_date, expiry_date) VALUES (:user_id, :plan, :amount, true, NOW(), NOW() + INTERVAL '30 days')"
                ), {
                    "user_id": data.user_id,
                    "plan": data.plan,
                    "amount": result["data"]["amount"] // 100
                })
                conn.execute(text(
                    "UPDATE fundi_profiles SET is_active = true WHERE user_id = :user_id"
                ), {"user_id": data.user_id})
                conn.commit()

            return {"message": "Payment verified! Profile is now active! ✅"}
        else:
            return {"error": "Payment not completed!"}

    except Exception as e:
        return {"error": str(e)}

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