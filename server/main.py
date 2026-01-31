import os
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from server.routes import tools, files, extract, verify, compress, organize

app = FastAPI(title="Drive Scripts Web GUI")

# Highly permissive CORS for Colab proxies
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    print(
        f"INFO: {request.method} {request.url.path} - {response.status_code} ({process_time:.2f}ms)"
    )
    return response


# Include API routes
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(extract.router, prefix="/api/extract", tags=["extract"])
app.include_router(verify.router, prefix="/api/verify", tags=["verify"])
app.include_router(compress.router, prefix="/api/compress", tags=["compress"])
app.include_router(organize.router, prefix="/api/organize", tags=["organize"])

# Path to the static files directory
# Use absolute path to avoid ambiguity
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(BASE_DIR, "static")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Serve static files
if os.path.exists(STATIC_PATH):
    print(f"INFO: Serving static files from {STATIC_PATH}")
    app.mount("/", StaticFiles(directory=STATIC_PATH, html=True), name="static")
else:
    print(f"ERROR: Static path {STATIC_PATH} not found!")


# Catch-all route to serve index.html for SPA routing
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if not request.url.path.startswith("/api"):
        index_file = os.path.join(STATIC_PATH, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
    return {"detail": "Not Found"}
