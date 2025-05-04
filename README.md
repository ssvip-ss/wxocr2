# WeChat OCR API Docker

[![Platform](https://img.shields.io/badge/platform-linux%2Famd64%20%7C%20linux%2Farm64-blue)](https://github.com/yuchanns/wxocr)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![Image](https://ghcr-badge.yuchanns.xyz/yuchanns/wxocr/tags?ignore=latest)](https://github.com/yuchanns/wxocr/pkgs/container/wxocr)
![Size](https://ghcr-badge.yuchanns.xyz/yuchanns/wxocr/size)

A modern, high-performance OCR API service utilizing WeChat's OCR capabilities, containerized for easy deployment. This project enhances [hx71105417/wxocr](https://github.com/hx71105417/wxocr) with improved architecture support, performance optimizations, and modern development practices. It provides both RESTful API and web interface for convenient OCR text extraction from images.

<details>
<summary>WebUI Example</summary>
<img src="https://github.com/user-attachments/assets/9c9afe61-8f63-4794-bf06-ae651842b30f" alt="WebUI Example"
width="600"/>
</details>

## 🚀 Features

- **Cross-Platform Support**: Runs natively on both AMD64 and ARM64 architectures
- **Modern Stack**: Built with Python 3.12 and FastAPI for optimal performance
- **Container-First**: Fully containerized with Docker for consistent deployment
- **Developer-Friendly API**: 
  - Clean REST API interface with JSON responses
  - Support for both base64-encoded images and image URLs
  - Built-in input validation and error handling
- **Efficient Processing**: 
  - Asynchronous connection handling with FastAPI
  - Smart CPU detection and multiprocess architecture for OCR tasks
  - Automatic resource management with semaphores
  - Optimized for high throughput
- **Interactive Testing**: Built-in web UI for quick API testing
- **Health Monitoring**: Built-in health check endpoint
- **Security Features**:
  - Image validation for supported formats (PNG, JPG, JPEG)
  - URL validation and secure image downloading
  - Base64 data validation

## 📋 Prerequisites

- Docker Engine (20.10.0 or later)
- Git with LFS support (for repository cloning)
- Internet access (for pulling container images)

## 🚀 Quick Start

```bash
pdm run dev  # Builds and runs the container locally with hot-reload
```

## 🛠️ Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yuchanns/wxocr
   cd wxocr
   git submodule update --init --recursive
   ```

2. **Build the Docker Image**
   ```bash
   # Setup multi-arch support
   docker run --privileged --rm tonistiigi/binfmt --install all

   # Configure buildx builder
   docker buildx create --name multiarch --driver docker-container --use

   # Build and push multi-arch image
   docker buildx build --platform linux/amd64,linux/arm64 \
     -t ghcr.io/yuchanns/wxocr:latest \
     -t ghcr.io/yuchanns/wxocr:3.12 \
     --push .
   ```

## 📖 Usage Guide

1. **Deploy Container**
   ```bash
   docker run -d -p 5000:5000 ghcr.io/yuchanns/wxocr:latest
   ```

2. **API Endpoints**

   - **Health Check**
     ```bash
     curl http://localhost:5000/health
     ```

   - **Web Interface**
     ```
     http://localhost:5000/
     ```

   - **OCR API**
     ```bash
     # OCR from Base64 encoded image
     curl -X POST http://localhost:5000/ocr \
       -H "Content-Type: application/json" \
       -d '{"image": "'$(base64 test_image.jpg)'"}'

     # OCR from Image URL
     curl -X POST http://localhost:5000/ocr \
       -H "Content-Type: application/json" \
       -d '{"url": "https://example.com/test_image.jpg"}'
     ```

3. **API Response Format**
   ```json
   {
     "code": 200,
     "data": [
       {
         "text": "Extracted text content",
         "position": [x1, y1, x2, y2]  // Text bounding box coordinates
       }
     ]
   }
   ```

4. **Environment Variables**
   - `PORT`: API server port (default: 5000)
   - `WXOCR_BASE_PATH`: Path to WXOCR base directory (default: /app/wx/opt/wechat/wxocr)
   - `WECHAT_PATH`: Path to WeChat directory (default: /app/wx/opt/wechat)

## 🙏 Credits

This project builds upon the work of these excellent repositories:
- [wechat-ocr](https://github.com/swigger/wechat-ocr)
- [wxocr](https://github.com/hx71105417/wxocr)

## ⚠️ Legal Notice

**Disclaimer:** This project is provided for educational and research purposes only. Commercial use is not advised. Users are solely responsible for ensuring their use complies with applicable laws and terms of service.

**Copyright Notice:** This project builds upon and containerizes existing open-source software. If you believe your intellectual property rights have been infringed, please contact us for prompt resolution. We are committed to maintaining open-source compliance and addressing any concerns immediately.

## 📄 License

This project is open-source software licensed under the MIT license.
