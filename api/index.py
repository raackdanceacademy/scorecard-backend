from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

# ----- YOUR ROUTES GO HERE -----
@app.get("/")
async def root():
    return {"message": "API is working!"}

@app.get("/hello")
async def hello():
    return {"message": "Hello World"}
# --------------------------------

# ⚠️ THIS LINE IS CRITICAL - Vercel looks for "handler"
handler = Mangum(app)