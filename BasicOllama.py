import os
import json
import requests
import torch
import base64
import io
import sys
import numpy as np
from PIL import Image
import platform

try:
    from server import PromptServer
    from aiohttp import web
except ImportError:
    print("BasicOllama: Could not import server or aiohttp. API will not work.")
    PromptServer = None

def get_prompt_files():
    """Scans the 'prompts' directory for .txt files and returns a dictionary."""
    prompt_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'prompts')
    if not os.path.exists(prompt_dir):
        return {}
    
    prompt_files = {}
    for filename in os.listdir(prompt_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(prompt_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                # Use filename without extension as the key
                key = os.path.splitext(filename)[0]
                prompt_files[key] = f.read().strip()
    return prompt_files

def rgba_to_rgb(image):
    """Convert RGBA image to RGB with white background"""
    if image.mode == 'RGBA':
        background = Image.new("RGB", image.size, (255, 255, 255))
        image = Image.alpha_composite(background.convert("RGBA"), image).convert("RGB")
    return image

def tensor_to_pil_image(tensor):
    """Convert tensor to PIL Image with RGBA support"""
    tensor = tensor.cpu()
    image_np = tensor.squeeze().mul(255).clamp(0, 255).byte().numpy()

    # Handle different channel counts
    if len(image_np.shape) == 2:  # Grayscale
        image_np = np.expand_dims(image_np, axis=-1)
    if image_np.shape[-1] == 1:   # Single channel
        image_np = np.repeat(image_np, 3, axis=-1)

    channels = image_np.shape[-1]
    mode = 'RGBA' if channels == 4 else 'RGB'

    image = Image.fromarray(image_np, mode=mode)
    return rgba_to_rgb(image)
    
def tensor_to_base64(tensor):
    """Convert tensor to base64 encoded PNG"""
    image = tensor_to_pil_image(tensor)
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def get_ollama_url():
    try:
        config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        ollama_url = config.get("OLLAMA_URL", "http://localhost:11434")
    except FileNotFoundError:
        print("Error: config.json not found, using default Ollama URL.")
        ollama_url = "http://localhost:11434"
    except json.JSONDecodeError:
        print("Error: Could not decode config.json, using default Ollama URL.")
        ollama_url = "http://localhost:11434"
    except Exception as e:
        print(f"An unexpected error occurred: {e}, using default Ollama URL.")
        ollama_url = "http://localhost:11434"
    return ollama_url

def fetch_ollama_models():
    ollama_url = get_ollama_url()
    try:
        # Shortened timeout for the fastest possible check
        response = requests.get(f"{ollama_url}/api/tags", timeout=1)
        response.raise_for_status()
        models = response.json().get('models', [])
        return [model['name'] for model in models]
    except Exception:
        return ["Start Ollama and Refresh"]

if PromptServer:
    try:
        @PromptServer.instance.routes.get("/basic_ollama/models")
        async def get_ollama_models_endpoint(request):
            models = fetch_ollama_models()
            return web.json_response(models)
    except Exception as e:
        print(f"BasicOllama: Could not register API route: {e}")

class BasicOllama:
    def __init__(self):
        self.ollama_url = get_ollama_url()

    @classmethod
    def INPUT_TYPES(cls):
        # Dynamically get the list of prompt structures from the filenames
        prompt_structures = list(get_prompt_files().keys())
        if not prompt_structures:
            prompt_structures = ["None"] # Fallback if no files are found

        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "ollama_model": (["Loading..."],),
                "keep_alive": ("INT", {"default": 0, "min": 0, "max": 60, "step": 1}),
                "saved_sys_prompt": (prompt_structures,),
                "use_sys_prompt_below": ("BOOLEAN", {"default": False}),
                "system_prompt": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        # We allow any value for ollama_model since it is populated dynamically on the frontend
        return True

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "generate_content"
    CATEGORY = "Ollama"

    def generate_content(self, prompt, ollama_model, keep_alive, use_sys_prompt_below, saved_sys_prompt, system_prompt, unique_id=None, **kwargs):
        url = f"{self.ollama_url}/api/generate"

        system_prompt_content = ""
        if use_sys_prompt_below:
            system_prompt_content = system_prompt
            print(f"BasicOllama: Applying User provided system prompt to {ollama_model}")
        else:
            prompt_templates = get_prompt_files()
            if saved_sys_prompt in prompt_templates:
                system_prompt_content = prompt_templates[saved_sys_prompt]
                print(f"BasicOllama: Applying {saved_sys_prompt} system prompt to {ollama_model}")

        payload = {
            "model": ollama_model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": f"{keep_alive}m",
        }

        if system_prompt_content:
            payload["system"] = system_prompt_content
        
        all_images = [kwargs[key] for key in sorted(kwargs.keys()) if key.startswith('image')]
        provided_images = [img for img in all_images if img is not None]

        if provided_images:
            print(f"BasicOllama: Processing {len(provided_images)} image(s) for Ollama API")
            image_data = [tensor_to_base64(img) for img in provided_images]
            payload["images"] = image_data

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()

            textoutput = response.json().get('response', '')

            if textoutput.strip():
                clean_text = textoutput.strip()
                # Remove triple backticks (```) that might wrap the output, often seen in code blocks from LLMs
                if clean_text.startswith("```") and "```" in clean_text[3:]:
                    first_block_end = clean_text.find("```", 3)
                    if first_block_end > 3:
                        # Attempt to remove language identifier if present (e.g., ```json)
                        language_line_end = clean_text.find("\n", 3)
                        if language_line_end > 3 and language_line_end < first_block_end:
                            clean_text = clean_text[language_line_end+1:first_block_end].strip()
                        else:
                            clean_text = clean_text[3:first_block_end].strip()

                # Remove surrounding quotes if the entire output is quoted (e.g., "generated text")
                if (clean_text.startswith('"') and clean_text.endswith('"')) or (clean_text.startswith("'") and clean_text.endswith("'")):
                    clean_text = clean_text[1:-1].strip()

                # Remove common prefixes that LLMs might add (e.g., "Prompt:", "Final Prompt:")
                prefixes_to_remove = ["Prompt:", "PROMPT:", "Generated Prompt:", "Final Prompt:"]
                for prefix in prefixes_to_remove:
                    if clean_text.startswith(prefix):
                        clean_text = clean_text[len(prefix):].strip()
                        break
                
                textoutput = clean_text

            return (textoutput,)
        except requests.exceptions.RequestException as e:
            # Handle connection errors and alert the frontend
            if "WinError 10061" in str(e) or "Connection refused" in str(e):
                if PromptServer and unique_id:
                     PromptServer.instance.send_sync("basic_ollama_connection_error", {"node_id": unique_id})
                return ("Error: Could not connect to Ollama. Please ensure it is running.",)
            
            error_message = f"API Error: {e}"
            if e.response:
                error_message += f"\nStatus Code: {e.response.status_code}"
                try:
                    error_message += f"\nResponse: {e.response.json()}"
                except json.JSONDecodeError:
                    error_message += f"\nResponse: {e.response.text}"
            return (error_message,)
        except Exception as e:
            return (f"An unexpected error occurred: {e}",)

NODE_CLASS_MAPPINGS = {
    "BasicOllama": BasicOllama,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BasicOllama": "Basic Ollama",
}

