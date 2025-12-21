"""pharmacy ai agent main application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.routes import chat, auth

app = FastAPI(
    title="Pharmacy AI Agent",
    description="AI-powered pharmacy assistant with user authentication",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    """root endpoint returns api status"""
    return {"message": "Pharmacy AI Agent API", "status": "running"}


@app.get("/health")
async def health_check():
    """health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.port)