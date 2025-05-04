import base64
import logging
import os

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ValidationError


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Application configuration
WXOCR_BASE_PATH = os.getenv("WXOCR_BASE_PATH", "/app/wx/opt/wechat/wxocr")
WECHAT_PATH = os.getenv("WECHAT_PATH", "/app/wx/opt/wechat")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


async def get_cpu_limit():
    from multiprocessing import cpu_count

    import aiofiles
    import aiopath

    try:
        if await aiopath.AsyncPath("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").exists():
            async with aiofiles.open(
                "/sys/fs/cgroup/cpu/cpu.cfs_quota_us", mode="r"
            ) as fp:
                cfs_quota_us = int((await fp.read()).strip())
            if cfs_quota_us > 0:
                async with aiofiles.open(
                    "/sys/fs/cgroup/cpu/cpu.cfs_period_us", mode="r"
                ) as fp:
                    cfs_period_us = int((await fp.read()).strip())
                if cfs_period_us > 0:
                    return max(1, cfs_quota_us // cfs_period_us)
        elif await aiopath.AsyncPath("/sys/fs/cgroup/cpu.max").exists():
            async with aiofiles.open("/sys/fs/cgroup/cpu.max", mode="r") as fp:
                content = (await fp.read()).strip().split()
                if len(content) > 2 or content[0] != "max":
                    quota = int(content[0])
                    period = int(content[1])
                    if quota > 0 and period > 0:
                        return max(1, quota // period)
    except Exception as e:
        logger.warning(f"Error detecting container CPU limit: {e}")

    return cpu_count()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    cpu = await get_cpu_limit()
    workers = max(1, cpu - 1)
    logger.info(f"Detected CPU limit: {cpu}, using {workers} workers")
    app.state.semaphore = asyncio.Semaphore(workers)

    yield


app = FastAPI(lifespan=lifespan)


def is_valid_url(url: str) -> bool:
    """Validate if the URL is legal"""
    try:
        result = urlparse(url)
        return all([result.scheme in ["http", "https"], result.netloc])
    except Exception:
        return False


def validate_base64(data: Optional[str]) -> bool:
    """Validate the validity of base64 data"""
    if not data:
        return False
    try:
        return len(base64.b64decode(data)) > 0
    except Exception:
        return False


async def download_image(url: str) -> Optional[bytes]:
    """Download image from URL"""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30)
        content_type = response.headers.get("Content-Type", "").lower()

        if (
            response.status_code == 200
            and content_type.startswith("image/")
            and content_type.split("/")[1] in ALLOWED_EXTENSIONS
        ):
            return response.content
        return None
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# Custom exceptions
class OCRException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@app.exception_handler(ValidationError)
def handle_validation_exception(error: ValidationError):
    logger.error(f"Validation error: {error}")
    return JSONResponse(
        {"error": "Invalid request format", "details": error.errors()},
        status_code=422,
    )


@app.exception_handler(OCRException)
def handle_ocr_exception(error: OCRException):
    return JSONResponse({"error": str(error)}, status_code=error.status_code)


@app.exception_handler(Exception)
def handle_exception(error: Exception):
    logger.error(f"Error processing request: {error}")
    return JSONResponse({"error": "Internal server error"}, status_code=500)


class OcrRequest(BaseModel):
    image: Optional[str] = None
    url: Optional[str] = None


def wxocr(path: str):
    import wcocr  # type: ignore

    # Initialize OCR
    try:
        wcocr.init(WXOCR_BASE_PATH, WECHAT_PATH)
        logger.info("Successfully initialized WXOCR")
        return wcocr.ocr(path)
    except Exception as e:
        logger.error(f"Failed to initialize WXOCR: {e}")
        raise


@app.post("/ocr")
async def ocr(req: OcrRequest):
    """OCR Image Recognition API
    Request body format: {"image": "base64 encoded image data"} or {"url": "image URL"}
    """
    image_data = req.image
    image_url = req.url
    # Prepare image data
    if image_url:
        if not is_valid_url(image_url):
            raise OCRException("Invalid URL format")
        image_bytes = await download_image(image_url)
        if not image_bytes:
            raise OCRException("Failed to download image")
    elif image_data:
        if not validate_base64(image_data):
            raise OCRException("Invalid base64 image data")
        image_bytes = base64.b64decode(image_data)
    else:
        raise OCRException("Must provide either image data or URL, not both")

    # Process image
    from aiofiles import tempfile

    async with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as temp:
        await temp.write(image_bytes)
        await temp.flush()

        start_time = datetime.now()
        processing_time = (datetime.now() - start_time).total_seconds()
        import asyncio

        from concurrent.futures import ProcessPoolExecutor

        async with app.state.semaphore:
            x = ProcessPoolExecutor(max_workers=1)
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(x, wxocr, str(temp.name))
                logger.info(f"OCR completed in {processing_time:.2f}s")
                return result
            finally:
                x.shutdown(wait=False)


try:
    with open("index.html", "r") as f:
        index_html = f.read()
except Exception as e:
    index_html = f"Error reading index.html: {e}"


@app.get("/favicon.ico")
def favicon():
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="32" height="32" viewBox="0 0 32 32" version="1.1" xmlns="http://www.w3.org/2000/svg">
    <circle cx="16" cy="16" r="16" fill="#07C160"/>
    <text x="16" y="22" font-family="Arial, sans-serif" font-size="14" font-weight="bold"
          text-anchor="middle" fill="white">
        OCR
    </text>
</svg>"""

    return Response(svg, media_type="image/svg+xml")


@app.get("/")
def index():
    return Response(index_html, media_type="text/html")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the FastAPI application")
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )
    args = parser.parse_args()
    import uvicorn

    port = int(os.getenv("PORT", 5000))
    uvicorn.run("main:app", port=port, reload=args.reload, host="0.0.0.0")
