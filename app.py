import os
import datetime
import io
import time
import threading
import re
import json
import pandas as pd
from functools import wraps
from flask import Flask, jsonify, render_template, request, Response
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

app = Flask(__name__)

EXCEL_FILE = "עדכון תוכנית שידורים TIAMO - 4.8.26.xlsx"
SCOPES = ['https://www.googleapis.com/auth/drive']

# שליפת מזהה התיקייה הראשית מתוך משתני הסביבה של Render (עם גיבוי למזהה המקורי)
PARENT_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID', '1tAy9l49lJAbMWRVJdoK4b2uEiU6vQLH-')

# ----------------- הגדרות אבטחה וניהול -----------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "tiamo123"

def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    return Response(
        'נדרשת הזנת שם משתמש וסיסמא לכניסה למערכת הרדיו', 401,
        {'WWW-Authenticate': 'Basic realm="Tiamo Radio Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated
# --------------------------------------------------------

requested_songs_list = [
    {
        'id': 1,
        'phone': '+972 53-855-0511',
        'raw_text': 'חיים משה - אהבת חיי\nאייל גולן - צליל מיתר',
        'parsed_songs': [
            {'artist': 'חיים משה', 'song': 'אהבת חיי'},
            {'artist': 'אייל גולן', 'song': 'צליל מיתר'}
        ],
        'time': '03:17 - 22/10/2026'
    }
]

def get_drive_service():
    # בדיקה האם תוכן ה-JSON מוגדר במשתנה הסביבה של Render
    creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    if creds_json:
        creds_info = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    else:
        # גיבוי לעבודה מקומית במחשב שלך אם הקובץ קיים פיזית
        creds = service_account.Credentials.from_service_account_file(
            'credentials.json', scopes=SCOPES
        )
    return build('drive', 'v3', credentials=creds)

def parse_playlist_text(raw_text):
    lines = raw_text.strip().split('\n')
    parsed_songs = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if '-' in line:
            parts = line.split('-', 1)
            artist = parts[0].strip()
            song = parts[1].strip()
            if artist and song:
                parsed_songs.append({'artist': artist, 'song': song})
                continue

        clean_text = re.sub(r'^(שלום|היי|אהלן)?\s*,?\s*(אני\s+[\w\s]+\s+)?(מבקש|רוצה|אפשר)\s*(את\s+השיר|את)?\s*:?\s*', '', line, flags=re.IGNORECASE).strip()

        match_of = re.search(r'(.+?)\s+של\s+(.+)', clean_text)
        if match_of:
            song = match_of.group(1).strip()
            artist = match_of.group(2).strip()
            parsed_songs.append({'artist': artist, 'song': song})
            continue

        if ':' in line:
            parts = line.split(':', 1)
            song = parts[1].strip()
            parsed_songs.append({'artist': 'לא צוין', 'song': song})
            continue

        parsed_songs.append({'artist': 'לא צוין', 'song': clean_text})
            
    return parsed_songs

def search_drive_songs(artist, song):
    try:
        service = get_drive_service()
        search_query = f"name contains '{song}' and trashed = false"
        if artist and artist != 'לא צוין':
            search_query += f" and name contains '{artist}'"

        results = service.files().list(
            q=search_query,
            pageSize=10,
            fields="files(id, name, mimeType)"
        ).execute()

        return results.get('files', [])
    except Exception as e:
        print(f"Drive Search Error: {e}", flush=True)
        return []

def fix_hebrew(text):
    return text

def get_current_week_of_month():
    now = datetime.datetime.now()
    first_day_of_month = datetime.datetime(now.year, now.month, 1)
    first_day_weekday = (first_day_of_month.weekday() + 1) % 7
    day_of_month = now.day
    
    week_number = ((day_of_month + first_day_weekday - 1) // 7) + 1
    if week_number > 4:
        week_number = 4
    return week_number

def background_whatsapp_scanner():
    while True:
        try:
            pass
        except Exception as e:
            pass
        time.sleep(60)

scanner_thread = threading.Thread(target=background_whatsapp_scanner, daemon=True)
scanner_thread.start()

# --- עמודי המערכת ---
@app.route('/')
@requires_auth
def index():
    return render_template('index.html')

# --- שליפת התיקיות הראשיות מהדרייב (עבור דף ניהול מדיה) ---
@app.route('/get_main_programs', methods=['GET'])
@requires_auth
def get_main_programs():
    try:
        service = get_drive_service()
        parent_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID', PARENT_FOLDER_ID)
        
        print(f"DEBUG - Fetching items from Drive parent_id: {parent_folder_id}", flush=True)
        results = service.files().list(
            q=f"'{parent_folder_id}' in parents and trashed = false",
            pageSize=50,
            fields="files(id, name, mimeType)"
        ).execute()
        items = results.get('files', [])
        
        print("DEBUG - All items found:", items, flush=True)

        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s['name'])]
        
        items.sort(key=natural_sort_key)
        return jsonify(items)
    except Exception as e:
        print("DEBUG - Error in get_main_programs:", str(e), flush=True)
        return jsonify([])

@app.route('/get_sub_items')
@requires_auth
def get_sub_items():
    folder_id = request.args.get('folder_id')
    try:
        service = get_drive_service()
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            pageSize=100,
            fields="files(id, name, mimeType)"
        ).execute()
        items = results.get('files', [])
        
        folders = [i for i in items if i['mimeType'] == 'application/vnd.google-apps.folder']
        files = [i for i in items if i['mimeType'] != 'application/vnd.google-apps.folder']
        
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s['name'])]
        
        folders.sort(key=natural_sort_key)
        files.sort(key=natural_sort_key)
        
        return jsonify({'folders': folders, 'files': files})
    except Exception as e:
        return jsonify({'folders': [], 'files': []})

@app.route('/stream_preview/<file_id>')
@requires_auth
def stream_preview(file_id):
    try:
        service = get_drive_service()
        request_drive = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request_drive)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return Response(fh.read(), mimetype="audio/mpeg")
    except Exception as e:
        return str(e), 500

@app.route('/get_current_program_status')
@requires_auth
def get_current_program_status():
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name='תוכנית חודשית', header=None)
        now = datetime.datetime.now()
        current_hour = now.hour
        
        day_column_map = {
            'Sunday': 1, 'Monday': 3, 'Tuesday': 5, 'Wednesday': 7,
            'Thursday': 9, 'Friday': 11, 'Saturday': 13
        }
        
        current_day_en = now.strftime('%A')
        time_col_idx = day_column_map.get(current_day_en, 1)
        program_col_idx = time_col_idx + 1
        
        current_program = "לא הוגדרה תוכנית"
        end_time_str = "00:00"

        for j in range(2, len(df)):
            time_val = str(df.iloc[j, time_col_idx]).strip()
            if '-' in time_val and ':' in time_val:
                try:
                    start_time, end_time = time_val.split('-')
                    start_h = int(start_time.split(':')[0])
                    end_h = int(end_time.split(':')[0])
                    
                    actual_end_h = 24 if end_h == 0 else end_h
                    
                    if start_h <= current_hour < actual_end_h:
                        prog_name = df.iloc[j, program_col_idx]
                        if pd.notna(prog_name):
                            current_program = str(prog_name).strip()
                            end_time_str = end_time.strip()
                            break
                except:
                    continue
                    
        return jsonify({
            'success': True,
            'program': fix_hebrew(current_program),
            'end_time': end_time_str,
            'current_week': get_current_week_of_month()
        })
    except Exception as e:
        return jsonify({'success': False, 'program': 'שגיאה בקריאת אקסל', 'end_time': '--:--', 'current_week': 1})

@app.route('/get_full_schedule')
@requires_auth
def get_full_schedule():
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name='תוכנית חודשית', header=None)
        schedule_data = df.fillna("").values.tolist()
        return jsonify({'success': True, 'data': schedule_data})
    except Exception as e:
        return jsonify({'success': False, 'data': []})

@app.route('/whatsapp_webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
        VERIFY_TOKEN = "tiamo_radio_token_123"
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if mode and token and mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        return 'Forbidden', 403

    elif request.method == 'POST':
        data = request.get_json()
        try:
            message = data['entry'][0]['changes'][0]['value']['messages'][0]
            sender_phone = message['from']
            raw_text = message['text']['body']
            
            parsed_songs = parse_playlist_text(raw_text)

            request_item = {
                'id': len(requested_songs_list) + 1,
                'phone': sender_phone,
                'raw_text': raw_text,
                'parsed_songs': parsed_songs,
                'time': datetime.datetime.now().strftime('%H:%M - %d/%m/%Y')
            }
            requested_songs_list.insert(0, request_item)
        except Exception as e:
            pass
            
        return jsonify({'status': 'success'}), 200

@app.route('/upload_file', methods=['POST'])
@requires_auth
def upload_file():
    try:
        folder_id = request.form.get('folder_id')
        uploaded_file = request.files.get('file')
        if not uploaded_file or not folder_id:
            return jsonify({'success': False, 'error': 'חסרים פרטים להעלאה'})
            
        service = get_drive_service()
        file_metadata = {
            'name': uploaded_file.filename,
            'parents': [folder_id]
        }
        
        file_mimetype = uploaded_file.mimetype or 'application/octet-stream'
        media = MediaIoBaseUpload(io.BytesIO(uploaded_file.read()), mimetype=file_mimetype, resumable=True)
        
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_file', methods=['POST'])
@requires_auth
def delete_file():
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        service = get_drive_service()
        service.files().delete(fileId=file_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_whatsapp_requests', methods=['GET'])
@requires_auth
def get_whatsapp_requests():
    return jsonify({'success': True, 'requests': requested_songs_list})

@app.route('/search_playlist_in_drive', methods=['POST'])
@requires_auth
def search_playlist_in_drive():
    try:
        data = request.get_json()
        songs_to_search = data.get('songs', [])
        
        results = []
        for item in songs_to_search:
            artist = item.get('artist', '')
            song = item.get('song', '')
            
            drive_files = search_drive_songs(artist, song)
            results.append({
                'requested_artist': artist,
                'requested_song': song,
                'found_in_drive': drive_files
            })
            
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/manual_scan_whatsapp', methods=['POST'])
@requires_auth
def manual_scan_whatsapp():
    try:
        return jsonify({'success': True, 'message': 'הסריקה הושלמה בהצלחה!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)