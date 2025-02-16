import pandas as pd
import pdfplumber
import streamlit as st
import os
import re
import tempfile
import urllib.request
from pdf2image import convert_from_path
import pytesseract
import shutil

# 📌 Poppler kurulu mu kontrol et
def is_poppler_installed():
    return shutil.which("pdftoppm") is not None

def get_temp_path(filename):
    """Streamlit'in geçici klasörüne dosya kaydetme"""
    return os.path.join(tempfile.gettempdir(), filename)

def check_files():
    """Streamlit çalışma ortamında dosyaların olup olmadığını kontrol eder"""
    mezuniyet_path = get_temp_path("HIR-MEZUNIYET.xlsx")
    katalog_path = get_temp_path("HIR-KATALOG.xlsx")

    st.write("📂 **Streamlit Çalışma Ortamındaki Dosyalar:**")
    try:
        files_in_dir = os.listdir(tempfile.gettempdir())
        for file in files_in_dir:
            st.write(f"📄 {file}")
    except FileNotFoundError:
        st.write("🚨 Geçici dosya klasörü bulunamadı!")

    st.write("🔍 **Dosya Kontrolü:**")
    st.write(f"📂 Mezuniyet Dosyası Var mı? → {os.path.exists(mezuniyet_path)}")
    st.write(f"📂 Katalog Dosyası Var mı? → {os.path.exists(katalog_path)}")

    if not is_poppler_installed():
        st.warning("⚠️ Poppler yüklü değil! Lütfen yükleyin: `apt-get install -y poppler-utils`")

def download_files():
    """GitHub'dan eksik dosyaları indir"""
    github_base_url = "https://raw.githubusercontent.com/nakiamo/hir-mezuniyet-kontrol/main/"
    
    files_to_download = ["HIR-MEZUNIYET.xlsx", "HIR-KATALOG.xlsx"]
    
    for file in files_to_download:
        file_path = get_temp_path(file)
        if not os.path.exists(file_path):
            try:
                urllib.request.urlretrieve(github_base_url + file, file_path)
                st.success(f"✅ {file} GitHub'dan indirildi!")
            except Exception as e:
                st.error(f"❌ {file} indirilemedi: {e}")

def extract_text_from_pdf(uploaded_file):
    """📌 pdf2image + OCR kullanarak PDF'den metin çıkarma"""
    transcript_data = []
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(uploaded_file.read())
            temp_pdf_path = temp_pdf.name
        
        # 📌 PDF'den sayfaları resme çevir
        images = convert_from_path(temp_pdf_path)
        
        # 📌 OCR kullanarak metni çıkar
        extracted_text = []
        for img in images:
            text = pytesseract.image_to_string(img)
            extracted_text.append(text)
        
        full_text = "\n".join(extracted_text)

        # 📌 Metni işleyerek dersleri ayıklama
        lines = full_text.split("\n")
        for line in lines:
            match = re.match(r"(\w{3}\d{3})\s+(.+?)\s+(\d+\.\d)\s+(\w+)\s+(\w+)\s*(\w+)?\s*(\w+)?", line)
            if match:
                ders_kodu = match.group(1).strip()
                ders_adi = match.group(2).strip()
                kredi = float(match.group(3))
                notu = match.group(4).strip()
                statü = match.group(5).strip()
                dil = "İng" if "(İng)" in ders_adi else "Tür"
                yerine_1 = match.group(6) if match.group(6) else ""
                yerine_2 = match.group(7) if match.group(7) else ""
                transcript_data.append((ders_kodu, ders_adi, kredi, notu, statü, dil, yerine_1, yerine_2))

    except Exception as e:
        st.error(f"📌 OCR okuma hatası! pdfplumber kullanılıyor... {e}")
        transcript_data = extract_table_from_pdf(uploaded_file)

    return transcript_data

def extract_table_from_pdf(uploaded_file):
    """📌 pdfplumber ile yedekleme: PDF'den ders tablolarını çıkarır"""
    transcript_data = []
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        transcript_data.append(row)
    except Exception as e:
        st.error(f"📌 pdfplumber PDF okuma sırasında hata oluştu: {e}")
    
    return transcript_data

def analyze_graduation_status(transcript):
    """📌 Mezuniyet kriterlerini kontrol eder ve eksik dersleri hesaplar"""
    if not transcript:
        return 0.0, 0, 0, 0, [], ["Transcript verisi okunamadı, PDF yapısını kontrol edin."]
    
    basarili_dersler = [c for c in transcript if c[3] not in ["FF", "DZ"]]
    toplam_ects = sum(c[2] for c in basarili_dersler)
    ingilizce_ects = sum(c[2] for c in basarili_dersler if c[5] == "İng")
    secmeli_ects = sum(c[2] for c in basarili_dersler if c[4] == "S")
    mesleki_secmeli_ects = sum(c[2] for c in basarili_dersler if c[4] not in ["Z", "S"])
    
    başarısız_dersler = [(c[0], c[1], c[3]) for c in transcript if c[3] in ["FF", "DZ"]]
    eksikler = []
    
    if toplam_ects < 240:
        eksikler.append(f"Eksik AKTS: {240 - toplam_ects}")
    if ingilizce_ects < 72:
        eksikler.append(f"Eksik İngilizce AKTS: {72 - ingilizce_ects}")
    if mesleki_secmeli_ects < 69.5:
        eksikler.append(f"Eksik Mesleki Seçmeli AKTS: {69.5 - mesleki_secmeli_ects}")
    if secmeli_ects < 7:
        eksikler.append(f"Eksik Seçmeli AKTS: {7 - secmeli_ects}")
    
    return toplam_ects, ingilizce_ects, mesleki_secmeli_ects, secmeli_ects, başarısız_dersler, eksikler

def main():
    st.title("HIR Mezuniyet Kontrol Sistemi")
    uploaded_file = st.file_uploader("Karteks PDF yükleyin", type=["pdf"])
    
    check_files()
    download_files()
    
    if uploaded_file is not None:
        transcript = extract_text_from_pdf(uploaded_file)
        toplam_ects, ingilizce_ects, mesleki_secmeli_ects, secmeli_ects, başarısız_dersler, eksikler = analyze_graduation_status(transcript)

        st.write(f"📊 **Mezuniyet Durumu**\n**Toplam AKTS:** {toplam_ects}\n**İngilizce AKTS:** {ingilizce_ects}\n**Mesleki Seçmeli AKTS:** {mesleki_secmeli_ects}\n**Seçmeli AKTS:** {secmeli_ects}")
        for eksik in eksikler:
            st.warning(f"⚠️ {eksik}")

if __name__ == "__main__":
    main()
