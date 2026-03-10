import os
import json
import torch
import base64
import io
import numpy as np
import aiohttp
from PIL import Image
from comfy_api.latest import ComfyExtension, io as comfy_io, ui as comfy_ui

try:
    from server import PromptServer
    from aiohttp import web
except ImportError:
    PromptServer = None

def get_prompt_files():
    """Scans the 'prompts' directory for .txt files and returns a dictionary."""
    prompt_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'prompts')
    prompt_files = {}
    if os.path.exists(prompt_dir):
        for filename in os.listdir(prompt_dir):
            if filename.endswith(".txt"):
                filepath = os.path.join(prompt_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        key = os.path.splitext(filename)[0]
                        prompt_files[key] = f.read().strip()
                except Exception as e:
                    print(f"BasicOllama: Error reading prompt file {filename}: {e}")
    return prompt_files

def rgba_to_rgb(image):
    """Convert RGBA image to RGB with white background"""
    if image.mode == 'RGBA':
        background = Image.new("RGB", image.size, (255, 255, 255))
        image = Image.alpha_composite(background.convert("RGBA"), image).convert("RGB")
    return image

def tensor_to_pil(tensor):
    """Convert a [H, W, C] tensor to PIL Image"""
    if tensor.dim() == 4:
        tensor = tensor[0]
        
    image_np = tensor.cpu().numpy()
    image_np = (image_np * 255).clip(0, 255).astype(np.uint8)
    
    if image_np.shape[-1] == 1:
        image_np = np.repeat(image_np, 3, axis=-1)
    
    mode = 'RGBA' if image_np.shape[-1] == 4 else 'RGB'
    image = Image.fromarray(image_np, mode=mode)
    return rgba_to_rgb(image)
    
def tensor_to_base64(tensor):
    """Convert tensor to base64 encoded PNG"""
    image = tensor_to_pil(tensor)
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def get_ollama_url():
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json')
    ollama_url = "http://localhost:11434"
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            ollama_url = config.get("OLLAMA_URL", ollama_url)
        except Exception as e:
            print(f"BasicOllama: Error reading config.json: {e}")
    return ollama_url

async def fetch_ollama_models():
    url = f"{get_ollama_url()}/api/tags"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=2) as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get('models', [])
                    return [model['name'] for model in models]
    except Exception:
        pass
    return ["Start Ollama and Refresh"]

class BasicOllama(comfy_io.ComfyNode):
    @classmethod
    def define_schema(cls) -> comfy_io.Schema:
        prompt_templates = get_prompt_files()
        prompt_structures = list(prompt_templates.keys())
        if not prompt_structures:
            prompt_structures = ["None"]

        return comfy_io.Schema(
            node_id="BasicOllama",
            display_name="Basic Ollama",
            category="Ollama",
            description="Interface with Ollama LLMs, supporting dynamic image inputs.",
            is_output_node=False,
            inputs=[
                comfy_io.String.Input("prompt", multiline=True, tooltip="The main text prompt for the LLM."),
                comfy_io.MultiType.Input(
                    comfy_io.Combo.Input("ollama_model", 
                                        options=["Loading..."],
                                        default="Loading...",
                                        tooltip="Select the Ollama model to use.",
                                        socketless=True,
                                        remote=comfy_io.RemoteOptions(
                                            route="/basic_ollama/models",
                                            refresh_button=True
                                        )),
                    types=[comfy_io.String]
                ),
                comfy_io.Int.Input(
                    "generation_seed",
                    default=0,
                    min=0,
                    max=0xffffffffffffffff,
                    step=1,
                    control_after_generate=True,
                    tooltip="Seed for randomness. Change this to force a new generation."
                ),
                comfy_io.Boolean.Input("enable_think", default=True, tooltip="Enable reasoning/thinking for supported models."),
                comfy_io.Combo.Input(
                    "saved_sys_prompt",
                    options=prompt_structures,
                    default=prompt_structures[0],
                    tooltip="Select a pre-defined system prompt."
                ),
                comfy_io.Boolean.Input("use_sys_prompt_below", default=False, tooltip="If True, use the custom system prompt below instead of the saved one."),
                comfy_io.String.Input("system_prompt", multiline=True, tooltip="Custom system prompt to guide the LLM's behavior."),
                comfy_io.Autogrow.Input("images", 
                                       comfy_io.Autogrow.TemplatePrefix(comfy_io.Image.Input("image", optional=True), prefix="image", min=1, max=10),
                                       optional=True,
                                       extra_dict={"autoshrink": True},
                                       tooltip="Dynamic image inputs for multimodal models.")
            ],
            outputs=[
                comfy_io.String.Output(id="text", display_name="text", tooltip="The text generated by the LLM."),
                comfy_io.String.Output(id="thinking", display_name="thinking", tooltip="The reasoning trace (if available).")
            ],
            hidden=[comfy_io.Hidden.unique_id]
        )

    @classmethod
    def validate_inputs(cls, **kwargs) -> bool | str:
        return True

    @classmethod
    async def execute(cls, prompt, ollama_model, generation_seed, enable_think, use_sys_prompt_below, saved_sys_prompt, system_prompt, images=None, **kwargs) -> comfy_io.NodeOutput:
        ollama_url = get_ollama_url()
        url = f"{ollama_url}/api/generate"

        system_prompt_content = ""
        if use_sys_prompt_below:
            system_prompt_content = system_prompt
        else:
            prompt_templates = get_prompt_files()
            if saved_sys_prompt in prompt_templates:
                system_prompt_content = prompt_templates[saved_sys_prompt]

        payload = {
            "model": ollama_model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "0m",
            "options": {
                "seed": generation_seed
            }
        }

        # Handle 'think' parameter logic
        payload["think"] = enable_think

        if system_prompt_content:
            payload["system"] = system_prompt_content
        
        # Collect all images from the 'images' dict (Autogrow) and any stray images in kwargs
        provided_images = []
        
        # Check the packed 'images' dictionary
        if isinstance(images, dict):
            for key in sorted(images.keys()):
                img_tensor = images[key]
                if isinstance(img_tensor, torch.Tensor):
                    for i in range(img_tensor.shape[0]):
                        provided_images.append(img_tensor[i])
        
        # Check kwargs for any stray image inputs
        for k, v in kwargs.items():
            if k.startswith("image") and isinstance(v, torch.Tensor):
                # Avoid duplicates if already in 'images' dict
                if not isinstance(images, dict) or k not in images:
                    for i in range(v.shape[0]):
                        provided_images.append(v[i])

        if provided_images:
            image_data = [tensor_to_base64(img) for img in provided_images]
            payload["images"] = image_data

        try:
            # Set a timeout (10 minutes) for model inference
            timeout = aiohttp.ClientTimeout(total=600)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        # Return empty strings on error to match output signature
                        return comfy_io.NodeOutput(f"Error: {response.status} - {error_text}", "")
                    
                    data = await response.json()
                    text_output = data.get('response', '')
                    thinking_output = data.get('thinking', '')

            if text_output.strip():
                text_output = cls.clean_text(text_output)

            return comfy_io.NodeOutput(text_output, thinking_output)

        except Exception as e:
            return comfy_io.NodeOutput(f"Connection Error: {e}. Ensure Ollama is running at {ollama_url}")

    @staticmethod
    def clean_text(text):
        clean_text = text.strip()
        if clean_text.startswith("```") and "```" in clean_text[3:]:
            first_block_end = clean_text.find("```", 3)
            if first_block_end > 3:
                language_line_end = clean_text.find("\n", 3)
                if language_line_end > 3 and language_line_end < first_block_end:
                    clean_text = clean_text[language_line_end+1:first_block_end].strip()
                else:
                    clean_text = clean_text[3:first_block_end].strip()

        if (clean_text.startswith('"') and clean_text.endswith('"')) or (clean_text.startswith("'") and clean_text.endswith("'")):
            clean_text = clean_text[1:-1].strip()

        prefixes_to_remove = ["Prompt:", "PROMPT:", "Generated Prompt:", "Final Prompt:"]
        for prefix in prefixes_to_remove:
            if clean_text.startswith(prefix):
                clean_text = clean_text[len(prefix):].strip()
                break
        
        return clean_text

async def get_ollama_models_endpoint(request):
    models = await fetch_ollama_models()
    return web.json_response(models)

if PromptServer:
    try:
        @PromptServer.instance.routes.get("/basic_ollama/models")
        async def get_ollama_models_endpoint_handler(request):
            return await get_ollama_models_endpoint(request)
    except Exception as e:
        print(f"BasicOllama: Could not register API route: {e}")

class BasicOllamaExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[comfy_io.ComfyNode]]:
        return [BasicOllama]

async def comfy_entrypoint() -> BasicOllamaExtension:
    return BasicOllamaExtension()
