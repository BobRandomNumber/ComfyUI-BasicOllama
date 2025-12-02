import os
import json
import requests
import torch
import base64
import io
import sys
import numpy as np
from PIL import Image
import ctypes
import platform

def print_colored(color, text=""):
    if platform.system() != 'Windows':
        if color == "success":
            print("✔ SUCCESS  Oh🦙 API is listening.")
        elif color == "failed":
            print("⚠ FAILED  Could not connect to Oh🦙.")
        elif color == "info":
            print(f"ℹ INFO: {text}")
        return

    # Define necessary structures
    class COORD(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class SMALL_RECT(ctypes.Structure):
        _fields_ = [("Left", ctypes.c_short), ("Top", ctypes.c_short),
                    ("Right", ctypes.c_short), ("Bottom", ctypes.c_short)]

    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [("dwSize", COORD),
                    ("dwCursorPosition", COORD),
                    ("wAttributes", ctypes.c_ushort),
                    ("srWindow", SMALL_RECT),
                    ("dwMaximumWindowSize", COORD)]

    # Constants for colors
    FOREGROUND_WHITE = 0x0007
    FOREGROUND_GREEN = 0x000A
    FOREGROUND_RED = 0x000C
    FOREGROUND_YELLOW = 0x000E
    FOREGROUND_BRIGHT_GREEN = 0x0002 | 0x0008
    BACKGROUND_GREEN = 0x0020
    BACKGROUND_RED = 0x0040
    BACKGROUND_BLUE = 0x0010
    BACKGROUND_PURPLE = BACKGROUND_RED | BACKGROUND_BLUE

    # Get handle to stdout
    STD_OUTPUT_HANDLE = -11
    handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    
    # Get original console attributes
    csbi = CONSOLE_SCREEN_BUFFER_INFO()
    if ctypes.windll.kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(csbi)):
        reset = csbi.wAttributes

        # Set color
        if color == "success":
            ctypes.windll.kernel32.SetConsoleTextAttribute(handle, BACKGROUND_GREEN | FOREGROUND_WHITE)
            print(" ✔ SUCCESS ", end="")
            sys.stdout.flush()
            ctypes.windll.kernel32.SetConsoleTextAttribute(handle, FOREGROUND_GREEN | (reset & 0xFFF0))
            print(" Oh🦙 API is listening.")
        elif color == "failed":
            ctypes.windll.kernel32.SetConsoleTextAttribute(handle, BACKGROUND_RED | FOREGROUND_WHITE)
            print(" ⚠ FAILED ", end="")
            sys.stdout.flush()
            ctypes.windll.kernel32.SetConsoleTextAttribute(handle, FOREGROUND_RED | (reset & 0xFFF0))
            print(" Could not connect to Oh🦙.")
        elif color == "info":
            ctypes.windll.kernel32.SetConsoleTextAttribute(handle, BACKGROUND_BLUE | FOREGROUND_YELLOW)
            sys.stdout.write(f" ℹ INFO: {text} ")
            sys.stdout.flush()
            ctypes.windll.kernel32.SetConsoleTextAttribute(handle, reset)
            sys.stdout.write("\n")
            sys.stdout.flush()
            return # Prevent double reset
        elif color == "image_info":
            ctypes.windll.kernel32.SetConsoleTextAttribute(handle, BACKGROUND_PURPLE | FOREGROUND_BRIGHT_GREEN)
            sys.stdout.write(f" 🖼 IMAGE: {text} ")
            sys.stdout.flush()
            ctypes.windll.kernel32.SetConsoleTextAttribute(handle, reset)
            sys.stdout.write("\n")
            sys.stdout.flush()
            return # Prevent double reset

        # Reset to original color
        ctypes.windll.kernel32.SetConsoleTextAttribute(handle, reset)
    else:
        # Fallback to simple print if not in a real console
        if color == "success":
            print("✔ SUCCESS Oh🦙 API is listening.")
        elif color == "failed":
            print("⚠ FAILED Could not connect to Oh🦙.")
        elif color == "info":
            print(f"ℹ INFO: {text}")
        elif color == "image_info":
            print(f"🖼 IMAGE: {text}")

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

class BasicOllama:
    _connection_error_printed = False
    _success_message_printed = False

    def __init__(self):
        self.ollama_url = get_ollama_url()

    @classmethod
    def get_ollama_models(cls):
        ollama_url = get_ollama_url()
        try:
            response = requests.get(f"{ollama_url}/api/tags")
            response.raise_for_status()
            models = response.json().get('models', [])
            
            if not cls._success_message_printed:
                print_colored("success")
                cls._success_message_printed = True
            
            cls._connection_error_printed = False # Reset on success
            return [model['name'] for model in models]
        except requests.exceptions.RequestException:
            cls._success_message_printed = False # Reset on failure
            if not cls._connection_error_printed:
                print_colored("failed")
                cls._connection_error_printed = True
            return []

    @classmethod
    def INPUT_TYPES(cls):
        # Dynamically get the list of prompt structures from the filenames
        prompt_structures = list(get_prompt_files().keys())
        if not prompt_structures:
            prompt_structures = ["None"] # Fallback if no files are found

        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "ollama_model": (cls.get_ollama_models(),),
                "keep_alive": ("INT", {"default": 0, "min": 0, "max": 60, "step": 1}),
                "saved_sys_prompt": (prompt_structures,),
                "use_sys_prompt_below": ("BOOLEAN", {"default": False}),
                "system_prompt": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "generate_content"
    CATEGORY = "Ollama"

    def generate_content(self, prompt, ollama_model, keep_alive, use_sys_prompt_below, saved_sys_prompt, system_prompt, **kwargs):
        url = f"{self.ollama_url}/api/generate"

        system_prompt_content = ""
        if use_sys_prompt_below:
            system_prompt_content = system_prompt
            print_colored("info", "Applying User provided system prompt")
        else:
            prompt_templates = get_prompt_files()
            if saved_sys_prompt in prompt_templates:
                system_prompt_content = prompt_templates[saved_sys_prompt]
                print_colored("info", f"Applying {saved_sys_prompt} system prompt")

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
            print_colored("image_info", f"Processing {len(provided_images)} image(s) for Ollama API")
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

