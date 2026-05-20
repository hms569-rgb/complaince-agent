import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from dotenv import load_dotenv
from models import BusinessProfile
from agent import run_compliance_agent

load_dotenv()

app = FastAPI(
    title="Compliance Agent API",
    description="AI-native compliance analysis for Indian businesses",
    version="1.0.0"
)

# CORS — allows the browser to call this API from index.html
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML file"""
    return FileResponse("index.html")


@app.post("/analyze")
async def analyze_compliance(profile: BusinessProfile):
    """
    Main endpoint — receives business profile, streams back compliance analysis.
    
    Uses StreamingResponse with SSE (Server-Sent Events) so the frontend
    receives the agent's output in real time as it works through tool calls.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set in .env")

    return StreamingResponse(
        run_compliance_agent(profile),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # important — prevents nginx from buffering the stream
        }
    )


@app.get("/health")
async def health_check():
    """Simple health check — useful for deployment later"""
    return {"status": "ok", "api_key_set": bool(os.getenv("ANTHROPIC_API_KEY"))}