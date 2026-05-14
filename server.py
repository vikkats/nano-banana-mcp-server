import base64
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastmcp import FastMCP
from google import genai
from google.genai import types

load_dotenv()

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8080"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/data/generated"))
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY is not set. Image tools will fail until configured.")

client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None
mcp = FastMCP("nano-banana-mcp-server")
app = FastAPI(title="Nano Banana MCP Server")
app.mount("/generated", StaticFiles(directory=str(OUTPUT_DIR)), name="generated")


def public_url_for(path: Path) -> str:
    if PUBLIC_BASE_URL:
        return f"{PUBLIC_BASE_URL}/generated/{path.name}"
    return str(path)


def save_image_bytes(data: bytes, suffix: str = ".png") -> dict[str, str]:
    filename = f"{uuid.uuid4().hex}{suffix}"
    output_path = OUTPUT_DIR / filename
    output_path.write_bytes(data)
    return {
        "path": str(output_path),
        "url": public_url_for(output_path),
    }


async def fetch_image_part(url: str, label: str) -> types.Part:
    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as http:
        response = await http.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type") or mimetypes.guess_type(url)[0] or "image/png"
        return types.Part.from_bytes(data=response.content, mime_type=content_type)


def extract_first_image(response: Any) -> bytes:
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and getattr(inline_data, "data", None):
                data = inline_data.data
                if isinstance(data, str):
                    return base64.b64decode(data)
                return data

    raise RuntimeError("No image data was returned by the model.")


async def call_image_model(parts: list[Any]) -> dict[str, str]:
    if client is None:
        raise RuntimeError("GOOGLE_API_KEY is not configured.")

    response = client.models.generate_content(
        model=GEMINI_IMAGE_MODEL,
        contents=parts,
        config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
    )
    image_bytes = extract_first_image(response)
    return save_image_bytes(image_bytes)


@mcp.tool()
async def generate_image(prompt: str, aspect_ratio: str = "1:1") -> dict[str, str]:
    """Generate an image from a text prompt."""
    full_prompt = f"{prompt}\n\nAspect ratio: {aspect_ratio}"
    return await call_image_model([full_prompt])


@mcp.tool()
async def edit_image(
    prompt: str,
    image_url: Optional[str] = None,
    first_face_url: Optional[str] = None,
    second_face_url: Optional[str] = None,
    aspect_ratio: str = "1:1",
) -> dict[str, str]:
    """Edit or compose an image from a prompt and optional image/reference URLs."""
    parts: list[Any] = [
        (
            f"{prompt}\n\n"
            f"Aspect ratio: {aspect_ratio}\n"
            "Use any supplied reference images only as visual references. "
            "Do not identify real people. Preserve privacy and avoid adding names."
        )
    ]

    if image_url:
        parts.append(await fetch_image_part(image_url, "base image"))
    if first_face_url:
        parts.append(await fetch_image_part(first_face_url, "first face reference"))
    if second_face_url:
        parts.append(await fetch_image_part(second_face_url, "second face reference"))

    return await call_image_model(parts)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "nano-banana-mcp-server",
        "status": "ok",
        "mcp_sse_endpoint": "/sse",
    }


app.mount("/", mcp.sse_app())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
