import pandas as pd
import pdfplumber
import streamlit as st
import os
import re
import tempfile
import urllib.request

# 🚀 Geçici dosya yollarını belirleme
def get_temp_path(filename):
    """Streamlit'in geçici klasörüne dosya kaydetme"""
    return os.path.join(tempfile.gettempdir(), filename)

# 📂 Dosya var mı kontrolü
def check_files():
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

# 📥 Eksik dosyaları GitHub'dan indir
def download_files():
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

# 📜 PDF'den dersleri çıkart
def extract_table_from_pdf(uploaded_file):
    transcript_data = []
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    lines = text.split("\n")
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
        st.error(f"❌ PDF okuma hatası: {e}")
    return transcript_data

# 📊 Mezuniyet hesaplaması
def analyze_graduation_status(transcript):
    if not transcript:
        st.error("❌ Transcript okunamadı! PDF formatını kontrol edin.")
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

    # 🔍 Debug mesajı ekleyelim
    st.write(f"📌 analyze_graduation_status() dönüş değerleri: {toplam_ects}, {ingilizce_ects}, {mesleki_secmeli_ects}, {secmeli_ects}, {len(başarısız_dersler)} başarısız ders, {len(eksikler)} eksik")

    return toplam_ects, ingilizce_ects, mesleki_secmeli_ects, secmeli_ects, başarısız_dersler, eksikler

# 🏆 **Streamlit Arayüzü**
def main():
    st.title("HIR Mezuniyet Kontrol Sistemi")
    uploaded_file = st.file_uploader("Karteks PDF yükleyin", type=["pdf"])
    
    check_files()
    download_files()
    
    if uploaded_file is not None:
        transcript = extract_table_from_pdf(uploaded_file)
        
        toplam_ects, ingilizce_ects, mesleki_secmeli_ects, secmeli_ects, başarısız_dersler, eksikler = analyze_graduation_status(transcript)
        
        st.write("### 📊 Mezuniyet Durumu")
        st.write(f"**Toplam AKTS:** {toplam_ects}")
        st.write(f"**İngilizce AKTS:** {ingilizce_ects}")
        st.write(f"**Mesleki Seçmeli AKTS:** {mesleki_secmeli_ects}")
        st.write(f"**Seçmeli Ders AKTS:** {secmeli_ects}")

        if eksikler:
            st.warning("🚨 Eksikler:")
            for eksik in eksikler:
                st.write(f"- {eksik}")
        else:
            st.success("🎉 Mezuniyet için tüm kriterler tamamlandı!")

        if başarısız_dersler:
            st.error("❌ Başarısız Dersler:")
            for ders in başarısız_dersler:
                st.write(f"- {ders[0]} | {ders[1]} | Not: {ders[2]}")

if __name__ == "__main__":
    main()
