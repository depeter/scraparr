"""
API endpoints for proxy traffic capture
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.proxy_service import proxy_service

router = APIRouter(prefix="/proxy", tags=["proxy"])


class ProxyStartRequest(BaseModel):
    """Request to start proxy"""
    web_interface: bool = True


@router.get("/status")
async def get_proxy_status():
    """Get current proxy status"""
    return proxy_service.get_status()


@router.post("/start")
async def start_proxy(request: ProxyStartRequest):
    """Start mitmproxy capture"""
    result = proxy_service.start(web_interface=request.web_interface)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to start proxy"))

    return result


@router.post("/stop")
async def stop_proxy():
    """Stop mitmproxy capture"""
    result = proxy_service.stop()

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to stop proxy"))

    return result


@router.get("/instructions")
async def get_instructions():
    """Get setup instructions for Android device"""
    return proxy_service.get_instructions()


@router.get("/certificate-url")
async def get_certificate_url():
    """Get mitmproxy certificate download URL"""
    return {
        "url": "http://mitm.it",
        "description": "Visit this URL from your Android device (with proxy configured) to download and install the certificate"
    }
