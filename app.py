import pandas as pd
import pdfplumber
import streamlit as st
import os

def load_excel_data():
    """Mezuniyet ve katalog dosyalarını yükler"""
    if not os.path.exists("HIR-MEZUNIYET.xlsx"):
        raise FileNotFoundError("Error: HIR-MEZUNIYET.xlsx file not found!")
    if not os.path.exists("HIR-KATALOG.xlsx"):
        raise FileNotFoundError("Error: HIR-KATALOG.xlsx file not found!")
    
    mezuniyet_df = pd.read_excel("HIR-MEZUNIYET.xlsx", engine="openpyxl")
    katalog_df = pd.read_excel("HIR-KATALOG.xlsx", engine="openpyxl")
    return mezuniyet_df, katalog_df

def convert_pdf_to_txt(pdf_path, output_txt="transcript_cleaned.txt"):
    """PDF'yi temizlenmiş metin dosyasına dönüştür"""
    with pdfplumber.open(pdf_path) as pdf:
        with open(output_txt, "w", encoding="utf-8") as txt_file:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text = text.replace("□", "İ")  # Türkçe karakter sorunu düzeltiliyor
                    txt_file.write(text + "\n")
    return output_txt

def extract_transcript_from_txt(txt_path):
    """Temizlenmiş metin dosyasından ders bilgilerini çıkarır"""
    courses = []
    with open(txt_path, "r", encoding="utf-8") as txt_file:
        lines = txt_file.readlines()
        for line in lines:
            parts = line.split()
            if len(parts) > 3:
                try:
                    ders_kodu = parts[0]
                    ders_adi = " ".join(parts[1:-3])
                    kredi_str = parts[-3].replace(",", ".")  # Virgüllü sayıları noktaya çevir
                    kredi = float(kredi_str) if kredi_str.replace(".", "").isdigit() else 0.0
                    statü = parts[-2]
                    dil = "İng" if "(İng)" in ders_adi else "Tür"
                    
                    # Eğer "Yerine" sütunu doluysa bu dersi dahil etme
                    if len(parts) > 4 and parts[-1] != "-":
                        continue
                    
                    courses.append((ders_kodu, ders_adi, kredi, statü, dil))
                except ValueError as e:
                    print(f"Hata: {line} satırında kredi bilgisi okunamadı - {e}")
    return courses

def analyze_graduation_status(transcript, mezuniyet_df, katalog_df):
    """Mezuniyet kriterlerini kontrol eder ve eksik dersleri hesaplar"""
    toplam_ects = sum([c[2] for c in transcript])
    ingilizce_ects = sum([c[2] for c in transcript if c[4] == "İng"])
    mesleki_seçmeli_ects = sum([c[2] for c in transcript if c[3] == "MS"])
    seçmeli_sayısı = len([c for c in transcript if c[3] == "S"])
    
    eksikler = []
    if toplam_ects < 240:
        eksikler.append(f"Eksik AKTS: {240 - toplam_ects}")
    if ingilizce_ects < 72:
        eksikler.append(f"Eksik İngilizce AKTS: {72 - ingilizce_ects}")
    if mesleki_seçmeli_ects < 69.5:
        eksikler.append(f"Eksik Mesleki Seçmeli AKTS: {69.5 - mesleki_seçmeli_ects}")
    if seçmeli_sayısı == 0:
        eksikler.append("En az 1 seçmeli ders alınmalıdır.")
    
    return toplam_ects, ingilizce_ects, mesleki_seçmeli_ects, seçmeli_sayısı, eksikler

def main():
    st.title("HIR Mezuniyet Kontrol Sistemi")
    uploaded_file = st.file_uploader("Transkript PDF yükleyin", type=["pdf"])
    
    if uploaded_file:
        mezuniyet_df, katalog_df = load_excel_data()
        
        # 1️⃣ PDF'yi TXT formatına dönüştür
        cleaned_txt = convert_pdf_to_txt(uploaded_file)
        
        # 2️⃣ TXT'den transkript verilerini oku
        transcript = extract_transcript_from_txt(cleaned_txt)
        
        toplam_ects, ingilizce_ects, mesleki_seçmeli_ects, seçmeli_sayısı, eksikler = analyze_graduation_status(transcript, mezuniyet_df, katalog_df)
        
        st.write("### Mezuniyet Durumu")
        st.write(f"Toplam AKTS: {toplam_ects}")
        st.write(f"İngilizce AKTS: {ingilizce_ects}")
        st.write(f"Mesleki Seçmeli AKTS: {mesleki_seçmeli_ects}")
        st.write(f"Seçmeli Ders Sayısı: {seçmeli_sayısı}")
        
        if eksikler:
            st.warning("Eksikler:")
            for eksik in eksikler:
                st.write(f"- {eksik}")
        else:
            st.success("Tebrikler! Mezuniyet için tüm kriterleri tamamladınız.")

if __name__ == "__main__":
    main()
