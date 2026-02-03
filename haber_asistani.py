import feedparser
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from fpdf import FPDF # fpdf2 yüklü olsa da bu şekilde çağrılır
import time
from datetime import datetime, timedelta
import urllib.parse

import os # Sisteme erişim için gerekli

# 1. AYARLAR
# Ortam değişkeninden anahtarı güvenli bir şekilde çeker
GEMINI_API_KEY = os.getenv("GEMINI_KEY") 

if not GEMINI_API_KEY:
    print("❌ HATA: GEMINI_KEY ortam değişkeni bulunamadı!")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# En kararlı model ismini buraya yazın
model = genai.GenerativeModel('gemini-3-flash-preview')

# Takip etmek istediğin kelimeleri buraya ekle
keywords = [
    'site:linkedin.com "ASELSAN"',
    'site:linkedin.com "FORD OTOSAN"',
    'site:linkedin.com "TÜPRAŞ"',
    'site:linkedin.com "VESTEL BEYAZ"',
    'site:linkedin.com "İSKENDERUN DEMİR ÇELİK"',
    'site:linkedin.com "Robotik"',
    'site:linkedin.com "Savunma Sanayii"',
    'site:linkedin.com "Montaj Mühendisliği"',
    'site:linkedin.com "Çip Yatırımı"'
]
RSS_URLS = [
    "https://webrazzi.com/feed/",
    "https://techcrunch.com/feed/",
    "https://www.haberturk.com/rss/kategori/ekonomi.xml"
]

# LinkedIn/Google News tünelini listeye ekliyoruz
for kw in keywords:
    safe_kw = urllib.parse.quote(kw)
    rss_link = f"https://news.google.com/rss/search?q={safe_kw}+when:24h&hl=tr&gl=TR&ceid=TR:tr"
    RSS_URLS.append(rss_link)

def get_news_summary():
    found_news = False
    all_entries_text = "" 
    
    now = time.time()
    # 1. 24 Saat Filtresi (Tam 1 gün geriye dönük)
    twenty_four_hours_ago = now - (24 * 60 * 60)
    
    entry_count = 0
    for url in RSS_URLS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            published_time = entry.get('published_parsed')
            if published_time and time.mktime(published_time) > twenty_four_hours_ago:
                entry_count += 1
                # Link bilgisini alt satıra geçecek şekilde metne ekliyoruz
                all_entries_text += f"\n--- HABER {entry_count} ---\nBAŞLIK: {entry.title}\nDETAY: {entry.description}\nKAYNAK: {entry.link}\n"
                found_news = True

    if not found_news:
        return "Son 24 saat içinde yeni haber bulunamadı."

    # Detaylı ve profesyonel İngilizce Prompt (Aynen korunmuştur)
    final_prompt = f"""
Act as a high-level technical analyst and advisor for an 'Assembly Engineer' and 'Field Operation Architect' (Calculated Field Leader). 
The user is a mechanical engineer specialized in robotics, the defense industry, and project-based system integration, with expertise in on-site implementation and technical project management, who is also a strategic investor in the Turkish Stock Market (BIST).
They also have a strategic interest in chip investments and high-tech hardware.

Your task is to analyze the following {entry_count} news items and provide a comprehensive, high-value report in TURKISH.

NEWS DATA:
{all_entries_text}

SPECIFIC MONITORING - BIST COMPANIES:
Analyze and highlight any developments, financial shifts, or strategic moves related to:
- ASELSAN / ASELS (Defense & Electronics)
- TÜPRAŞ / TUPRS (Energy & Refinery)
- ASTOR ENERJİ / ASTOR (Energy)
- VESTEL BEYAZ EŞYA / VESBE (Manufacturing & Consumer Electronics)
- İSKENDERUN DEMİR ÇELİK / ISDMR (Heavy Industry & Steel)
- FORD OTOSAN / FROTO (Automotive & Automation)
- TURKISH AIRLINES / THYAO (AVIATION)

STRUCTURE:
1. ANALYSIS SECTION: Detailed technical and financial analysis. 
2. SEPARATOR: You MUST use the exact tag [KAYNAKCA_BOLUMU] after the analysis.
3. SOURCES SECTION: List all source links after the tag.

STRICT CONSTRAINTS:
1. ANALYSIS DEPTH: Provide expert-level technical insights regarding field operations, assembly precision, system architecture, and project-specific requirements (Robotics/Defense context).
2. CHARACTER LIMIT: The total response must NOT exceed 15,000 characters (including spaces). This is a hard limit.
3. FORMAT: Use structured headings (e.g., Teknik Analiz, Saha Operasyon Etkileri ve öngörüleri, BIST Şirket Değerlendirmeleri, Yatırım Potansiyeli) and technical bullet points.
4. LANGUAGE: The entire response must be written in TURKISH.
5. TONE: Professional, concise, and highly engineering-focused.
"""

    try:
        # Tek seferde tüm haberlerin analizini alıyoruz
        response = model.generate_content(final_prompt)
        return response.text
    except Exception as e:
        return f"Analiz raporu oluşturulurken bir hata oluştu: {str(e)}"

def create_pdf(analiz, kaynakca):
    # fpdf2 kullanımı
    pdf = FPDF()
    pdf.add_page()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(script_dir, "DejaVuSans.ttf")
    
    try:
        # uni=True sildik, fpdf2 bunu otomatik yönetir
        pdf.add_font('DejaVu', '', font_path)
        pdf.set_font('DejaVu', size=12)
        
        # Başlık - fpdf2'de 'text' parametresi kullanılır
        pdf.set_font('DejaVu', style='B', size=14)
        pdf.cell(0, 10, text="Günlük Teknik & Stratejik Analiz", align='C')
        pdf.ln(15)
    except Exception as e:
        print(f"⚠️ Font yükleme hatası: {e}")
        pdf.set_font("Helvetica", size=12)

    # 1. ANALİZ KISMI (Doğru hizalama ile)
    pdf.set_font('DejaVu', size=11)
    # fpdf2'de multi_cell 'text' parametresini bekler
    pdf.multi_cell(0, 10, text=analiz)

    # 2. KAYNAKÇA KISMI
    if kaynakca:
        pdf.add_page()
        pdf.set_font('DejaVu', style='B', size=12)
        pdf.cell(0, 10, text="Haber Kaynakları")
        pdf.ln(10)
        pdf.set_font('DejaVu', size=8) 
        pdf.multi_cell(0, 6, text=kaynakca)

    pdf_output = "Gunluk_Analiz.pdf"
    pdf.output(pdf_output)
    return pdf_output
    
def send_email_with_pdf(content, pdf_path):
    msg = MIMEMultipart()
    msg['Subject'] = f'Teknik Analiz Raporu - {datetime.now().strftime("%d/%m/%Y")}'
    msg['From'] = 'duhanbasboga46@gmail.com'
    msg['To'] = 'duhanbasboga46@gmail.com'

    body = "Merhaba, son 24 saate ait analiz raporunuz ekteki PDF dosyasındadır."
    msg.attach(MIMEText(body, 'plain'))

    with open(pdf_path, "rb") as f:
        attachment = MIMEApplication(f.read(), _subtype="pdf")
        attachment.add_header('Content-Disposition', 'attachment', filename=pdf_path)
        msg.attach(attachment)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            # Buradaki Uygulama Şifrenizi aynı şekilde koruyun
            # Artık şifre açıkta değil, sistemden (environment) çekiliyor
            EMAIL_PASSWORD = os.getenv("EMAIL_PASS")
            server.login("duhanbasboga46@gmail.com", EMAIL_PASSWORD) 
            server.send_message(msg)
        print("✅ PDF raporu başarıyla gönderildi!")
    except Exception as e:
        print(f"❌ Mail hatası: {e}")

if __name__ == "__main__":
    max_retries = 3
    attempt = 1
    success = False

    while attempt <= max_retries and not success:
        try:
            # f harfini unutma: f"..." değişkenleri okumasını sağlar
            print(f"🔄 Deneme {attempt}: Analiz hazırlanıyor...")
            report = get_news_summary()

            if not report or (len(report) < 200 and "hata" in report.lower()):
                 raise Exception("AI geçerli bir içerik döndüremedi.")
            
            if "yeni haber bulunamadı" in report:
                print("📭 " + report)
                success = True 
            else:
                # --- PARÇALAMA BURADA OLMALI ---
                if "[KAYNAKCA_BOLUMU]" in report:
                    parts = report.split("[KAYNAKCA_BOLUMU]")
                    analiz_metni = parts[0].strip()
                    kaynakca_metni = parts[1].strip()
                else:
                    analiz_metni = report
                    kaynakca_metni = ""

                # Fonksiyonu iki veriyle çağırıyoruz
                pdf_dosyasi = create_pdf(analiz_metni, kaynakca_metni)
                
                send_email_with_pdf(report, pdf_dosyasi)
                
                print(f"✅ İşlem {attempt}. denemede başarıyla tamamlandı!")
                success = True

        except Exception as e:
            print(f"⚠️ Hata: {e}")
            if attempt < max_retries:
                time.sleep(15)
            attempt += 1










    




