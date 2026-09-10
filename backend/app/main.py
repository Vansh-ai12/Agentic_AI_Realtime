from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import trace

app = FastAPI()

# TODO before deploy (D27): restrict CORS to actual frontend origin, remove allow_methods=['*']
# Currently wide-open for local dev (Next.js on :3000 → FastAPI on :8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trace.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Agentic AI Realtime Backend is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}