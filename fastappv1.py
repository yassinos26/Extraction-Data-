from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import google.generativeai as genai
import threading
from pdf2image import convert_from_path
# Configuration de l'API FastAPI
app = FastAPI()
# Configurez la clé API Google
GOOGLE_API_KEY = ''  # Remplacez par votre clé API Google
if not GOOGLE_API_KEY:
    raise ValueError("API Key not found. Please set the GOOGLE_API_KEY environment variable.")
genai.configure(api_key=GOOGLE_API_KEY)
# Configuration du modèle génératif
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={"temperature": 0.2, "top_p": 1, "top_k": 32, "max_output_tokens": 4096},
    safety_settings=[
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
    ]
)
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
# Schémas pour les requêtes
class ImageRequest(BaseModel):
    image_path: str
    user_prompt: str = None  # Rend user_prompt optionnel
class PDFRequest(BaseModel):
    pdf_path: str
    user_prompt: str = None  # Rend user_prompt optionnel
# Fonction pour vérifier et lire l'image
def image_format(image_path):
    img = Path(image_path)
    if not img.exists():
        raise FileNotFoundError(f"Could not find image: {img}")
    return {"mime_type": "image/png", "data": img.read_bytes()}
# Mise à jour de la fonction gemini_output pour inclure des arguments optionnels
def gemini_output(image_path, system_prompt=None, user_prompt=None):
    image_info = image_format(image_path)
    input_prompt = [system_prompt, image_info]
    if user_prompt:
        input_prompt.append(user_prompt)
    response = model.generate_content(input_prompt)
    return response.text

# Fonction pour convertir le PDF en PNG
def convert_pdf_to_png(pdf_path, output_folder):
    pages = convert_from_path(pdf_path, 300)  # 300 dpi
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    image_paths = []
    for i, page in enumerate(pages):
        image_path = Path(output_folder) / f"page_{i+1}.png"
        page.save(image_path, 'PNG')
        image_paths.append(str(image_path))
    return image_paths

# Fonction pour générer le contenu avec le modèle
def gemini_output_all(image_path, user_prompt=None):
    image_info = image_format(image_path)
    input_prompt = [image_info]
    if user_prompt:
        input_prompt.append(user_prompt)
    response = model.generate_content(input_prompt)
    return response.text

# Fonction pour traiter le PDF
def process_pdf_content_all(pdf_path, user_prompt=None):
    output_folder = "images"
    image_paths = convert_pdf_to_png(pdf_path, output_folder)
    results = []
    for image_path in image_paths:
        output = gemini_output_all(image_path, user_prompt=user_prompt)
        results.append(output)
    return results

# Fonction pour convertir le PDF en PNG
def convert_pdf_to_png(pdf_path, output_folder):
    pages = convert_from_path(pdf_path, 300)  # 300 dpi
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    image_paths = []
    for i, page in enumerate(pages):
        image_path = Path(output_folder) / f"page_{i+1}.png"
        page.save(image_path, 'PNG')
        image_paths.append(str(image_path))
    return image_paths

# Fonction pour traiter le PDF
def process_pdf_content(pdf_path, user_prompt):
    output_folder = "images"
    image_paths = convert_pdf_to_png(pdf_path, output_folder)
    results = []
    for image_path in image_paths:
        # Ici, vous pouvez appeler `gemini_output` si nécessaire pour chaque image
        output = gemini_output(image_path, system_prompt, user_prompt)
        results.append(output)
    return  results 

# Route pour traiter les images avec extraction totale
@app.post("/extract-all_image")
async def extract_all_words_from_image(request: ImageRequest):
    try:
        result = {}
        thread = threading.Thread(target=lambda: result.update({"output": gemini_output_all(
            request.image_path, user_prompt=request.user_prompt)}))
        thread.start()
        thread.join()

        return {"output": result.get('output', 'No output generated')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route pour traiter les PDFs avec extraction totale
@app.post("/extract-all_pdf")
async def extract_all_words_from_pdf(request: PDFRequest):
    try:
        result = {}
        thread = threading.Thread(target=lambda: result.update({"output": process_pdf_content_all(
            request.pdf_path, user_prompt=request.user_prompt)}))
        thread.start()
        thread.join()

        return result  # Retourne les résultats complets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Routes existantes pour traiter les images et PDFs avec prompts spécifiques
@app.post("/process-image")
async def process_image(request: ImageRequest):
    try:
        result = {}
        thread3 = threading.Thread(target=lambda: result.update({"output": gemini_output(
            request.image_path, system_prompt=system_prompt, user_prompt=request.user_prompt)}))
        thread3.start()
        thread3.join()
        return {"output": result.get('output', 'No output generated')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/process-pdf")
async def process_pdf(request: PDFRequest):
    try:
        result = {}
        thread3 = threading.Thread(target=lambda: result.update({"output": process_pdf_content(
            request.pdf_path, user_prompt=request.user_prompt)}))
        thread3.start()
        thread3.join()
        return result  # Retourne les résultats complets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))