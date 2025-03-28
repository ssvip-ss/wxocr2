import os
import base64
import logging
import tempfile
import requests

from datetime import datetime, timezone
from typing import Optional, cast
from urllib.parse import urlparse
from flask import Flask, request, jsonify, Response
from flask.json.provider import DefaultJSONProvider
from twisted.web.wsgi import WSGIResource
from twisted.web.server import Site
from twisted.internet import reactor, endpoints
from twisted.internet.base import ReactorBase
from werkzeug.middleware.proxy_fix import ProxyFix
import wcocr  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Application configuration
WXOCR_BASE_PATH = os.getenv('WXOCR_BASE_PATH', '/app/wx/opt/wechat/wxocr')
WECHAT_PATH = os.getenv('WECHAT_PATH', '/app/wx/opt/wechat')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
provider = DefaultJSONProvider(app)
provider.ensure_ascii = False
app.json = provider
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Initialize OCR
try:
    wcocr.init(WXOCR_BASE_PATH, WECHAT_PATH)
    logger.info("Successfully initialized WXOCR")
except Exception as e:
    logger.error(f"Failed to initialize WXOCR: {e}")
    raise


def is_valid_url(url: str) -> bool:
    """Validate if the URL is legal"""
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
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


def download_image(url: str) -> Optional[bytes]:
    """Download image from URL"""
    try:
        response = requests.get(url, timeout=30)
        content_type = response.headers.get('Content-Type', '').lower()

        if (response.status_code == 200 and content_type.startswith('image/') and content_type.split('/')[1] in ALLOWED_EXTENSIONS):
            return response.content
        return None
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None


@app.route('/health')
def health_check() -> Response:
    return Response(
        response=jsonify({'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()}).get_data(as_text=True),
        status=200,
        mimetype='application/json'
    )


@app.route('/ocr', methods=['POST'])
def ocr() -> Response:
    """OCR Image Recognition API
    Request body format: {"image": "base64 encoded image data"} or {"url": "image URL"}
    """
    if not request.is_json:
        res = jsonify({'error': 'Content-Type must be application/json'})
        res.status_code = 400
        return res

    data = request.get_json()
    if data is None:
        res = jsonify({'error': 'Invalid JSON data'})
        res.status_code = 400
        return res

    image_data = data.get('image')
    image_url = data.get('url')

    # Validate request parameters
    if (not image_data and not image_url) or (image_data and image_url):
        res = jsonify({'error': 'Must provide either image data or URL, not both'})
        res.status_code = 400
        return res

    try:
        # Prepare image data
        if image_url:
            if not is_valid_url(image_url):
                res = jsonify({'error': 'Invalid URL format'})
                res.status_code = 400
                return res
            image_bytes = download_image(image_url)
            if not image_bytes:
                res = jsonify({'error': 'Failed to download image'})
                res.status_code = 400
                return res
        else:
            if not validate_base64(image_data):
                res = jsonify({'error': 'Invalid base64 image data'})
                res.status_code = 400
                return res
            image_bytes = base64.b64decode(image_data)

        # Process image
        with tempfile.NamedTemporaryFile(suffix='.png', delete=True) as temp:
            temp.write(image_bytes)
            temp.flush()

            start_time = datetime.now()
            result = wcocr.ocr(temp.name)
            processing_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"OCR completed in {processing_time:.2f}s")
            return jsonify(result)

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        res = jsonify({'error': 'Internal server error'})
        res.status_code = 500
        return res


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    typed_reactor = cast(ReactorBase, reactor)
    resource = WSGIResource(typed_reactor, typed_reactor.getThreadPool(), app)
    endpoint = endpoints.TCP4ServerEndpoint(typed_reactor, port, interface='0.0.0.0')
    endpoint.listen(Site(resource))
    logger.info(f"Starting server on port {port}")
    typed_reactor.run()
