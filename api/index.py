from fastapi import FastAPI  
from mangum import Mangum

# ✅ PUT YOUR CUSTOM IMPORTS HERE (with the dot .)
from .database import engine
from .models import User
from .schemas import UserSchema
from .scoring import calculate_score
# (Add any other imports you need)

app = FastAPI()

# ----- YOUR ROUTES GO HERE -----
@app.get("/")
async def root():
    return {"message": "API is working!"}

@app.get("/hello")
async def hello():
    return {"message": "Hello World"}

# If you have routes that use the database, add them here
# Example:
# @app.get("/users")
# async def get_users():
#     # Use your database code here
#     return {"users": []}

# --------------------------------

# ⚠️ THIS LINE MUST BE AT THE VERY BOTTOM
handler = Mangum(app)