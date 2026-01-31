import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from server.routes import tools, files, extract, verify, compress, organize

app = FastAPI(title="Drive Scripts Web GUI")

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(extract.router, prefix="/api/extract", tags=["extract"])
app.include_router(verify.router, prefix="/api/verify", tags=["verify"])
app.include_router(compress.router, prefix="/api/compress", tags=["compress"])
app.include_router(organize.router, prefix="/api/organize", tags=["organize"])

# Path to the static files directory
STATIC_PATH = os.path.join(os.path.dirname(__file__), "static")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Serve static files
app.mount("/", StaticFiles(directory=STATIC_PATH, html=True), name="static")


# Catch-all route to serve index.html for SPA routing
@app.exception_handler(404)
async def not_found_handler(request, exc):
    if not request.url.path.startswith("/api"):
        return FileResponse(os.path.join(STATIC_PATH, "index.html"))
    return {"detail": "Not Found"}
