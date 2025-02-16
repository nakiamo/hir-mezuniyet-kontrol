import pandas as pd
import pdfplumber
import streamlit as st
import os
import re

# 📌 Excel veri dosyalarını yükle
def load_excel_data():
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

# 📌 PDF'den ders bilgilerini çıkarma fonksiyonu
def extract_table_from_pdf(uploaded_file):
    transcript_data = []
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    st.write(f"**Debug: Sayfa {i+1} Ham Metin**")
                    st.code(text)

                # Tabloyu çekmeyi dene
                tables = page.extract_table()
                if tables:
                    for row in tables:
                        if len(row) < 5:
                            continue  # Boş veya eksik satırları geç

                        ders_kodu = row[0].strip()
                        ders_adi = row[1].strip()
                        try:
                            kredi = float(row[2].replace(',', '.'))
                        except ValueError:
                            kredi = 0.0
                        notu = row[3].strip()
                        statü = row[4].strip()
                        dil = "İng" if "(İng)" in ders_adi else "Tür"
                        yerine_1 = row[5] if len(row) > 5 else ""
                        yerine_2 = row[6] if len(row) > 6 else ""

                        transcript_data.append((ders_kodu, ders_adi, kredi, notu, statü, dil, yerine_1, yerine_2))

                    st.write(f"**Debug: Sayfa {i+1} Tablo Verisi**")
                    st.write(transcript_data)

    except Exception as e:
        st.error(f"PDF okuma sırasında hata oluştu: {e}")
    
    return transcript_data

# 📌 Alternatif dersleri bulma fonksiyonu
def find_alternative_courses(failed_courses, katalog_df):
    alternatives = {}
    for ders_kodu, ders_adi, _ in failed_courses:
        alternative_rows = katalog_df[(katalog_df['Yerine-1'] == ders_kodu) | (katalog_df['Yerine-2'] == ders_kodu)]
        if not alternative_rows.empty:
            alternatives[ders_kodu] = alternative_rows[['Ders Kodu', 'Ders Adı']].values.tolist()
    return alternatives

# 📌 Mezuniyet analiz fonksiyonu
def analyze_graduation_status(transcript, katalog_df):
    if not transcript:
        return 0.0, 0, 0, 0, [], ["Transcript verisi okunamadı, PDF yapısını kontrol edin!"], {}

    # Başarılı dersleri filtrele (FF veya DZ olmayanlar)
    basarili_dersler = [c for c in transcript if c[3] not in ["FF", "DZ"]]

    # Toplam AKTS hesapla
    toplam_ects = sum(c[2] for c in basarili_dersler)
    ingilizce_ects = sum(c[2] for c in basarili_dersler if c[5] == "İng")
    mesleki_seçmeli_ects = sum(c[2] for c in basarili_dersler if c[4] == "MS")
    secmeli_sayisi = sum(1 for c in basarili_dersler if c[4] == "S")

    # Başarısız dersleri listele
    başarısız_dersler = [(c[0], c[1], c[3]) for c in transcript if c[3] in ["FF", "DZ"]]

    # Eksik dersleri kontrol et
    eksikler = []
    if toplam_ects < 240:
        eksikler.append(f"Eksik AKTS: {240 - toplam_ects}")
    if ingilizce_ects < 72:
        eksikler.append(f"Eksik İngilizce AKTS: {72 - ingilizce_ects}")
    if mesleki_seçmeli_ects < 69.5:
        eksikler.append(f"Eksik Mesleki Seçmeli AKTS: {69.5 - mesleki_seçmeli_ects}")
    if secmeli_sayisi == 0:
        eksikler.append("En az 1 seçmeli ders alınmalıdır.")

    # Alternatif dersleri bul
    alternatifler = find_alternative_courses(başarısız_dersler, katalog_df)

    return toplam_ects, ingilizce_ects, mesleki_seçmeli_ects, secmeli_sayisi, başarısız_dersler, eksikler, alternatifler

# 📌 Streamlit uygulaması
def main():
    st.title("HIR Mezuniyet Kontrol Sistemi")
    uploaded_file = st.file_uploader("Karteks PDF yükleyin", type=["pdf"])
    
    mezuniyet_df, katalog_df = load_excel_data()
    
    if uploaded_file and katalog_df is not None:
        transcript = extract_table_from_pdf(uploaded_file)
        toplam_ects, ingilizce_ects, mesleki_seçmeli_ects, secmeli_sayisi, başarısız_dersler, eksikler, alternatifler = analyze_graduation_status(transcript, katalog_df)
        
        st.write("### Mezuniyet Durumu")
        st.write(f"**Toplam AKTS:** {toplam_ects}")
        st.write(f"**İngilizce AKTS:** {ingilizce_ects}")
        st.write(f"**Mesleki Seçmeli AKTS:** {mesleki_seçmeli_ects}")
        st.write(f"**Seçmeli Ders Sayısı:** {secmeli_sayisi}")
        
        if eksikler:
            st.warning("Eksikler:")
            for eksik in eksikler:
                st.write(f"- {eksik}")
        else:
            st.success("Tebrikler! Mezuniyet için tüm kriterleri tamamladınız.")
        
        if başarısız_dersler:
            st.error("Başarısız Dersler:")
            for ders in başarısız_dersler:
                st.write(f"- {ders[0]} | {ders[1]} | Not: {ders[2]}")
            
            if alternatifler:
                st.write("### Alternatif Ders Önerileri")
                for ders_kodu, ders_listesi in alternatifler.items():
                    st.write(f"**{ders_kodu}** yerine alınabilecek dersler:")
                    for kod, ad in ders_listesi:
                        st.write(f"- {kod} | {ad}")

if __name__ == "__main__":
    main()
