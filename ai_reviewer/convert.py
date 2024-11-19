import os
import hashlib
import requests
import json



def download_pdf(url):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    pdf_path = f"pdfs/{url_hash}.pdf"

    if os.path.exists(pdf_path):
        print("PDF already downloaded.")
        return pdf_path
    
    os.makedirs("pdfs", exist_ok=True)

    response = requests.get(url)
    with open(pdf_path, "wb") as f:
        f.write(response.content)
    return pdf_path


def parse_pdf(pdf_path):
    # curl -X POST -F "file=@2401.01854.pdf" http://localhost:8000/parse_document/pdf 
    url = "http://localhost:8000/parse_document/pdf"
    files = {"file": open(pdf_path, "rb")}
    response = requests.post(url, files=files, timeout=240)
    output_json = response.json()
    # text = response.json()["text"]
    # images = response.json()["images"]

    # {
    #   "text": "Hello, world!", 
    #   "images": [
    #     {
    #       "image_name": "image1.png",
    #       "image_info": {},
    #       "image": "base64-encoded-image-data"
    #     }
    #   ]
    # }

    # with open(f"test.json", "w") as f:
    #     json.dump(output_json, f)

    return output_json


if __name__ == "__main__":
    pdf_path = download_pdf("https://arxiv.org/abs/2401.01854")
    output_json = parse_pdf(pdf_path)
    print(output_json)