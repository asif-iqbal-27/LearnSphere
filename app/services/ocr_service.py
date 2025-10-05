import os
import base64
from pathlib import Path
from mistralai import Mistral
from app.core.settings import settings


class OCRService:
    def __init__(self):
        self.client = Mistral(api_key=settings.MISTRAL_API_KEY)
    
    def data_uri_to_bytes(self, data_uri: str) -> bytes:
        """Convert data URI to bytes"""
        _, encoded = data_uri.split(",", 1)
        return base64.b64decode(encoded)
    
    def export_image(self, image, image_folder: Path) -> str:
        """Export image to file and return filename"""
        parsed_image = self.data_uri_to_bytes(image.image_base64)

        # ✅ Strip any extension from OCR id (e.g. "img-0.jpeg" → "img-0")
        base_name = Path(image.id).stem  

        # Save cleanly as PNG
        image_path = image_folder / f"{base_name}.png"
        
        with open(image_path, 'wb') as file:
            file.write(parsed_image)
        
        return str(image_path)
    
    def process_pdf(self, pdf_path: str, output_folder: Path) -> tuple:
        """Process PDF with OCR and return markdown content and image paths"""
        try:
            # Upload file to Mistral
            with open(pdf_path, "rb") as file:
                uploaded_file = self.client.files.upload(
                    file={
                        "file_name": os.path.basename(pdf_path),
                        "content": file
                    },
                    purpose="ocr"
                )
            
            # Get signed URL
            file_url = self.client.files.get_signed_url(file_id=uploaded_file.id)
            
            # Process with OCR
            response = self.client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "document_url",
                    "document_url": file_url.url
                },
                include_image_base64=True
            )
            
            # Create directories
            markdown_folder = output_folder / "markdown"
            images_folder = output_folder / "images"
            markdown_folder.mkdir(parents=True, exist_ok=True)
            images_folder.mkdir(parents=True, exist_ok=True)
            
            # Export markdown
            markdown_path = markdown_folder / "content.md"
            markdown_content = ""
            image_paths = []
            
            with open(markdown_path, 'w', encoding='utf-8') as f:
                for page_idx, page in enumerate(response.pages):
                    f.write(f"\n## Page {page_idx + 1}\n\n")
                    f.write(page.markdown)
                    f.write("\n\n")
                    markdown_content += f"\n## Page {page_idx + 1}\n\n{page.markdown}\n\n"
                    
                    # Export images for this page
                    for image in page.images:
                        image_path = self.export_image(image, images_folder)
                        image_paths.append(image_path)
                        # Add image reference to markdown
                        f.write(f"![Image]({image_path})\n\n")
            
            return markdown_content, image_paths, str(markdown_path)
            
        except Exception as e:
            print(f"Error processing PDF: {e}")
            raise e


ocr_service = OCRService()
