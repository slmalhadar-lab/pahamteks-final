from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import json
import random
import os

app = Flask(__name__)
CORS(app)

# Konfigurasi API
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# SOLUSI: Menggunakan "gemini-pro" yang 100% didukung oleh versi server mana pun
model = genai.GenerativeModel('gemini-pro')

quiz_cache = {}
users_db = {}
otp_db = {}

# Pembersih JSON yang diperkuat dan tahan banting
def parse_safe_json(raw_text):
    try:
        text = raw_text.strip()
        # Cari lokasi kurung siku pembuka dan penutup dari Array JSON
        start = text.find('[')
        end = text.rfind(']') + 1
        
        if start != -1 and end != 0:
            text = text[start:end] # Potong dan ambil bagian JSON-nya saja
            
        return json.loads(text)
    except Exception as e:
        print(f"JSON Error: {e} | Teks Asli: {raw_text}")
        raise Exception("Format JSON dari AI rusak.")

@app.route('/api/send_otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email', '').strip()
    if not email: return jsonify({'error': 'Email wajib diisi!'}), 400
    if email in users_db: return jsonify({'error': 'Email terdaftar! Sign In.'}), 400
    otp_db[email] = "123456" 
    return jsonify({'message': 'Kode terkirim!'})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    fname = data.get('fname', '').strip()
    lname = data.get('lname', '').strip()
    otp_code = data.get('otp', '').strip()
    
    if not email or not password or not fname or not lname:
        return jsonify({'error': 'Data tidak lengkap!'}), 400
    if otp_db.get(email) != otp_code:
        return jsonify({'error': 'Kode OTP salah!'}), 400
    if email in users_db:
        return jsonify({'error': 'Email terdaftar!'}), 400
        
    full_name = f"{fname} {lname}"
    users_db[email] = {'name': full_name, 'password': password}
    del otp_db[email]
    return jsonify({'message': 'Pendaftaran berhasil.', 'name': full_name})

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
        if not api_key: return jsonify({'translated_text': '⚠️ Error: API Key Gemini kosong.'})
        prompt = f"Translate this text exactly from {source_name} to {target_name}:\n{teks}\n\nONLY output the translation result. Do not add any explanation. If {target_name} is non-Latin, provide Romaji reading below it."
        
        response = model.generate_content(prompt)
        return jsonify({'translated_text': response.text.strip().strip('"')})
    except Exception as e:
        if "429" in str(e).lower() or "quota" in str(e).lower():
            return jsonify({'translated_text': '⏳ Limit API Gratis (15x/menit) tercapai. Tunggu 1 menit.'})
        return jsonify({'translated_text': f'⚠️ AI Error: {str(e)}'})

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
    Buat 5 soal kuis tingkat {level} materi edukasi: {', '.join(categories)}.
    Format WAJIB JSON Array of Objects sesuai schema:
    [
      {{ "instruction": "Instruksi pengerjaan", "question": "Soal lengkap", "options": ["A", "B", "C", "D"], "answer": "Jawaban yang benar" }}
    ]
    GANTI SEMUA tanda kutip ganda (") di dalam teks soal/opsi dengan kutip tunggal (').
    Keluarkan JSON murni saja.
    """
    try:
        if not api_key: raise Exception("API Key Kosong")
        
        response = model.generate_content(prompt)
        
        quiz_data = parse_safe_json(response.text)
        quiz_cache[cache_key] = quiz_data
        return jsonify(quiz_data)
    except Exception as e:
        err_msg = "Sistem gagal menyusun struktur kuis. Silakan coba lagi."
        if "429" in str(e).lower() or "quota" in str(e).lower():
            err_msg = "⏳ Limit API Gratis Google (15x/menit) habis. Jangan klik apapun selama 1 menit, lalu coba lagi."
            
        return jsonify([{
            "instruction": "Peringatan Sistem",
            "question": err_msg,
            "options": ["Tunggu 1 Menit", "Refresh Web", "Paham", "Coba Lagi"],
            "answer": "Paham"
        }])

@app.route('/api/generate_challenge', methods=['POST'])
def generate_challenge():
    data = request.json
    category = data.get('category', 'General')
    prompt = f"""
    Buat 3 soal ujian SANGAT SULIT topik: {category}.
    Format WAJIB JSON Array of Objects:
    [
      {{ "instruction": "Tantangan Analisis", "question": "Studi kasus rumit", "options": ["A", "B", "C", "D"], "answer": "Jawaban yang benar" }}
    ]
    GANTI SEMUA tanda kutip ganda (") di dalam teks soal/opsi dengan kutip tunggal (').
    Keluarkan JSON murni saja.
    """
    try:
        if not api_key: raise Exception("API Key Kosong")
        
        response = model.generate_content(prompt)
        
        challenge_data = parse_safe_json(response.text)
        return jsonify(challenge_data)
    except Exception as e:
        err_msg = "Sistem gagal memproses tantangan. Coba lagi."
        if "429" in str(e).lower() or "quota" in str(e).lower():
            err_msg = "⏳ Limit API Gratis Google habis. Tunggu 1 menit lalu coba lagi."
            
        return jsonify([{
            "instruction": "Peringatan Sistem",
            "question": err_msg,
            "options": ["Tunggu 1 Menit", "Refresh", "Ok", "Batal"],
            "answer": "Ok"
        }])

@app.route('/api/dictionary', methods=['POST'])
def dictionary():
    data = request.json
    keyword = data.get('keyword', '')
    prompt = f"""
    Kamu Kamus Pintar AI edukasi. Pengguna mencari: "{keyword}".
    Jika bahasa: Berikan Kelas Kata, Cara Baca, Definisi, contoh kalimat.
    Jika IT: Berikan Fungsi/Konsep, Penjelasan, contoh kode singkat.
    Selain itu tolak dengan ramah.
    """
    try:
        if not api_key: return jsonify({'result': '⚠️ Error: API Key belum dimasukkan.'})
        response = model.generate_content(prompt)
        return jsonify({'result': response.text.strip()})
    except Exception as e:
        if "429" in str(e).lower() or "quota" in str(e).lower():
            return jsonify({'result': '⏳ Limit API Gratis Google tercapai. Tunggu 1 menit lalu coba lagi.'})
        return jsonify({'result': f'⚠️ AI Error: {str(e)}'})

@app.route('/')
@app.route('/index.html')
def home():
    try:
        file_path = os.path.join(os.path.dirname(__file__), '..', 'index.html')
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"<h1>Memuat Tampilan...</h1><p>Error: {e}</p>"