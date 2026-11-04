import os
import datetime
import io
import time
import threading
import re
import json
import subprocess
import tempfile
import random
import pandas as pd
from functools import wraps
from flask import Flask, jsonify, render_template, request, Response
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

app = Flask(__name__)

EXCEL_FILE = "עדכון תוכנית שידורים TIAMO - שבועי.xlsx"
SCOPES = ['https://www.googleapis.com/auth/drive']

# שליפת מזהה התיקייה הראשית מתוך משתני הסביבה של Render (עם גיבוי למזהה המקורי)
PARENT_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID', '1tAy9l49lJAbMWRVJdoK4b2uEiU6vQLH-')

# כתובת שרת הסטרימינג (עדכן את YOUR_PASSWORD ואת ה-mountpoint במידת הצורך)
STREAMING_URL = os.environ.get('STREAMING_URL', 'icecast://source:YOUR_PASSWORD@liveradio.co.il:8030/stream')

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

# ----------------- מנוע הזרמה אוטומטי (Auto DJ) -----------------
def download_and_stream(file_id, service):
    temp_file_path = None
    try:
        request_drive = service.files().get_media(fileId=file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            downloader = MediaIoBaseDownload(temp_audio, request_drive)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            temp_file_path = temp_audio.name
            
        command = [
            'ffmpeg', '-re', '-i', temp_file_path,
            '-c:a', 'copy', '-content_type', 'audio/mpeg',
            '-f', 'mp3', STREAMING_URL
        ]
        subprocess.run(command)
    except Exception as e:
        print(f"Streaming error: {e}", flush=True)
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def auto_dj_background_loop():
    service = get_drive_service()
    while True:
        try:
            with app.app_context():
                status_response = get_current_program_status().json
                current_program = status_response.get('program', '')

            if current_program and current_program != "לא הוגדרה תוכנית":
                parent_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID', PARENT_FOLDER_ID)
                folders_result = service.files().list(
                    q=f"'{parent_folder_id}' in parents and name = '{current_program}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                    fields="files(id, name)"
                ).execute()
                
                folders = folders_result.get('files', [])
                if folders:
                    program_folder_id = folders[0]['id']
                    
                    songs_result = service.files().list(
                        q=f"'{program_folder_id}' in parents and mimeType contains 'audio' and trashed = false",
                        fields="files(id, name)"
                    ).execute()
                    
                    songs = songs_result.get('files', [])
                    if songs:
                        next_song = random.choice(songs)
                        print(f"Auto DJ logic streaming: {next_song['name']}", flush=True)
                        download_and_stream(next_song['id'], service)
                        continue

            time.sleep(10)
        except Exception as e:
            print(f"Auto DJ Loop Error: {e}", flush=True)
            time.sleep(10)

# הפעלת תהליכי הרקע
scanner_thread = threading.Thread(target=background_whatsapp_scanner, daemon=True)
scanner_thread.start()

autodj_thread = threading.Thread(target=auto_dj_background_loop, daemon=True)
autodj_thread.start()

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
                    
                    actual_end