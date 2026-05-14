# Nano Banana MCP Server

A small FastMCP server for generating and editing images with Google Gemini image models, including Nano Banana / Gemini image-generation workflows.

This repo is intentionally generic and public-safe. It uses neutral reference-image parameter names such as `first_face_url` and `second_face_url` instead of private/person-specific names.

## Features

- MCP tool for text-to-image generation
- MCP tool for image editing with optional reference images
- Optional first/second face reference URLs
- Returns saved image paths and public URLs when configured
- Railway-friendly server setup
- No private prompts, no personal names, no hardcoded secrets

## Tools

### `generate_image`

Generate an image from a text prompt.

Arguments:

```json
{
  "prompt": "cinematic product photo of a glass perfume bottle on wet stone",
  "aspect_ratio": "1:1"
}
```

### `edit_image`

Edit or compose an image using a prompt and optional image references.

Arguments:

```json
{
  "prompt": "Create a cinematic portrait using the two face references as inspiration.",
  "image_url": "https://example.com/base-image.png",
  "first_face_url": "https://example.com/first-face.png",
  "second_face_url": "https://example.com/second-face.png",
  "aspect_ratio": "1:1"
}
```

## Environment variables

```bash
GOOGLE_API_KEY=your-google-ai-studio-key
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
PUBLIC_BASE_URL=https://your-service.up.railway.app
OUTPUT_DIR=/data/generated
PORT=8080
```

`PUBLIC_BASE_URL` is optional. If set, the server returns public `/generated/...` URLs. If not set, it still returns local file paths.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

## Railway setup

1. Create a Railway service from this repo.
2. Add the environment variables above.
3. Add a persistent volume mounted at `/data` if you want generated images to survive redeploys.
4. Deploy.

## MCP endpoint

The server uses FastMCP with SSE transport by default.

Typical endpoint:

```txt
https://your-service.up.railway.app/sse
```

## Privacy note

Do not commit API keys, private image URLs, or personal reference images. Use environment variables and temporary signed URLs when possible.
