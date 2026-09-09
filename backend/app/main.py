from fastapi import FastAPI

from routes import trace

app = FastAPI()


app.include_router(trace.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Agentic AI Realtime Backend is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}