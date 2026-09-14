from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import json
import random
import os

app = Flask(__name__)
CORS(app)

# Ambil API Key dari Vercel
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# Menggunakan model paling cepat & andal untuk menghindari batas waktu Vercel
model = genai.GenerativeModel('gemini-1.5-flash')

quiz_cache = {}
users_db = {}
otp_db = {}

# Fungsi pemanggil AI tanpa sistem tunggu/delay agar tidak terkena Timeout Vercel 10 Detik
def generate_fast(prompt):
    if not api_key:
        raise Exception("API Key Gemini belum terpasang di Vercel.")
    return model.generate_content(prompt)

@app.route('/api/send_otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email', '').strip()
    if not email: return jsonify({'error': 'Email wajib diisi!'}), 400
    if email in users_db: return jsonify({'error': 'Email sudah terdaftar! Silakan Sign In.'}), 400
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
    
    if email not in users_db: return jsonify({'error': 'Email tidak ditemukan!'}), 400
    if users_db[email]['password'] != password: return jsonify({'error': 'Kata sandi salah!'}), 400
    return jsonify({'message': 'Login berhasil!', 'name': users_db[email]['name']})

@app.route('/api/user_log', methods=['POST'])
def user_log():
    data = request.json
    print(f"[TRACKER] User: {data.get('user', 'Tamu')} | Kategori: {data.get('category', 'General')} | Aktivitas: {data.get('activity', '')} | Skor: {data.get('score', 0)}")
    return jsonify({'status': 'logged'})

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

@app.route('/api/languages', methods=['GET'])
def get_languages():
    return jsonify(LANGUAGES)

@app.route('/api/translate', methods=['POST'])
def translate_text():
    data = request.json
    teks = data.get('text', '').strip()
    if not teks: return jsonify({'translated_text': ''})

    source_name = next((k for k, v in LANGUAGES.items() if v == data.get('source')), "Auto Detect")
    target_name = next((k for k, v in LANGUAGES.items() if v == data.get('target')), "English")
            
    try:
        prompt = f"Translate this text from {source_name} to {target_name}: '{teks}'. Provide ONLY the translated text. If {target_name} is non-Latin script, include Romaji/Latin pronunciation below it."
        response = generate_fast(prompt)
        return jsonify({'translated_text': response.text.strip().strip('"')})
    except Exception as e:
        print(f"Error Translate: {e}")
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
        
    prompt = f"""
    Buat 5 soal kuis tingkat {level} untuk materi edukasi: {', '.join(categories)}.
    ATURAN SANGAT KETAT:
    1. JANGAN PERNAH gunakan tanda kutip ganda (") di dalam teks soal maupun teks jawaban. Ganti SEMUA dengan kutip tunggal (').
    2. Hasil harus murni JSON Array. Jangan bungkus dengan ```json dan jangan beri kata pengantar.
    Bentuk JSON yang wajib dipatuhi:
    [{{ "instruction": "Perintah", "question": "Soal hanya boleh kutip tunggal", "options": ["A", "B", "C", "D"], "answer": "Jawaban Benar" }}]
    """
    try:
        response = generate_fast(prompt)
        raw_text = response.text.strip()
        if "```" in raw_text:
            raw_text = raw_text.replace("```json", "").replace("```html", "").replace("```", "").strip()
            
        quiz_data = json.loads(raw_text)
        quiz_cache[cache_key] = quiz_data
        return jsonify(quiz_data)
    except Exception as e:
        print(f"Error Quiz: {e}")
        return jsonify({'error': "Gagal memproses data JSON. Coba lagi."}), 500

@app.route('/api/generate_challenge', methods=['POST'])
def generate_challenge():
    data = request.json
    category = data.get('category', 'General')
    prompt = f"""
    Buat 3 soal ujian tantangan (SANGAT SULIT) untuk topik: {category}.
    ATURAN SANGAT KETAT:
    1. Ganti SEMUA tanda kutip ganda (") di teks soal atau teks kodingan menjadi kutip tunggal (').
    2. Format WAJIB berupa JSON Array murni tanpa markdown (```).
    Bentuk JSON:
    [{{ "instruction": "Tantangan", "question": "Studi kasus...", "options": ["A", "B", "C", "D"], "answer": "Jawaban Benar" }}]
    """
    try:
        response = generate_fast(prompt)
        raw_text = response.text.strip()
        if "```" in raw_text:
            raw_text = raw_text.replace("```json", "").replace("```html", "").replace("```", "").strip()
        return jsonify(json.loads(raw_text))
    except Exception as e:
        print(f"Error Challenge: {e}")
        return jsonify({'error': "Gagal memproses tantangan."}), 500

@app.route('/api/dictionary', methods=['POST'])
def dictionary():
    data = request.json
    keyword = data.get('keyword', '')
    prompt = f"""
    Kamu adalah 'Kamus Pintar AI' untuk edukasi. Pengguna mencari: "{keyword}".
    1. Jika ini tentang bahasa manusia: Berikan Kelas Kata, Cara Baca, Definisi, dan contoh kalimat mendidik.
    2. Jika ini tentang koding/pemrograman: Berikan Fungsi/Konsep, Penjelasan, dan contoh kode sintaksis.
    3. Jika BUKAN tentang bahasa/IT, tolak dengan ramah bahwa kamu hanya melayani edukasi.
    Gunakan teks rapi dan bersih.
    """
    try:
        response = generate_fast(prompt)
        return jsonify({'result': response.text.strip()})
    except Exception as e:
        print(f"Error Kamus: {e}")
        return jsonify({'error': "Gagal memuat pengertian dari AI."}), 500

@app.route('/')
@app.route('/index.html')
def home():
    try:
        file_path = os.path.join(os.path.dirname(__file__), '..', 'index.html')
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"<h1>Memuat Tampilan...</h1><p>Silakan muat ulang halaman. Error: {e}</p>"