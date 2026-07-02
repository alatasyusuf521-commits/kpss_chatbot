import os
import glob
import fitz  # PyMuPDF
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = "data"
FAISS_INDEX_PATH = "faiss_index"
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
OCR_LANGUAGE = "tur"  # Tesseract Türkçe dil paketi
MIN_TEXT_LENGTH = 20  # Bu uzunluktan az metin çıkarsa taranmış sayfa kabul edilir

# Global variables for caching
_vectorstore = None
_qa_chain = None

def get_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

def init_rag():
    """Initializes the RAG components if the FAISS index exists."""
    global _vectorstore, _qa_chain
    if os.path.exists(FAISS_INDEX_PATH):
        try:
            embeddings = get_embeddings()
            _vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
            _qa_chain = _build_chain(_vectorstore)
            print("RAG Motoru başarıyla başlatıldı.")
            return True
        except Exception as e:
            print(f"RAG Motoru başlatılamadı: {e}")
            return False
    return False

def _build_chain(vectorstore):
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    
    # Strict prompt to prevent hallucination
    system_prompt = (
        "Sen KPSS sınavına hazırlanan öğrencilere yardımcı olan uzman bir asistansın.\n"
        "Sana sağlanan belge parçalarını (context) kullanarak kullanıcının sorusunu yanıtla.\n"
        "Eğer cevap bu metinlerin içinde yoksa veya kesin olarak çıkarılamıyorsa, KESİNLİKLE uydurma veya kendi genel bilgilerini kullanma.\n"
        "Böyle bir durumda sadece şunu söyle: '⚠️ Bu bilgi PDF kaynaklarında bulunamadı.'\n"
        "Cevabın her zaman Türkçe, net, anlaşılır ve akademik olsun.\n\n"
        "Context:\n{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    chain = create_retrieval_chain(retriever, question_answer_chain)
    return chain

def _load_pdf_with_ocr_fallback(pdf_file):
    """
    PDF'i PyMuPDF ile açar. Bir sayfadan çıkan normal metin çok kısaysa
    (taranmış/görüntü tabanlı sayfa olduğu anlaşılırsa) o sayfayı OCR ile okur.
    """
    docs = []
    pdf_doc = fitz.open(pdf_file)
    total_pages = len(pdf_doc)
    ocr_page_count = 0

    for page_number in range(total_pages):
        page = pdf_doc[page_number]
        text = page.get_text().strip()

        if len(text) < MIN_TEXT_LENGTH:
            # Muhtemelen taranmış bir sayfa -> OCR uygula
            try:
                textpage_ocr = page.get_textpage_ocr(
                    flags=0, language=OCR_LANGUAGE, dpi=200, full=True
                )
                ocr_text = page.get_text(textpage=textpage_ocr).strip()
                if len(ocr_text) > len(text):
                    text = ocr_text
                    ocr_page_count += 1
            except Exception as e:
                print(f"OCR hatası (sayfa {page_number + 1}, {pdf_file}): {e}")

        if text:
            docs.append(
                Document(
                    page_content=text,
                    metadata={"source": pdf_file, "page": page_number + 1},
                )
            )

    pdf_doc.close()
    if ocr_page_count > 0:
        print(f"  -> {ocr_page_count}/{total_pages} sayfa OCR ile okundu: {pdf_file}")
    return docs

def process_pdfs():
    """Processes all PDFs in the data directory and builds the FAISS index."""
    global _vectorstore, _qa_chain
    pdf_files = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
    
    if not pdf_files:
        raise FileNotFoundError("data klasöründe işlenecek PDF bulunamadı.")
    
    documents = []
    print(f"{len(pdf_files)} PDF dosyası işleniyor...")
    for pdf_file in pdf_files:
        print(f"Yükleniyor: {pdf_file}")
        documents.extend(_load_pdf_with_ocr_fallback(pdf_file))
    
    print(f"Toplam {len(documents)} sayfa yüklendi. Metinler parçalanıyor...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    
    print(f"Toplam {len(chunks)} parça oluşturuldu. Vektörler hesaplanıyor (Bu işlem biraz sürebilir)...")
    embeddings = get_embeddings()
    _vectorstore = FAISS.from_documents(chunks, embeddings)
    _vectorstore.save_local(FAISS_INDEX_PATH)
    
    _qa_chain = _build_chain(_vectorstore)
    print("PDF işleme ve indeksleme tamamlandı.")
    return True

def ask_question(question, chat_history=None):
    """Answers a question using the RAG chain."""
    global _qa_chain
    if _qa_chain is None:
        return "RAG motoru henüz hazır değil. Lütfen önce PDF'leri işleyin."
    
    try:
        response = _qa_chain.invoke({"input": question})
        return response["answer"]
    except Exception as e:
        return f"Bir hata oluştu: {str(e)}"