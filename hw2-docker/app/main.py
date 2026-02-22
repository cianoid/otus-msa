import os

from fastapi import FastAPI

app = FastAPI()


@app.get("/health/")
async def health():
    return {"status": "OK"}

@app.get("/otusapp/{student_name}/health/")
async def health():
    return {"status": "OK"}

@app.get("/")
async def health():
    return {"hostname": os.getenv("HOSTNAME")}
