import os
import time
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from server.routes import tool_routes, files, extract, verify, compress, organize, demo

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
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        print(
            f"INFO: {request.method} {request.url.path} - {response.status_code} ({process_time:.2f}ms)"
        )
        sys.stdout.flush()
        return response
    except Exception as e:
        print(
            f"ERROR: Exception during {request.method} {request.url.path}: {e}",
            file=sys.stderr,
        )
        import traceback

        traceback.print_exc()
        sys.stderr.flush()
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": str(e)},
        )


@app.get("/api/test")
async def test_endpoint():
    return {"status": "ok"}


# Include API routes
app.include_router(tool_routes.router, prefix="/api/tools", tags=["tools"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(extract.router, prefix="/api/extract", tags=["extract"])
app.include_router(verify.router, prefix="/api/verify", tags=["verify"])
app.include_router(compress.router, prefix="/api/compress", tags=["compress"])
app.include_router(organize.router, prefix="/api/organize", tags=["organize"])
app.include_router(demo.router, prefix="/api/demo", tags=["demo"])

# Path to the static files directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(BASE_DIR, "static")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Serve static files
if os.path.exists(STATIC_PATH):
    app.mount("/", StaticFiles(directory=STATIC_PATH, html=True), name="static")


# Catch-all route to serve index.html for SPA routing
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if not request.url.path.startswith("/api"):
        index_file = os.path.join(STATIC_PATH, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
    return JSONResponse(status_code=404, content={"detail": "Not Found"})
