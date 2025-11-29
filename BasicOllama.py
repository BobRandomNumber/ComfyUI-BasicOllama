import os
import json
import requests
import torch
import base64
import io
import numpy as np
from PIL import Image


# Common function to apply prompt structure templates
def apply_prompt_template(prompt, prompt_structure="Custom"):
    # Define prompt structure templates
    prompt_templates = {
        "VideoGen": "Create a professional cinematic video generation prompt based on my description. Structure your prompt in this precise order: (1) SUBJECT: Define main character(s)/object(s) with specific, vivid details (appearance, expressions, attributes); (2) CONTEXT/SCENE: Establish the detailed environment with atmosphere, time of day, weather, and spatial relationships; (3) ACTION: Describe precise movements and temporal flow using dynamic verbs and sequential language ('first... then...'); (4) CINEMATOGRAPHY: Specify exact camera movements (dolly, pan, tracking), shot types (close-up, medium, wide), lens choice (35mm, telephoto), and professional lighting terminology (Rembrandt, golden hour, backlit); (5) STYLE: Define the visual aesthetic using specific references to film genres, directors, or animation styles. For realistic scenes, emphasize photorealism with natural lighting and physics. For abstract/VFX, include stylistic terms (surreal, psychedelic) and dynamic descriptors (swirling, morphing). For animation, specify the exact style (anime, 3D cartoon, hand-drawn). Craft a single cohesive paragraph that flows naturally while maintaining technical precision. Return ONLY the prompt text itself no more 200 tokens.",

        "FLUX.1-dev": "As an elite text-to-image prompt engineer, craft an exceptional FLUX.1-dev prompt from my description. Create a hyper-detailed, cinematographic paragraph that includes: (1) precise subject characterization with emotional undertones, (2) specific artistic influences from legendary painters/photographers, (3) technical camera specifications (lens, aperture, perspective), (4) sophisticated lighting setup with exact quality and direction, (5) atmospheric elements and depth effects, (6) composition techniques, and (7) post-processing styles. Use language that balances technical precision with artistic vision. Return ONLY the prompt text itself - no explanations or formatting no more 200 tokens.",

        "SDXL": "Create a premium comma-separated tag prompt for SDXL based on my description. Structure the prompt with these elements in order of importance: (1) main subject with precise descriptors, (2) high-impact artistic medium (oil painting, digital art, photography, etc.), (3) specific art movement or style with named influences, (4) professional lighting terminology (rembrandt, cinematic, golden hour, etc.), (5) detailed environment/setting, (6) exact camera specifications (35mm, telephoto, macro, etc.), (7) composition techniques, (8) color palette/mood, and (9) post-processing effects. Use 20-30 tags maximum, prioritizing quality descriptors over quantity. Include 2-3 relevant artist references whose style matches the desired aesthetic. Return ONLY the comma-separated tags without explanations or formatting.",

        "FLUXKontext": "Generate precise Flux Kontext editing instructions using this complete framework: (1) clear action verbs (change, add, remove, replace, transform, modify) with specific target objects and spatial identifiers, (2) detailed modification specs with quantified values (percentages, measurements, exact colors), (3) character consistency protection using 'while maintaining exact same character/facial features/identity' - critical for character preservation, (4) multi-layered preservation clauses for composition/lighting/atmosphere/positioning, (5) specific descriptors avoiding all pronouns - use detailed physical attributes, (6) precise style names with medium characteristics and cultural context, (7) quoted text replacements with typography preservation, (8) semantic relationship maintenance for natural blending, (9) context-aware modifications that understand whole image content. Focus on descriptive language over complex formatting. Ensure edits blend seamlessly with existing content through contextual understanding. Return ONLY the Flux Kontext instruction no more 50 words.",

        "Imagen4": (
            "Craft a vivid, layered image prompt optimized for Imagen 4. "
            "Structure in this precise order: "
            "(1) SUBJECT: Define the main subject(s) with concrete, vivid traits (appearance, pose, expression). "
            "(2) SCENE: Establish environment and context (setting, time of day, background elements). "
            "(3) ATMOSPHERE & LIGHT: Specify lighting—natural or artificial (e.g. golden hour, dramatic side lighting), and mood. "
            "(4) COMPOSITION & TECHNICAL: Describe camera angle, framing, lens effect (e.g. shallow depth of field, wide-angle), perspective and spatial arrangement. "
            "(5) STYLE & QUALITY: Include artistic style and medium (photorealistic, oil painting, illustration), text layout if needed, resolution cues (e.g. 2K, high resolution), and mood-enhancing terms (cinematic, hyper-realistic). "
            "Aim for specificity and clarity; layer in descriptive detail progressively. "
            "Return ONLY the prompt text itself, in a cohesive single paragraph, under 200 tokens."
        ),

        "GeminiNanaBananaEdit": (
            "Convert my editing request into precise Gemini conversational image editing instructions that leverage its mask-free contextual editing capabilities: "
            "(1) CONTEXTUAL REFERENCE: Begin with 'Using the provided image' and identify the specific element to modify using detailed descriptive language rather than spatial coordinates (the blue ceramic vase on the wooden table, the person wearing the red jacket in the center). "
            "(2) EDIT ACTION: Use clear, conversational verbs that specify the transformation (replace with, transform into, add beside, remove while preserving, change the color to, adjust the lighting to make more). "
            "(3) INTEGRATION SPECIFICATION: Describe how the change should blend seamlessly with existing elements, maintaining consistency in lighting, perspective, style, and atmosphere (ensuring the new element matches the existing warm golden hour lighting and rustic kitchen aesthetic). "
            "(4) PRESERVATION DIRECTIVES: Explicitly state what should remain unchanged to protect critical elements (keep everything else exactly the same, preserve the original character's facial features and expression, maintain the architectural details of the background). "
            "(5) STYLE CONTINUITY: Reference the existing visual style and ensure the modification matches (in the same photorealistic style, maintaining the impressionistic brushwork quality, keeping the vintage film photography aesthetic). "
            "(6) RELATIONSHIP CONTEXT: Describe how the edited element should relate to other objects in the scene for natural composition (positioned naturally beside the existing furniture, scaled appropriately for a person of that height, casting realistic shadows on the ground). "
            "Structure as conversational instructions under 75 words that feel like natural directions to an artist who can see and understand the full image context. "
            "Avoid technical jargon and focus on descriptive, intuitive language that leverages Gemini's contextual understanding. "
            "Return ONLY the editing instruction text."
        )
    }

    # Apply template based on prompt_structure parameter
    modified_prompt = prompt
    if prompt_structure != "Custom" and prompt_structure in prompt_templates:
        template = prompt_templates[prompt_structure]
        print(f"Applying {prompt_structure} template")
        modified_prompt = f"{prompt}\n\n{template}"
    else:
        # Fallback to checking if prompt contains a template request
        for template_name, template in prompt_templates.items():
            if template_name.lower() in prompt.lower():
                print(f"Detected {template_name} template request in prompt")
                modified_prompt = f"{prompt}\n\n{template}"
                break

    return modified_prompt

# ================== UNIVERSAL MEDIA UTILITIES ==================
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
    except:
        print("Error: Ollama URL not found, using default")
        ollama_url = "http://localhost:11434"
    return ollama_url

def update_config_key(key, value):
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json')
    try:
        # Read existing config
        with open(config_path, 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is empty/corrupt, start with a new dict
        config = {}

    # Update the key
    config[key] = value

    # Write the updated config back
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Successfully updated {key} in config.json")
    except Exception as e:
        print(f"Error writing to config.json: {str(e)}")

class BasicOllama: # Renamed from GeminiOllamaAPI
    def __init__(self):
        self.ollama_url = get_ollama_url()

    @classmethod
    def get_ollama_models(cls):
        ollama_url = get_ollama_url()
        try:
            response = requests.get(f"{ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
            return ["llama2"]
        except Exception as e:
            print(f"Error fetching Ollama models: {str(e)}")
            return ["llama2"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "What is the meaning of life?", "multiline": True}),
                "input_type": ([ "text", "image"], {"default": "text"}),
                "ollama_model": (cls.get_ollama_models(),),
                "keep_alive": ("INT", {"default": 0, "min": 0, "max": 60, "step": 1}),
                "structure_output": ("BOOLEAN", {"default": False}),
                "prompt_structure": ([ 
                    "Custom",
                    "VideoGen",
                    "FLUX.1-dev",
                    "SDXL",
                    "FLUXKontext",
                    "Imagen4",
                    "GeminiNanaBananaEdit"
                ], {"default": "Custom"}),
                "structure_format": ("STRING", {"default": "Return only the prompt text itself. No explanations or formatting.", "multiline": True}),
                "output_format": ([ 
                    "raw_text",
                    "json"
                ], {"default": "raw_text"}),
            },
            "optional": {
                "image1": ("IMAGE",),
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
                "image5": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "generate_content"
    CATEGORY = "Ollama"

    def generate_content(self, prompt, input_type, ollama_model, keep_alive, structure_output, prompt_structure, structure_format, output_format, image1=None, image2=None, image3=None, image4=None, image5=None):
        url = f"{self.ollama_url}/api/generate"

        # Apply prompt template
        modified_prompt = apply_prompt_template(prompt, prompt_structure)

        # Add structure format if requested
        if structure_output:
            print(f"Requesting structured output from {ollama_model}")
            # Add the structure format to the prompt
            modified_prompt = f"{modified_prompt}\n\n{structure_format}"
            print(f"Modified prompt with structure format")

        payload = {
            "model": ollama_model,
            "prompt": modified_prompt,
            "stream": False,
            "keep_alive": f"{keep_alive}m"
        }

        try:
            # Process different input types
            if input_type == "text":
                # Text-only input, no additional processing needed
                print(f"Processing text input for Ollama API")

            elif input_type == "image":
                # Handle multiple images
                all_images = [image1, image2, image3, image4, image5]
                provided_images = [img for img in all_images if img is not None]

                if provided_images:
                    print(f"Processing {len(provided_images)} image(s) for Ollama API")
                    image_data = []
                    for img in provided_images:
                        pil_image = tensor_to_pil_image(img)
                        buffered = io.BytesIO()
                        pil_image.save(buffered, format="PNG")
                        image_data.append(base64.b64encode(buffered.getvalue()).decode())

                    payload["images"] = image_data
                    # Update prompt to indicate image analysis
                    modified_prompt = f"Analyze these image(s): {modified_prompt}"
                    payload["prompt"] = modified_prompt

            # Send request to Ollama API
            response = requests.post(url, json=payload)
            response.raise_for_status()

            # Get the response text
            textoutput = response.json().get('response', '')

            # Process the output based on the selected format
            if textoutput.strip():
                # Clean up the text output
                clean_text = textoutput.strip()

                # Remove any markdown code blocks if present
                if clean_text.startswith("```") and "```" in clean_text[3:]:
                    first_block_end = clean_text.find("```", 3)
                    if first_block_end > 3:
                        # Extract content between the first set of backticks
                        language_line_end = clean_text.find("\n", 3)
                        if language_line_end > 3 and language_line_end < first_block_end:
                            # Skip the language identifier line
                            clean_text = clean_text[language_line_end+1:first_block_end].strip()
                        else:
                            clean_text = clean_text[3:first_block_end].strip()

                # Remove any quotes around the text
                if (clean_text.startswith('"') and clean_text.endswith('"')) or \
                   (clean_text.startswith("'") and clean_text.endswith("'")):
                    clean_text = clean_text[1:-1].strip()

                # Remove any "Prompt:" or similar prefixes
                prefixes_to_remove = ["Prompt:", "PROMPT:", "Generated Prompt:", "Final Prompt:"]
                for prefix in prefixes_to_remove:
                    if clean_text.startswith(prefix):
                        clean_text = clean_text[len(prefix):].strip()
                        break

                # Format as JSON if requested
                if output_format == "json":
                    try:
                        # Create a JSON object with the appropriate key based on the prompt structure
                        key_name = "prompt"
                        if prompt_structure != "Custom":
                            key_name = f"{prompt_structure.lower().replace('.', '_').replace('-', '_')}_prompt"

                        json_output = json.dumps({
                            key_name: clean_text
                        }, indent=2)

                        print(f"Formatted output as JSON with key: {key_name}")
                        textoutput = json_output
                    except Exception as e:
                        print(f"Error formatting output as JSON: {str(e)}")
                else:
                    # Just return the clean text
                    textoutput = clean_text
                    print("Returning raw text output")

            return (textoutput,)
        except Exception as e:
            return (f"API Error: {str(e)}",)

# ================== NODE REGISTRATION ==================
NODE_CLASS_MAPPINGS = {
    "BasicOllama": BasicOllama,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BasicOllama": "Basic Ollama",
}