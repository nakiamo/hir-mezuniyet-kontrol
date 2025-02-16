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

def analyze_pdf_structure(pdf_path):
    """PDF'nin yapısını analiz eder ve çıktı olarak ham metni döndürür."""
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            table = page.extract_table()
            print(f"=== Sayfa {i+1} Ham Metni ===")
            print(text if text else "Metin bulunamadı")
            print("=== Sayfa {i+1} Tablo Verisi ===")
            print(table if table else "Tablo bulunamadı")
            print("=====================================")

def extract_table_from_pdf(pdf_path):
    """PDF'den tablo verisini çıkarır."""
    with pdfplumber.open(pdf_path) as pdf:
        all_tables = []
        for i, page in enumerate(pdf.pages):
            table = page.extract_table()
            if table:
                for row in table:
                    all_tables.append(row)
    return all_tables

def extract_transcript_data(pdf_path):
    """Transkript PDF dosyasından dersleri ve kredileri çıkarır."""
    courses = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text = text.replace("□", "İ")  # Türkçe karakter sorunu düzeltiliyor
                lines = text.split("\n")
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
    """Mezuniyet kriterlerini kontrol eder ve eksik dersleri hesaplar."""

    # 🔍 Debugging: Transcript çıktısını inceleyelim
    print("=== DEBUG: Transcript Verisi ===")
    print(transcript)

    # Eğer transcript boşsa, hata vermeden işlemi durduralım
    if not transcript:
        print("Hata: Transcript verisi boş!")
        return 0.0, 0, 0, 0, ["Transcript verisi okunamadı, PDF yapısını kontrol edin."]

    # 🔍 Her satırın doğru formatta olup olmadığını kontrol edelim
    if not all(isinstance(c, (list, tuple)) and len(c) >= 5 for c in transcript):
        print("Hata: Transcript verisi yanlış formatta!")
        return 0.0, 0, 0, 0, ["Transcript verisi yanlış formatta, PDF yapısını kontrol edin."]

    toplam_ects = sum([float(c[2]) for c in transcript if isinstance(c[2], (int, float))])
    ingilizce_ects = sum([float(c[2]) for c in transcript if c[4] == "İng"])
    mesleki_seçmeli_ects = sum([float(c[2]) for c in transcript if c[3] == "MS"])
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
        
        # 1️⃣ PDF yapısını analiz et ve debug çıktısı al
        analyze_pdf_structure(uploaded_file)
        
        # 2️⃣ Tablolar varsa onları oku, yoksa metin tabanlı analiz yap
        transcript = extract_table_from_pdf(uploaded_file)
        if not transcript:
            transcript = extract_transcript_data(uploaded_file)
        
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
