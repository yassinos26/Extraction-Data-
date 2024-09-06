from flask import Flask, request, jsonify
from pathlib import Path
import google.generativeai as genai
from pdf2image import convert_from_path
import threading
import time

app = Flask(__name__)

# Configure Google API Key
global system_prompt 
system_prompt = """
    Veuillez extraire les informations suivantes :
    1. Le nom du client
    2. Le nom du fournisseur
    3. La date de la facture
    4. Le montant total TTC
    5. Le montant fiscal
    6. Les frais d'immatriculation
    7. Le code TVA
    8. Le timbre fiscal
    9. Le total TVA
    10. Le montant net à payer
    11. Le matricule fiscale
    """
start1= time.time()
GOOGLE_API_KEY = ''
if not GOOGLE_API_KEY:
    raise ValueError("API Key not found. Please set the GOOGLE_API_KEY environment variable.")
genai.configure(api_key=GOOGLE_API_KEY)
# Configure the generative model
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={"temperature": 0.2,"top_p": 1,"top_k": 32,"max_output_tokens": 4096,},
    safety_settings=[
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
    ]
)
end1 = time.time()
print(f"init model took {end1-start1} seconds")
# Function to convert PDF to PNG
def convert_pdf_to_png(pdf_path, output_folder, result):
    start = time.time()
    pages = convert_from_path(pdf_path, 300)  # 300 dpi
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    image_paths = []
    for i, page in enumerate(pages):
        image_path = Path(output_folder) / f"page_{i+1}.png"
        page.save(image_path, 'PNG')
        image_paths.append(str(image_path))
    end = time.time()
    print(f"PDF conversion took {end-start} seconds")
    result['image_paths'] = image_paths
# Function to format the image for processing
def image_format(image_path, result):
    img = Path(image_path)
    formatted_image = [{"mime_type": "image/png", "data": img.read_bytes()}]
    result['formatted_image'] = formatted_image
# Function to process the image and generate the content using the model
def gemini_output(image_path, system_prompt, user_prompt, result):
    start = time.time()
    image_info = result['formatted_image']
    input_prompt = [system_prompt, image_info[0], user_prompt]
    response = model.generate_content(input_prompt)
    end = time.time()
    print(f"gemini output took {end-start} seconds")
    result['output'] = response.text
# Define a route for processing PDF invoices with threading
@app.route('/process-pdf', methods=['POST'])
def process_invoice():
    data = request.json
    pdf_path = data.get('pdf_path')
    user_prompt = data.get('user_prompt')

    if not pdf_path or not user_prompt:
        return jsonify({"error": "Missing 'pdf_path' or 'user_prompt' in the request"}), 400
    output_folder = "images"
    result = {}
    # Thread for converting PDF to PNG
    thread1 = threading.Thread(target=convert_pdf_to_png, args=(pdf_path, output_folder, result))
    thread1.start()
    thread1.join()
    outputs = []
    for image_path in result['image_paths']:
        # Thread for formatting image
        thread2 = threading.Thread(target=image_format, args=(image_path, result))
        thread2.start()
        thread2.join()

        # Thread for generating content using the model
        thread3 = threading.Thread(target=gemini_output, args=(image_path, system_prompt, user_prompt, result))
        thread3.start()
        thread3.join()
        outputs.append(result['output'])
    return jsonify({"outputs": outputs})

# Define a route for processing images directly
@app.route('/process-image', methods=['POST'])
def process_image():
    data = request.json
    image_path = data.get('image_path')
    user_prompt = data.get('user_prompt')

    if not image_path or not user_prompt:
        return jsonify({"error": "Missing 'image_path' or 'user_prompt' in the request"}), 400
    try:
        result = {}
        # Thread for formatting image
        thread2 = threading.Thread(target=image_format, args=(image_path, result))
        thread2.start()
        thread2.join()
        # Thread for generating content using the model
        thread3 = threading.Thread(target=gemini_output, args=(image_path, system_prompt, user_prompt, result))
        thread3.start()
        thread3.join()
        return jsonify({"output": result['output']})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True)