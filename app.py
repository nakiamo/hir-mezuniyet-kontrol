import pandas as pd
import pdfplumber
import streamlit as st
import os
import re

# 📌 PDF'den metni ayıkla ve dersleri çek
def extract_courses_from_pdf(uploaded_file):
    transcript_data = []
    
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    # Dersleri yakalamak için regex
                    ders_regex = re.findall(r"([A-ZÇĞİÖŞÜ]{2,4}\d{3})\s+\((İng|Tür)\)\s+(.+?)\s+(\d+\.\d)\s+([A-Z]{2})", text)

                    for match in ders_regex:
                        ders_kodu = match[0].strip()
                        dil = match[1].strip()
                        ders_adi = match[2].strip()
                        kredi = float(match[3].replace(',', '.'))
                        notu = match[4].strip()

                        # Başarısız dersleri FF, DZ notuna göre belirle
                        statü = "Başarısız" if notu in ["FF", "DZ"] else "Başarılı"

                        transcript_data.append((ders_kodu, ders_adi, kredi, notu, statü, dil))
    
    except Exception as e:
        st.error(f"PDF okuma hatası: {e}")

    return transcript_data

# 📌 Mezuniyet kriterlerini kontrol et
def analyze_graduation_status(transcript):
    if not transcript:
        return 0.0, 0, 0, 0, [], ["Transcript verisi okunamadı, PDF yapısını kontrol edin!"]

    # Başarılı dersleri filtrele (FF veya DZ olmayanlar)
    basarili_dersler = [c for c in transcript if c[4] == "Başarılı"]

    # Toplam AKTS hesapla
    toplam_ects = sum(c[2] for c in basarili_dersler)
    ingilizce_ects = sum(c[2] for c in basarili_dersler if c[5] == "İng")
    mesleki_seçmeli_ects = sum(c[2] for c in basarili_dersler if c[0].startswith("RHİ"))  # RHİ kodları mesleki seçmeli
    secmeli_sayisi = sum(1 for c in basarili_dersler if c[0].startswith("KÜL"))  # Seçmeli dersler KÜL ile başlıyor olabilir

    # Başarısız dersleri listele
    başarısız_dersler = [(c[0], c[1], c[3]) for c in transcript if c[4] == "Başarısız"]

    # Eksik dersleri kontrol et
    eksikler = []
    if toplam_ects < 240:
        eksikler.append(f"Eksik AKTS: {240 - toplam_ects}")
    if ingilizce_ects < 72:
        eksikler.append(f"Eksik İngilizce AKTS: {72 - ingilizce_ects}")
    if mesleki_seçmeli_ects < 56:
        eksikler.append(f"Eksik Mesleki Seçmeli AKTS: {56 - mesleki_seçmeli_ects}")
    if secmeli_sayisi == 0:
        eksikler.append("En az 1 seçmeli ders alınmalıdır.")

    return toplam_ects, ingilizce_ects, mesleki_seçmeli_ects, secmeli_sayisi, başarısız_dersler, eksikler

# 📌 Streamlit uygulaması
def main():
    st.title("HIR Mezuniyet Kontrol Sistemi")
    uploaded_file = st.file_uploader("Karteks PDF yükleyin", type=["pdf"])
    
    if uploaded_file:
        transcript = extract_courses_from_pdf(uploaded_file)
        toplam_ects, ingilizce_ects, mesleki_seçmeli_ects, secmeli_sayisi, başarısız_dersler, eksikler = analyze_graduation_status(transcript)
        
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

if __name__ == "__main__":
    main()
