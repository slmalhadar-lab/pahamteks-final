from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import json
import time
import random
import os

app = Flask(__name__)
CORS(app)

# 1. PERBAIKAN: Menggunakan versi model API yang resmi, ringan, dan cepat anti-timeout
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

quiz_cache = {}

# --- SISTEM DATABASE MEMORI & OTP ---
users_db = {}
otp_db = {}

@app.route('/api/send_otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email', '').strip()
    
    if not email:
        return jsonify({'error': 'Email wajib diisi!'}), 400
    if email in users_db:
        return jsonify({'error': 'Email sudah terdaftar! Silakan Sign In.'}), 400
        
    otp_db[email] = "123456" 
    return jsonify({'message': 'Kode verifikasi telah dikirim ke email Anda!'})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    fname = data.get('fname', '').strip()
    lname = data.get('lname', '').strip()
    oname = data.get('oname', '').strip()
    otp_code = data.get('otp', '').strip()
    
    if not email or not password or not fname or not lname:
        return jsonify({'error': 'Nama Depan, Belakang, Email, dan Sandi wajib diisi!'}), 400
        
    if email not in otp_db or otp_db[email] != otp_code:
        return jsonify({'error': 'Kode OTP salah atau kedaluwarsa!'}), 400
        
    if email in users_db:
        return jsonify({'error': 'Email sudah terdaftar!'}), 400
        
    full_name = f"{fname} {lname}"
    if oname: full_name += f" {oname}"
        
    users_db[email] = {'name': full_name, 'password': password}
    del otp_db[email]
    
    return jsonify({'message': 'Verifikasi sukses! Pendaftaran berhasil.', 'name': full_name})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    if email not in users_db:
        return jsonify({'error': 'Email tidak ditemukan!'}), 400
        
    if users_db[email]['password'] != password:
        return jsonify({'error': 'Kata sandi salah!'}), 400
        
    return jsonify({'message': 'Login berhasil!', 'name': users_db[email]['name']})

# --- SERVER LOGS TRACKING ---
@app.route('/api/user_log', methods=['POST'])
def user_log():
    data = request.json
    user_identifier = data.get('user', 'Tamu')
    activity = data.get('activity', '')
    score = data.get('score', 0)
    category = data.get('category', 'General')
    
    print(f"[TRACKER] User: {user_identifier} | Kategori: {category} | Aktivitas: {activity} | Skor: {score}")
    return jsonify({'status': 'logged'})

# --- DAFTAR LENGKAP BAHASA DUNIA ---
LANGUAGES = {
    "afrikaans": "af", "albanian": "sq", "amharic": "am", "arabic": "ar", "armenian": "hy", "azerbaijani": "az",
    "basque": "eu", "belarusian": "be", "bengali": "bn", "bosnian": "bs", "bulgarian": "bg", "catalan": "ca",
    "cebuano": "ceb", "chichewa": "ny", "chinese (simplified)": "zh-cn", "chinese (traditional)": "zh-tw",
    "corsican": "co", "croatian": "hr", "czech": "cs", "danish": "da", "dutch": "nl", "english": "en",
    "esperanto": "eo", "estonian": "et", "filipino": "tl", "finnish": "fi", "french": "fr", "frisian": "fy",
    "galician": "gl", "georgian": "ka", "german": "de", "greek": "el", "gujarati": "gu", "haitian creole": "ht",
    "hausa": "ha", "hawaiian": "haw", "hebrew": "he", "hindi": "hi", "hmong": "hmn", "hungarian": "hu",
    "icelandic": "is", "igbo": "ig", "indonesian": "id", "irish": "ga", "italian": "it", "japanese": "ja",
    "javanese": "jw", "kannada": "kn", "kazakh": "kk", "khmer": "km", "korean": "ko", "kurdish (kurmanji)": "ku",
    "kyrgyz": "ky", "lao": "lo", "latin": "la", "latvian": "lv", "lithuanian": "lt", "luxembourgish": "lb",
    "macedonian": "mk", "malagasy": "mg", "malay": "ms", "malayalam": "ml", "maltese": "mt", "maori": "mi",
    "marathi": "mr", "mongolian": "mn", "myanmar (burmese)": "my", "nepali": "ne", "norwegian": "no",
    "pashto": "ps", "persian": "fa", "polish": "pl", "portuguese": "pt", "punjabi": "pa", "romanian": "ro",
    "russian": "ru", "samoan": "sm", "scots gaelic": "gd", "serbian": "sr", "sesotho": "st", "shona": "sn",
    "sindhi": "sd", "sinhala": "si", "slovak": "sk", "slovenian": "sl", "somali": "so", "spanish": "es",
    "sundanese": "su", "swahili": "sw", "swedish": "sv", "tajik": "tg", "tamil": "ta", "telugu": "te",
    "thai": "th", "turkish": "tr", "ukrainian": "uk", "urdu": "ur", "uzbek": "uz", "vietnamese": "vi",
    "welsh": "cy", "xhosa": "xh", "yiddish": "yi", "yoruba": "yo", "zulu": "zu"
}

def generate_with_retry(prompt, max_retries=3, sleep_time=5):
    for attempt in range(max_retries):
        try:
            return model.generate_content(prompt)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                if attempt < max_retries - 1:
                    time.sleep(sleep_time)
                    continue 
                else:
                    raise Exception("Server Google AI sedang sibuk. Yuk coba 10 detik lagi! ⏳")
            else:
                raise e

@app.route('/api/languages', methods=['GET'])
def get_languages():
    return jsonify(LANGUAGES)

@app.route('/api/translate', methods=['POST'])
def translate_text():
    data = request.json
    if not data or 'text' not in data:
        return jsonify({'error': 'Teks tidak ditemukan'}), 400
        
    teks = data.get('text', '').strip()
    source_lang = data.get('source', 'auto')
    target_lang = data.get('target', 'en')
    
    if not teks: return jsonify({'translated_text': ''})

    source_name = "Auto Detect"
    target_name = "English"
    for name, code in LANGUAGES.items():
        if code == source_lang: source_name = name
        if code == target_lang: target_name = name
            
    try:
        prompt = f"""
        Translate this text from {source_name} to {target_name}: "{teks}"
        Jika ada slang atau idiom, terjemahkan sesuai konteks budaya yang paling natural.
        HANYA berikan hasil terjemahannya saja, tanpa penjelasan tambahan.
        CRITICAL RULE: Jika {target_name} menggunakan huruf non-Latin (seperti Arab, Jepang, Rusia, dll), WAJIB berikan format persis seperti ini:
        [Tulisan Huruf Asli]
        
        [Cara Baca Latin / Romaji]
        """
        response = generate_with_retry(prompt)
        return jsonify({'translated_text': response.text.strip().strip('"')})
    except Exception as e:
        print(f"Error Translator: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate_quiz', methods=['POST'])
def generate_quiz():
    data = request.json
    categories = data.get('categories', [])
    level = data.get('level', 'Pemula')
    
    cache_key = f"{level}_{'_'.join(categories)}"
    
    if cache_key in quiz_cache:
        cached_data = quiz_cache[cache_key].copy()
        random.shuffle(cached_data) 
        return jsonify(cached_data)
        
    # 2. PERBAIKAN PENTING: Mencegah AI merusak JSON dengan tanda kutip ganda di kodingan
    prompt = f"""
    Kamu adalah Guru Ahli Bahasa dan Pemrograman Komputer.
    Buat 5 soal kuis tingkat {level} untuk materi: {', '.join(categories)}.
    
    ATURAN PALING PENTING (CRITICAL):
    1. JIKA SOAL BERUPA KODING/PEMROGRAMAN, GANTI SEMUA tanda kutip ganda (") di dalam teks pertanyaan maupun jawaban menjadi tanda kutip tunggal (').
    2. Format keluaran WAJIB berupa JSON Array utuh. JANGAN gunakan markdown (seperti ```json). Output harus siap di-parse oleh json.loads() di Python.
    
    Bentuk JSON yang benar:
    [{{ "instruction": "Perintah", "question": "Soal (Hanya gunakan kutip tunggal ' )", "options": ["A", "B", "C", "D"], "answer": "Jawaban Benar" }}]
    """
    
    try:
        response = generate_with_retry(prompt)
        raw_text = response.text.strip()
        
        # Bersihkan sisa-sisa markdown jika AI membandel
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`").strip("json").strip("html").strip()
            
        quiz_data = json.loads(raw_text)
        quiz_cache[cache_key] = quiz_data
        return jsonify(quiz_data)
    except Exception as e:
        print(f"Error Quiz JSON Parsing: {e}") # Log untuk Vercel Dashboard
        return jsonify({'error': "Gagal memproses susunan soal dari AI. Coba lagi."}), 500

@app.route('/api/generate_challenge', methods=['POST'])
def generate_challenge():
    data = request.json
    category = data.get('category', 'General')
    
    prompt = f"""
    Kamu adalah Profesor Penguji Ahli.
    Buat 3 soal ujian tantangan (Challenge Mode ber-timer) yang SULIT & menjebak untuk topik: {category}.
    Jika ini pemrograman: berikan analisis potongan kode, perbaikan bug, atau logika algoritma yang rumit.
    
    ATURAN PALING PENTING (CRITICAL):
    1. GANTI SEMUA tanda kutip ganda (") di dalam teks koding/soal menjadi tanda kutip tunggal (').
    2. Format WAJIB berupa JSON Array utuh tanpa markdown (```).
    
    Bentuk JSON yang benar:
    [{{ "instruction": "Tantangan", "question": "Studi kasus...", "options": ["A", "B", "C", "D"], "answer": "Jawaban Benar" }}]
    """
    try:
        response = generate_with_retry(prompt)
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`").strip("json").strip("html").strip()
        return jsonify(json.loads(raw_text))
    except Exception as e:
        print(f"Error Challenge JSON: {e}")
        return jsonify({'error': "Gagal memproses susunan soal tantangan. Coba lagi."}), 500

@app.route('/api/explain_answer', methods=['POST'])
def explain_answer():
    data = request.json
    pertanyaan = data.get('question', '')
    jawaban = data.get('answer', '')
    
    prompt = f"""
    Kamu adalah guru les profesional yang ramah. Murid sedang mengecek soal: "{pertanyaan}". Jawaban benar: "{jawaban}".
    Jelaskan dengan edukatif mengapa jawaban itu benar (bahas dari segi grammar, linguistik, atau logika kodenya).
    Akhiri dengan: "Apakah kamu udah paham soal pembahasan ini? Atau kamu ingin melihat kamus dulu?"
    """
    try:
        response = generate_with_retry(prompt)
        return jsonify({'explanation': response.text.strip()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat_tutor', methods=['POST'])
def chat_tutor():
    data = request.json
    user_msg = data.get('message', '')
    history = data.get('history', '')
    
    prompt = f"""
    Kamu adalah Tutor AI PahamTeks yang HANYA ahli dalam Bahasa Asing, Linguistik, dan Pemrograman Komputer.
    Tugas utamamu adalah membantu proses pembelajaran. JIKA pengguna bertanya hal random di luar itu, tolak dengan sopan dan arahkan kembali ke topik belajar bahasa atau koding.
    Konteks: {history}
    Murid merespons: "{user_msg}"
    Berikan jawaban interaktif dan ramah sesuai instruksi di atas. Jangan gunakan markdown tebal/miring berlebihan.
    """
    try:
        response = generate_with_retry(prompt)
        return jsonify({'reply': response.text.strip()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dictionary', methods=['POST'])
def dictionary():
    data = request.json
    keyword = data.get('keyword', '')
    
    prompt = f"""
    Kamu adalah 'Kamus Pintar AI' yang DEDIKATIF untuk edukasi bahasa dan pemrograman komputer.
    Pengguna mencari: "{keyword}".
    Aturan Ketat:
    1. Jika berhubungan dengan kata/bahasa: Berikan Kelas Kata (Noun/Verb/dll), Cara Baca (jika non-latin), Definisi, dan satu contoh kalimat.
    2. Jika berhubungan dengan pemrograman/IT: Berikan Fungsi/Konsep, Penjelasan singkat, dan contoh struktur kodenya.
    3. Jika pencarian pengguna BUKAN tentang bahasa atau IT, jawab: "Mohon maaf, Kamus Pintar AI PahamTeks hanya berfokus pada eksplorasi istilah bahasa dunia dan pemrograman. Adakah kosakata lain yang ingin Anda pelajari?"
    
    Gunakan teks biasa yang rapi dan mudah dibaca tanpa markdown berlebihan.
    """
    try:
        response = generate_with_retry(prompt)
        return jsonify({'result': response.text.strip()})
    except Exception as e:
        print(f"Error Kamus: {e}")
        return jsonify({'error': "Gagal memuat pengertian dari server AI."}), 500

@app.route('/')
@app.route('/index.html')
def home():
    try:
        file_path = os.path.join(os.path.dirname(__file__), '..', 'index.html')
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"<h1>Memuat Tampilan...</h1><p>Silakan muat ulang halaman. Error: {e}</p>"