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
from newspaper import Article

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
    "ASELSAN",
    "FORD OTOSAN",
    "TÜPRAŞ",
    "Robotik Haberleri",
    "Savunma Sanayii Gelişmeleri",
    "Çip Yatırımı"
    "Yapay Zeka"
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

def get_full_text(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text[:5000] # Çok uzun haberlerde sınırı aşmamak için ilk 5000 karakter
    except:
        return ""
        
def get_news_summary():
    found_news = False
    all_entries_text = "" 
    sources_list = []
    
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
                found_news = True
                
                # --- AI FİLTRESİ BAŞLANGICI ---
                search_text = (entry.title + " " + entry.description).lower()
                ai_keywords = ["yapay zeka", "ai", "llm", "robotik", "otonom", "machine learning"]
                
                # Eğer haber yapay zeka ile ilgiliyse tam metni çek
                if any(kw in search_text for kw in ai_keywords):
                    full_text = get_full_text(entry.link)
                    content = full_text if full_text else entry.description
                    type_label = "[FULL TEXT ANALYSIS]"
                else:
                    content = entry.description
                    type_label = "[SUMMARY]"
                
                all_entries_text += f"\n--- HABER {entry_count} {type_label} ---\nBAŞLIK: {entry.title}\nİÇERİK: {content}\nKAYNAK: {entry.link}\n"
                # Başlığı ve linki birbirinden ayırarak bir paket (tuple) yapıyoruz
                sources_list.append((f"Haber {entry_count}: {entry.title}", entry.link))
                # --- AI FİLTRESİ BİTİŞİ ---

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

STRICT CONSTRAINTS:
1. ANALYSIS DEPTH: Provide expert-level technical insights regarding field operations, assembly precision, system architecture, and project-specific requirements (Robotics/Defense context).
2. CHARACTER LIMIT: The total response must NOT exceed 20,000 characters (including spaces). This is a hard limit.
3. FORMAT: Use structured headings (e.g., Teknik Analiz, Saha Operasyon Etkileri ve öngörüleri, BIST Şirket Değerlendirmeleri, Yatırım Potansiyeli) and technical bullet points.
4. LANGUAGE: The entire response must be written in TURKISH.
5. TONE: Professional, concise, and highly engineering-focused.
6. DEEP ANALYSIS FOR AI: For news items provided with full text (marked as [FULL TEXT]), perform a SWOT analysis regarding their impact on BIST technology stocks and assembly automation.
"""

    try:
        response = model.generate_content(final_prompt)
        # Listeyi olduğu gibi döndürüyoruz (Unpack hatasını önlemek için)
        return response.text, sources_list 
    except Exception as e:
        print(f"❌ AI Hatası: {e}")
        # Hata durumunda boş liste döndürerek sistemin çökmesini engelliyoruz
        return f"Analiz raporu oluşturulurken bir hata oluştu: {str(e)}", []

from fpdf import FPDF

def create_pdf(analiz, kaynakca_listesi):
    pdf = FPDF()
    pdf.add_page()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(script_dir, "DejaVuSans.ttf")
    
    try:
        pdf.add_font('DejaVu', '', font_path)
        
        # --- 1. ANA BAŞLIK: SİYAH ---
        pdf.set_font('DejaVu', size=16)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, text="Günlük Teknik ve Stratejik Analiz", align='C')
        pdf.ln(15)
        
        # ANALİZ METNİ
        pdf.set_font('DejaVu', size=11)
        safe_analiz = analiz.encode('utf-8', 'ignore').decode('utf-8')
        pdf.multi_cell(0, 10, text=safe_analiz)

        # --- 2. KAYNAKÇA BÖLÜMÜ ---
        if kaynakca_listesi and isinstance(kaynakca_listesi, list):
            pdf.add_page()
            pdf.set_font('DejaVu', size=14)
            pdf.set_text_color(34, 139, 34) # Başlık Yeşil
            pdf.cell(0, 10, text="Haber Kaynakları", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)
            
            for item in kaynakca_listesi:
                # 'item' bir demet (tuple) olmalı: (başlık, link)
                if isinstance(item, tuple) and len(item) == 2:
                    baslik, link = item
                    
                    # BAŞLIK KISMI -> YEŞİL
                    pdf.set_font('DejaVu', size=10)
                    pdf.set_text_color(34, 139, 34)
                    safe_baslik = baslik.encode('utf-8', 'ignore').decode('utf-8')
                    pdf.multi_cell(0, 6, text=safe_baslik)

                    # LİNK KISMI -> SİYAH
                    pdf.set_font('DejaVu', size=8)
                    pdf.set_text_color(0, 0, 0)
                    pdf.multi_cell(0, 6, text=link)
                    
                    pdf.ln(4)

    except Exception as e:
        print(f"⚠️ PDF Oluşturma Hatası: {e}")
        pdf.set_font("Helvetica", size=12)
        pdf.set_text_color(0, 0, 0) # Hata durumunda rengi sıfırla

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
            report_text, original_sources = get_news_summary() # Değişiklik 4 buradaydı

            # 219. satır civarı: report -> report_text oldu
            if not report_text or (len(report_text) < 200 and "hata" in report_text.lower()):
                raise Exception("AI geçerli bir içerik döndüremedi.")

            # 222. satır civarı: report -> report_text oldu
            if "yeni haber bulunamadı" in report_text:
                print("🗞️ " + report_text)
                success = True
            else:
                # ARTIK PARÇALAMA YOK.
                # Analiz metni direkt Gemini'den gelen metindir.
                analiz_metni = report_text
                # Kaynakça listesi de bizim topladığımız listedir.
                kaynakca_listesi = original_sources

                # Fonksiyonu çağırıyoruz
                pdf_dosyasi = create_pdf(analiz_metni, kaynakca_listesi)

                # Mail gövdesine analiz metnini, ek olarak PDF'i gönderiyoruz
                send_email_with_pdf(analiz_metni, pdf_dosyasi)

                print(f"✅ İşlem {attempt}. denemede başarıyla tamamlandı!")
                success = True

        except Exception as e:
            print(f"⚠️ Hata: {e}")
            if attempt < max_retries:
                time.sleep(15)
            attempt += 1










    















