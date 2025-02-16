import pandas as pd
import pdfplumber
import streamlit as st
import os

def load_excel_data():
    """Mezuniyet ve katalog dosyalarını yükler"""
    mezuniyet_path = "HIR-MEZUNIYET.xlsx"
    katalog_path = "HIR-KATALOG.xlsx"
    
    if not os.path.exists(mezuniyet_path):
        st.error("HIR-MEZUNIYET.xlsx dosyası bulunamadı!")
        return None, None
    if not os.path.exists(katalog_path):
        st.error("HIR-KATALOG.xlsx dosyası bulunamadı!")
        return None, None
    
    mezuniyet_df = pd.read_excel(mezuniyet_path, engine="openpyxl")
    katalog_df = pd.read_excel(katalog_path, engine="openpyxl")
    return mezuniyet_df, katalog_df

def extract_table_from_pdf(uploaded_file):
    """PDF'den ders tablolarını çıkarır ve uygun formatta işler."""
    transcript_data = []
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        if not row or len(row) < 5:
                            continue
                        ders_kodu = row[0].strip() if row[0] else ""
                        ders_adi = row[1].strip() if row[1] else ""
                        kredi = row[2].replace(",", ".") if row[2] else "0"
                        statü = row[4].strip() if row[4] else ""
                        dil = "İng" if "(İng)" in ders_adi else "Tür"
                        yerine_1 = row[5] if len(row) > 5 and row[5] else ""
                        yerine_2 = row[6] if len(row) > 6 and row[6] else ""
                        
                        try:
                            kredi = float(kredi) if kredi.replace(".", "").isdigit() else 0.0
                        except ValueError:
                            continue
                        
                        if not ders_kodu or kredi == 0 or yerine_1 or yerine_2:
                            continue
                        
                        transcript_data.append((ders_kodu, ders_adi, kredi, statü, dil))
    except Exception as e:
        st.error(f"PDF okuma sırasında hata oluştu: {e}")
    return transcript_data

def analyze_graduation_status(transcript):
    """Mezuniyet kriterlerini kontrol eder ve eksik dersleri hesaplar."""
    if not transcript:
        return 0.0, 0, 0, 0, ["Transcript verisi okunamadı, PDF yapısını kontrol edin."]
    
    toplam_ects = sum(c[2] for c in transcript)
    ingilizce_ects = sum(c[2] for c in transcript if c[4] == "İng")
    mesleki_seçmeli_ects = sum(c[2] for c in transcript if c[3] == "MS")
    seçmeli_sayısı = sum(1 for c in transcript if c[3] == "S")
    
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
        transcript = extract_table_from_pdf(uploaded_file)
        toplam_ects, ingilizce_ects, mesleki_seçmeli_ects, seçmeli_sayısı, eksikler = analyze_graduation_status(transcript)
        
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
