# KPSS RAG Chatbot

Bu proje, yerel PDF dosyalarınızı okuyarak size yapay zeka destekli soru-cevap asistanlığı yapan bir sistemdir.
Web arayüzü sayesinde geçmiş sohbetlerinizi görüntüleyebilir, internet kullanılmadan sadece kendi dosyalarınızdan bilgi alabilirsiniz.

## Özellikler
- **FastAPI** ile süper hızlı backend mimarisi.
- **PyMuPDF** ile büyük PDF'lerin hızlı okunması.
- **FAISS** ve **MiniLM-L12-v2** modeli ile yüksek hızlı yerel vektör arama.
- **Gemini 2.5 Flash** ile sadece PDF'e dayalı akıllı cevaplar.
- Estetik ve modern HTML/CSS/JS Arayüz.

## Kurulum ve Çalıştırma

1. Python yüklü olduğundan emin olun ve terminalde proje klasörüne gidin.
2. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
3. `.env` adında bir dosya oluşturup içine Gemini API anahtarınızı ekleyin:
   ```env
   GOOGLE_API_KEY="BURAYA_API_ANAHTARINIZ_GELECEK"
   ```
4. Uygulamayı aşağıdaki komutla başlatın:
   ```bash
   uvicorn app:app --reload
   ```

5. Tarayıcınızda `http://localhost:8000` adresine giderek sistemi kullanmaya başlayabilirsiniz! (Önce **PDF İşle** butonuna basmayı unutmayın).
