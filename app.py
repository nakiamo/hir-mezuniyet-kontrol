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

def extract_table_from_pdf(pdf_path):
    """PDF'den ders tablolarını çıkarır ve uygun formatta işler."""
    with pdfplumber.open(pdf_path) as pdf:
        all_courses = []
        for i, page in enumerate(pdf.pages):
            table = page.extract_table()
            if table:
                for row in table:
                    if not row or len(row) < 5:
                        continue
                    ders_kodu = row[0].strip() if row[0] else ""
                    ders_adi = row[1].strip() if row[1] else ""
                    kredi_str = row[2].replace(",", ".") if row[2] else "0"
                    try:
                        kredi = float(kredi_str) if kredi_str.replace(".", "").isdigit() else 0.0
                    except ValueError:
                        print(f"Hata: Kredi dönüştürme başarısız - {row}")
                        continue
                    statü = row[4].strip() if row[4] else ""
                    dil = "İng" if "(İng)" in ders_adi else "Tür"
                    yerine_1 = row[5] if len(row) > 5 and row[5] else ""
                    yerine_2 = row[6] if len(row) > 6 and row[6] else ""
                    if yerine_1 or yerine_2:
                        continue
                    if not ders_kodu or not kredi or kredi == 0:
                        print(f"Uyarı: Yanlış formatta satır atlandı - {row}")
                        continue
                    all_courses.append((ders_kodu, ders_adi, kredi, statü, dil))
    return all_courses

def analyze_graduation_status(transcript, mezuniyet_df, katalog_df):
    """Mezuniyet kriterlerini kontrol eder ve eksik dersleri hesaplar."""
    if not transcript:
        print("Hata: Transcript verisi boş!")
        return 0.0, 0, 0, 0, ["Transcript verisi okunamadı, PDF yapısını kontrol edin."]
    try:
        toplam_ects = sum([float(c[2]) for c in transcript if isinstance(c[2], (int, float, str)) and str(c[2]).replace(".", "").isdigit()])
        ingilizce_ects = sum([float(c[2]) for c in transcript if c[4] == "İng" and isinstance(c[2], (int, float, str)) and str(c[2]).replace(".", "").isdigit()])
        mesleki_seçmeli_ects = sum([float(c[2]) for c in transcript if c[3] == "MS" and isinstance(c[2], (int, float, str)) and str(c[2]).replace(".", "").isdigit()])
        seçmeli_sayısı = len([c for c in transcript if c[3] == "S"])
    except Exception as e:
        print(f"Hata: Kredi hesaplama sırasında hata oluştu - {e}")
        return 0.0, 0, 0, 0, ["Kredi hesaplama sırasında hata oluştu, PDF formatını kontrol edin."]
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
        transcript = extract_table_from_pdf(uploaded_file)
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
