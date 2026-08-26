from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello from Vercel!"}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

handler = Mangum(app)