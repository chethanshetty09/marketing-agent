"""
AI Image Generation Tool — Create social media visuals, promotional graphics,
and educational illustrations for Ayurvedic content.
Supports OpenAI DALL-E 3 and Stability AI.
"""

import json
import base64
import httpx
from typing import Type, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from config.settings import settings

IMAGES_DIR = Path(__file__).resolve().parent.parent / "data" / "generated_images"


class GenerateImageInput(BaseModel):
    prompt: str = Field(
        description=(
            "Detailed image description. Be specific about: subject, style, colors, "
            "mood, composition. Example: 'A serene Ayurvedic treatment room with warm "
            "golden lighting, brass oil lamps, fresh herbs on a wooden tray, watercolor style'"
        )
    )
    style: str = Field(
        default="natural",
        description=(
            "Visual style: 'natural' (photo-realistic), 'watercolor', 'illustration', "
            "'minimalist', 'infographic', 'vintage_botanical'"
        )
    )
    size: str = Field(
        default="1024x1024",
        description="Image size: '1024x1024' (square/Instagram), '1792x1024' (landscape/Facebook), '1024x1792' (portrait/Stories)"
    )
    purpose: str = Field(
        default="social_post",
        description="Purpose: 'social_post', 'story', 'blog_header', 'ad_creative', 'infographic'"
    )


class GenerateBatchInput(BaseModel):
    theme: str = Field(
        description="Content theme, e.g. 'Panchakarma benefits', 'Winter Ritucharya', 'Dosha types'"
    )
    count: int = Field(default=3, description="Number of variations to generate (1-5)")
    platform: str = Field(
        default="instagram",
        description="Target platform: 'instagram', 'facebook', 'story', 'blog'"
    )


# Ayurvedic visual style presets
STYLE_PRESETS = {
    "natural": (
        "Professional wellness photography style, warm earthy tones, "
        "soft natural lighting, clean composition, spa-like atmosphere"
    ),
    "watercolor": (
        "Elegant watercolor painting style, soft flowing colors, "
        "botanical elements, earthy greens and golden yellows, artistic and serene"
    ),
    "illustration": (
        "Modern flat illustration style, clean lines, warm color palette, "
        "contemporary wellness aesthetic, minimalist detail"
    ),
    "minimalist": (
        "Ultra-clean minimalist design, lots of white space, single accent color, "
        "elegant typography-friendly composition, modern and sophisticated"
    ),
    "infographic": (
        "Clean infographic style, organized layout with clear sections, "
        "icons and visual elements, educational and easy to read"
    ),
    "vintage_botanical": (
        "Vintage botanical illustration style, detailed herb drawings, "
        "aged parchment texture, classical scientific illustration feel, "
        "muted earth tones with green accents"
    ),
}

# Common Ayurvedic visual elements
AYURVEDIC_ELEMENTS = (
    "Important: The image should feel authentically Ayurvedic. Consider including elements like: "
    "brass vessels, herbal powders, mortar and pestle, oil lamps (diyas), tulsi plant, "
    "wooden textures, warm golden tones, traditional Indian patterns, natural ingredients. "
    "Avoid generic stock photo aesthetics. Do not include any text or words in the image."
)


class ImageGenerationTool(BaseTool):
    name: str = "generate_ayurvedic_image"
    description: str = (
        "Generate AI images for Ayurvedic clinic marketing content. Creates visuals "
        "for social media posts, stories, blog headers, and ad creatives. "
        "Automatically applies Ayurvedic-appropriate styling and composition. "
        "Supports styles: natural, watercolor, illustration, minimalist, infographic, vintage_botanical. "
        "Input: prompt (detailed description), style, size, purpose."
    )
    args_schema: Type[BaseModel] = GenerateImageInput

    def _run(
        self, prompt: str, style: str = "natural",
        size: str = "1024x1024", purpose: str = "social_post"
    ) -> str:
        api_key = settings.llm.openai_api_key
        if not api_key:
            return "ERROR: OpenAI API key not configured (needed for DALL-E). Set OPENAI_API_KEY in .env"

        # Build enhanced prompt
        style_modifier = STYLE_PRESETS.get(style, STYLE_PRESETS["natural"])
        enhanced_prompt = f"{prompt}. {style_modifier}. {AYURVEDIC_ELEMENTS}"

        # Map purpose to quality settings
        quality = "hd" if purpose in ("ad_creative", "blog_header") else "standard"

        try:
            resp = httpx.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "dall-e-3",
                    "prompt": enhanced_prompt[:4000],  # DALL-E 3 limit
                    "n": 1,
                    "size": size,
                    "quality": quality,
                    "response_format": "url",
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()

            image_url = data["data"][0]["url"]
            revised_prompt = data["data"][0].get("revised_prompt", "")

            # Save metadata
            IMAGES_DIR.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            meta_file = IMAGES_DIR / f"img_{timestamp}_meta.json"
            with open(meta_file, "w") as f:
                json.dump({
                    "original_prompt": prompt,
                    "enhanced_prompt": enhanced_prompt[:500],
                    "revised_prompt": revised_prompt,
                    "style": style,
                    "size": size,
                    "purpose": purpose,
                    "image_url": image_url,
                    "created_at": datetime.now().isoformat(),
                }, f, indent=2)

            return json.dumps({
                "status": "success",
                "image_url": image_url,
                "size": size,
                "style": style,
                "purpose": purpose,
                "revised_prompt": revised_prompt[:200],
                "note": (
                    "Image URL is temporary (expires in ~1 hour). "
                    "Download and upload to your hosting/CDN before posting."
                ),
            }, indent=2)

        except httpx.HTTPStatusError as e:
            return f"DALL-E API error ({e.response.status_code}): {e.response.text}"
        except Exception as e:
            return f"Error generating image: {str(e)}"


class BatchImageGenerationTool(BaseTool):
    name: str = "generate_ayurvedic_image_batch"
    description: str = (
        "Generate multiple image variations for a content theme. Creates a set of "
        "visuals that can be used across different posts or A/B tested. "
        "Automatically varies composition and style while maintaining theme consistency. "
        "Input: theme, count (1-5), platform."
    )
    args_schema: Type[BaseModel] = GenerateBatchInput

    def _run(self, theme: str, count: int = 3, platform: str = "instagram") -> str:
        api_key = settings.llm.openai_api_key
        if not api_key:
            return "ERROR: OpenAI API key not configured. Set OPENAI_API_KEY in .env"

        # Map platform to size
        size_map = {
            "instagram": "1024x1024",
            "facebook": "1792x1024",
            "story": "1024x1792",
            "blog": "1792x1024",
        }
        size = size_map.get(platform, "1024x1024")

        # Generate varied prompts from the theme
        prompt_variations = [
            f"Close-up detail shot related to {theme}, focusing on textures and ingredients",
            f"Wide lifestyle scene depicting {theme} in a warm Ayurvedic clinic setting",
            f"Artistic flat lay arrangement related to {theme} with herbs and traditional vessels",
            f"Person experiencing {theme} in a peaceful therapeutic environment (no face visible)",
            f"Educational diagram-style illustration explaining {theme} with visual elements",
        ]

        styles = ["natural", "watercolor", "illustration", "minimalist", "vintage_botanical"]

        results = []
        image_tool = ImageGenerationTool()

        for i in range(min(count, 5)):
            prompt = prompt_variations[i % len(prompt_variations)]
            style = styles[i % len(styles)]

            result = image_tool._run(
                prompt=prompt,
                style=style,
                size=size,
                purpose="social_post",
            )

            try:
                result_data = json.loads(result)
                result_data["variation"] = i + 1
                result_data["prompt_used"] = prompt
                results.append(result_data)
            except json.JSONDecodeError:
                results.append({"variation": i + 1, "error": result})

        return json.dumps({
            "theme": theme,
            "platform": platform,
            "variations_generated": len(results),
            "images": results,
        }, indent=2)
