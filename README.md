# ComfyUI-BasicOllama

A streamlined and simplified custom node for ComfyUI that provides direct access to local Ollama models. This node allows you to send prompts and images to your local Ollama instance and receive text-based responses.

This project is a heavily modified and stripped-down version of the original [ComfyUI-OllamaGemini](https://github.com/al-swaiti/ComfyUI-OllamaGemini) by [@al-swaiti](https://github.com/al-swaiti). All credit for the original concept and implementation goes to them.

This simplified version can be found at [https://github.com/BobRandomNumber/ComfyUI-BasicOllama](https://github.com/BobRandomNumber/ComfyUI-BasicOllama).

## 🚀 Features

*   **Direct Ollama Integration:** Seamlessly connect to your local Ollama instance.
*   **Text and Image Support:** Send both text prompts and images to multimodal Ollama models.
*   **Multiple Image Inputs:** Input up to five images for analysis.
*   **Structured Output:**  Get cleaned, structured output from the Ollama model.
*   **Easy Configuration:**  Quickly set up your Ollama URL.

## 📦 Installation

1.  **Clone the Repository:**
    Navigate to your `ComfyUI/custom_nodes` directory and clone this repository:
    ```bash
    git clone https://github.com/BobRandomNumber/ComfyUI-BasicOllama
    ```

2.  **Install Dependencies:**
    Navigate to the newly cloned directory and install the required packages:
    ```bash
    cd ComfyUI-BasicOllama
    pip install -r requirements.txt
    ```

3.  **Restart ComfyUI:**
    Restart your ComfyUI instance to load the new custom node.

## ✨ Usage

The `BasicOllama` node can be found under the `Ollama` category in the ComfyUI menu.

### Inputs

| Name               | Type                                  | Description                                                                                                                              |
| ------------------ | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `prompt`           | `STRING`                              | The text prompt to send to the Ollama model.                                                                                             |
| `input_type`       | `COMBO` (`text`, `image`)             | The type of input to send to the model. `text` for text-only prompts, and `image` to include images.                                    |
| `ollama_model`     | `COMBO`                               | A list of available Ollama models on your local instance.                                                                                |
| `keep_alive`       | `INT`                                 | The duration (in minutes) that the Ollama model should remain loaded in memory after the request is complete.                            |
| `structure_output` | `BOOLEAN`                             | If `True`, the output will be cleaned and structured.                                                                                    |
| `prompt_structure` | `COMBO`                               | A selection of prompt templates to structure your prompt for various models.                                                              |
| `structure_format` | `STRING`                              | A custom format for the structured output.                                                                                               |
| `output_format`    | `COMBO` (`raw_text`, `json`)          | The format of the output. `raw_text` for plain text, and `json` for a JSON object.                                                         |
| `image1` - `image5`| `IMAGE` (Optional)                    | Up to five optional image inputs for multimodal models.                                                                                  |

### Outputs

| Name   | Type     | Description                               |
| ------ | -------- | ----------------------------------------- |
| `text` | `STRING` | The text-based response from the Ollama model. |

## ⚙️ Configuration

By default, the `BasicOllama` node will attempt to connect to your Ollama instance at `http://localhost:11434`.

If your Ollama instance is running on a different URL, you can change it by editing the `config.json` file located in the `ComfyUI-BasicOllama` directory:

```json
{
  "OLLAMA_URL": "http://your-ollama-url:11434"
}
```

## 🙏 Attribution

A special thank you to [@al-swaiti](https://github.com/al-swaiti) for creating the original [ComfyUI-OllamaGemini](https://github.com/al-swaiti/ComfyUI-OllamaGemini) which served as the foundation for this.
This project is licensed under the [MIT License](LICENSE).
