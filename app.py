from pdf2image import convert_from_path
import pytesseract

images = convert_from_path("test.pdf", poppler_path="/usr/bin/poppler-utils")
for img in images:
    text = pytesseract.image_to_string(img)
    st.write("OCR Çıktısı:", text)
