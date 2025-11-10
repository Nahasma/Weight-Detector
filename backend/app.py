import os
import io
import json
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from dotenv import set_key
from openai import OpenAI
from PIL import Image

# --- 1. Initialization ---
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
app = Flask(__name__)

# Enable CORS (Cross-Origin Resource Sharing)
# This allows the HTML file to call the backend
CORS(app) 

# --- 2. Configuration & API Client ---
MODEL_POOL = [
    "Qwen/Qwen3-VL-32B-Instruct",
    "Qwen/Qwen3-VL-32B-Thinking",
    "Qwen/Qwen3-VL-8B-Instruct",
    "Qwen/Qwen3-VL-8B-Thinking",
    "Qwen/Qwen3-VL-235B-A22B-Instruct",
    "Qwen/Qwen3-VL-235B-A22B-Thinking",
    "Qwen/Qwen3-Omni-30B-A3B-Instruct",
    "Qwen/Qwen3-Omni-30B-A3B-Thinking"
]
def _dotenv_path():
    # Ensure we always read/write the .env colocated with this app.py
    return os.path.join(os.path.dirname(__file__), '.env')

def create_client_from_env():
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        return None
    return OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1",
        timeout=20.0
    )

# Defer client creation to request time to avoid import-time failures
client = None

# --- 3. Image Validation Helper ---
def validate_image(file_storage):
    """
    Validates the image (format and readability)
    Supports: jpg, png
    """
    try:
        # Read file into memory
        file_bytes = file_storage.read()
        
        # Use Pillow to verify it's a valid image
        image = Image.open(io.BytesIO(file_bytes))
        image.verify() # Verify the image data
        
        # Re-open after verify
        image = Image.open(io.BytesIO(file_bytes))
        
        if image.format.upper() not in ["JPEG", "PNG"]:
            raise ValueError("Invalid image format. Only JPG/PNG allowed.")
            
        return file_bytes, image.format
        
    except Exception as e:
        print(f"Image validation failed: {e}")
        return None, None
    finally:
        # Reset file pointer in case it's used again
        file_storage.seek(0)

# --- 4. Core API Route ---
@app.route('/recognize', methods=['POST'])
def recognize_item():
    
    # 1. Check for file
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # 2. Validate Image File
    image_bytes, image_format = validate_image(file)
    if not image_bytes:
        return jsonify({"error": "Invalid or unsupported image file. Use JPG/PNG."}), 400

    # 3. Call SiliconFlow API 
    try:
        # Ensure API key/client configured
        global client
        if client is None:
            client = create_client_from_env()
        if client is None:
            return jsonify({"error": "API key not configured. Please set it via /config."}), 400

        # Encode image to Base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        mime_type = f"image/{image_format.lower()}"
        image_url = f"data:{mime_type};base64,{base64_image}"

        # Define the system prompt
        # IMPORTANT: We force the model to return ONLY JSON.
        system_prompt = """
        You are an object recognition expert.
        Analyze the user's image and identify the single main object.
        Respond ONLY with a valid JSON object. Do not add any text before or after the JSON.
        The JSON object must have exactly two keys:
        1. "item_name": (string) The common name of the object.
        2. "estimated_weight_kg": (float) The estimated weight of the object in kilograms.
        
        Example:
        {
          "item_name": "Red Apple",
          "estimated_weight_kg": 0.15
        }
        """

        # Model selection from request (with failover list)
        req_model = (request.form.get('model') or '').strip()
        if req_model not in MODEL_POOL:
            req_model = MODEL_POOL[0]

        candidates = [req_model] + [m for m in MODEL_POOL if m != req_model]
        errors = []

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": image_url}}]}
        ]

        for model in candidates:
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=256,
                    temperature=0.1
                )
                response_text = completion.choices[0].message.content

                # Clean potential markdown (```json ... ```)
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]

                data = json.loads(response_text)

                # Validate required keys
                if "item_name" not in data or "estimated_weight_kg" not in data:
                    raise ValueError("AI response missing required keys")

                # Return with the model actually used
                data["used_model"] = model
                return jsonify(data)
            except Exception as e:
                errors.append(f"{model}: {str(e)}")
                continue

        # If all models failed
        return jsonify({
            "error": "AI API Error: all candidate models failed",
            "details": errors
        }), 503

    except json.JSONDecodeError:
        print(f"Failed to parse AI response: {response_text}")
        return jsonify({"error": "AI response was not valid JSON"}), 500
    except Exception as e:
        print(f"Error calling AI API: {e}")
        return jsonify({"error": f"AI API Error: {str(e)}"}), 503

# --- 4.1. API Key Config Route ---
def _mask_key(key: str):
    if not key:
        return None
    if len(key) <= 8:
        return "****"
    return key[:4] + "..." + key[-4:]

@app.route('/config', methods=['GET', 'POST'])
def configure_api_key():
    """Configure and persist the SiliconFlow API key via frontend."""
    if request.method == 'GET':
        current = os.getenv("SILICONFLOW_API_KEY")
        return jsonify({
            "configured": bool(current),
            "masked_key": _mask_key(current)
        })

    # POST
    try:
        data = request.get_json(force=True)
        api_key = (data or {}).get('api_key', '').strip()
        if not api_key:
            return jsonify({"error": "api_key is required"}), 400

        # Persist to .env colocated with app.py
        dotenv_path = _dotenv_path()
        # Ensure file exists; if not, create an empty one
        if not os.path.exists(dotenv_path):
            with open(dotenv_path, 'w', encoding='utf-8') as f:
                f.write('')
        set_key(dotenv_path, 'SILICONFLOW_API_KEY', api_key)

        # Update current process env
        os.environ['SILICONFLOW_API_KEY'] = api_key

        return jsonify({
            "success": True,
            "message": "API key configured successfully",
            "masked_key": _mask_key(api_key)
        })
    except Exception as e:
        print(f"Failed to configure API key: {e}")
        return jsonify({"error": f"Failed to configure API key: {str(e)}"}), 500

# --- 5. Run Server ---
if __name__ == '__main__':
    print("Starting Flask server on http://127.0.0.1:5001")
    app.run(port=5001)