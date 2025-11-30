# ComfyUI-BasicOllama

A simplified node that provides access to Ollama. It allows you to send prompts, system prompts, and images to your Ollama instance and receive text-based responses.

## ⚠️ Requirements

**You must have Ollama installed and running on your local machine for this node to function.** You can download it from [https://ollama.com/](https://ollama.com/).

![](https://github.com/BobRandomNumber/ComfyUI-BasicOllama/blob/main/BasicOllama.png)

## 🚀 Features

* **Direct Ollama Integration:** Seamlessly connect to your local Ollama instance.
* **Automatic Image Detection:** The node automatically detects if an image is connected and sends it to Ollama for multimodal analysis, simplifying the workflow.
* **System Prompt Support:** Utilize the `system` parameter in the Ollama API for more control over model behavior.
* **Dynamic Prompt Templates:** Easily load your own system prompts from `.txt` files in the `prompts` directory.
* **Multiple Image Inputs:** Input up to five images for analysis.
* **Easy Configuration:** Quickly set up your Ollama URL via a `config.json` file.

## 📦 Installation

1. **Clone the Repository:**
   Navigate to your `ComfyUI/custom_nodes` directory and clone this repository:

&nbsp;   ```bash
    git clone https://github.com/BobRandomNumber/ComfyUI-BasicOllama
    ```

2. **Install Dependencies:**
   Navigate to the newly cloned directory and install the required packages:

&nbsp;   ```bash
    cd ComfyUI-BasicOllama
    pip install -r requirements.txt
    ```

3. **Restart ComfyUI:**
   Restart your ComfyUI instance to load the new custom node.

## ✨ Usage

The `BasicOllama` node can be found under the `Ollama` category in the ComfyUI menu. Simply connect an image to one of the `image` inputs to have it automatically included in your prompt.

### Inputs

| Name                   | Type      | Description                                                                                                                                                             |
| ---------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `prompt`               | `STRING`  | The main text prompt to send to the Ollama model.                                                                                                                       |
| `ollama\_model`         | `COMBO`   | A list of available Ollama models on your local instance.                                                                                                               |
| `keep\_alive`           | `INT`     | The duration (in minutes) that the Ollama model should remain loaded in memory after the request is complete.                                                           |
| `saved\_sys\_prompt`     | `COMBO`   | A dropdown list of saved system prompts from the `.txt` files in the `prompts` directory. This is used as the system prompt by default.                                 |
| `use\_sys\_prompt\_below` | `BOOLEAN` | If checked (`True`), the `system\_prompt` text box below will be used instead of the dropdown selection. If unchecked (`False`), the `saved\_sys\_prompt` dropdown is used. |
| `system\_prompt`        | `STRING`  | A multiline text box for a custom, one-off system prompt. This is only active when `use\_sys\_prompt\_below` is checked.                                                     |
| `image1` - `image5`    | `IMAGE`   | Up to five optional image inputs for multimodal models. The node will automatically detect and process any connected images.                                            |

### Outputs

| Name   | Type     | Description                               |
| ------ | -------- | ----------------------------------------- |
| `text` | `STRING` | The text-based response from the Ollama model. |

## ✍️ Adding Custom System Prompts

You can easily add your own reusable system prompts to the `saved\_sys\_prompt` dropdown menu.

1. Navigate to the `ComfyUI-BasicOllama/prompts` directory.
2. Create a new text file (e.g., `my\_prompt.txt`).
3. Write your system prompt inside this file. For example, if you want a system prompt for generating JSON, the content of the file could be:

&nbsp;   ```
    You are a helpful assistant that only responds with valid, well-formatted JSON.
    ```

4. Save the file.
5. Refresh your ComfyUI browser window.

The name of your file (without the `.txt` extension) will now appear as an option in the `saved\_sys\_prompt` dropdown. In the example above, you would see `my\_prompt` in the list.

## ⚙️ Configuration

By default, the `BasicOllama` node will attempt to connect to your Ollama instance at `http://localhost:11434`.

If your Ollama instance is running on a different URL/port, you can change it by editing the `config.json` file located in the `ComfyUI-BasicOllama` directory:

```json
{
  "OLLAMA\_URL": "http://your-ollama-url:11434"
}
```

## 🙏 Attribution

A special thank you to [@al-swaiti](https://github.com/al-swaiti) for creating the original [ComfyUI-OllamaGemini](https://github.com/al-swaiti/ComfyUI-OllamaGemini) whose Ollama node served as the foundation and inspiration for this.
This project is licensed under the [MIT License](LICENSE).

