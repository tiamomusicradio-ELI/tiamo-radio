import datetime
import time
import subprocess
import os
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- הגדרות חיבור לGoogle Drive ---
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'credentials.json'

# --- פרטי הזרמת שידור לשרת (מתוך פאנל RLive) ---
STREAM_HOST = "liveradio.co.il"
STREAM_PORT = 8000  # פורט המקור של Shoutcast
STREAM_PASSWORD = "Tkhvu5020nzrjh"  # סיסמת הניהול/שידור
# ---------------------------------------------

try:
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)
    print("========================================")
    print(" בוט הרדיו מחובר בהצלחה לגוגל דרייב ולשרת השידור!")
    print("========================================\n")
except Exception as e:
    print(f"שגיאה בהתחברות: {e}")
    exit()

excel_file = 'עדכון תוכנית שידורים TIAMO - 4.8.26.xlsx'
last_played_program = None

def fix_hebrew(text):
    if not text:
        return ""
    if any('\u0590' <= c <= '\u05FF' for c in text):
        return text[::-1]
    return text

def get_subfolders(service, parent_id):
    try:
        print(f"DEBUG - Searching subfolders for parent_id: {parent_id}")
        query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get('files', [])
        print(f"DEBUG - Found folders for {parent_id}: {folders}")
        return folders
    except Exception as e:
        print(f"DEBUG - Error in get_subfolders: {e}")
        return []

def get_files_from_folder(service, folder_id):
    """
    שולף וממיין את כל קבצי האודיו מתיקייה ספציפית בדרייב
    """
    if not folder_id:
        return []
    try:
        query = f"'{folder_id}' in parents and (mimeType contains 'audio/' or name contains '.mp3' or name contains '.wav') and trashed=false"
        results = service.files().list(
            q=query, 
            fields="files(id, name, mimeType)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = results.get('files', [])
        # מיון השירים בסדר עולה (מספרי/אלפביתי)
        files.sort(key=lambda x: x['name'])
        return files
    except Exception as e:
        print(f"❌ שגיאה בשליפת קבצים מתיקייה {folder_id}: {e}")
        return []

def get_program_playlist_with_fallback(service, daily_folder_id, completion_folder_id):
    """
    שולף את הפלייליסט היומי. אם הוא ריק או נגמר, משלים אוטומטית מתיקיית 'השלמה'.
    """
    playlist = []
    
    print("📁 טוען שירים מהתיקייה היומית...")
    daily_songs = get_files_from_folder(service, daily_folder_id)
    playlist.extend(daily_songs)
    print(f" -> נמצאו {len(daily_songs)} שירים בתיקייה היומית.")

    # במידה וקיימת תיקיית השלמה, נוסיף את השירים שלה לסוף התור
    if completion_folder_id:
        print("📁 טוען שירים נוספים מתיקיית 'השלמה' של התוכנית...")
        completion_songs = get_files_from_folder(service, completion_folder_id)
        
        for song in completion_songs:
            if song not in playlist:  # מניעת כפילויות
                playlist.append(song)
                
        print(f" -> נוספו {len(completion_songs)} שירים מתיקיית ההשלמה.")

    return playlist

def stream_song(file_id, file_name):
    """
    מוריד זמנית את השיר מהדרייב ומזרים אותו באמצעות FFmpeg ישירות לשרת השידור
    """
    print(f" -> מתחיל להזרים לשידור: {fix_hebrew(file_name)}")
    try:
        request = drive_service.files().get_media(fileId=file_id)
        local_temp_song = "temp_song.mp3"
        
        with open(local_temp_song, "wb") as f:
            f.write(request.execute())
        
        ffmpeg_cmd = [
            'ffmpeg', '-re', '-i', local_temp_song,
            '-c:a', 'libmp3lame', '-b:a', '128k',
            '-content_type', 'audio/mpeg',
            f'icecast://source:{STREAM_PASSWORD}@{STREAM_HOST}:{STREAM_PORT}/stream'
        ]
        
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process.wait() # ממתין עד לסיום ניגון השיר הנוכחי
        print(f" -> הסתיים שידור השיר: {fix_hebrew(file_name)}")
        
    except Exception as e:
        print(f" -> שגיאה בהזרמת השיר {file_name}: {e}")

# ==================== הלולאה הראשית של הבוט ====================
while True:
    try:
        df = pd.read_excel(excel_file, sheet_name='תוכנית חודשית', header=None)
        
        now = datetime.datetime.now()
        current_hour = now.hour

        day_column_map = {
            'Sunday': 1, 'Monday': 3, 'Tuesday': 5, 'Wednesday': 7,
            'Thursday': 9, 'Friday': 11, 'Saturday': 13
        }

        current_day_en = now.strftime('%A')
        time_col_idx = day_column_map.get(current_day_en, 1)
        program_col_idx = time_col_idx + 1

        current_program = "לא נמצאה תוכנית מוגדרת לשעה זו"

        for j in range(2, 14):
            if j >= len(df):
                break
                
            time_val = str(df.iloc[j, time_col_idx]).strip()
            if '-' in time_val and ':' in time_val:
                try:
                    start_time, end_time = time_val.split('-')
                    start_h = int(start_time.split(':')[0])
                    end_h = int(end_time.split(':')[0])

                    if end_h == 0:
                        end_h = 24

                    if start_h <= current_hour < end_h:
                        prog_name = df.iloc[j, program_col_idx]
                        if pd.notna(prog_name):
                            current_program = str(prog_name).strip()
                            break
                except:
                    continue

        if current_program != last_played_program:
            print(f"[{now.strftime('%H:%M')}] תוכנית פעילה כעת מהאקסל: {fix_hebrew(current_program)}")
            
            if current_program != "לא נמצאה תוכנית מוגדרת לשעה זו":
                query_folder = f"name = '{current_program}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
                folder_results = drive_service.files().list(q=query_folder, fields="files(id, name)").execute()
                matching_folders = folder_results.get('files', [])
                
                if matching_folders:
                    program_folder_id = matching_folders[0]['id']
                    hebrew_days = {
                        'Sunday': 'ראשון', 'Monday': 'שני', 'Tuesday': 'שלישי',
                        'Wednesday': 'רביעי', 'Thursday': 'חמישי', 'Friday': 'שישי', 'Saturday': 'שבת'
                    }
                    target_day_name = hebrew_days.get(current_day_en, '')
                    
                    month_folders = get_subfolders(drive_service, program_folder_id)
                    day_folder_id = None
                    completion_folder_id = None
                    
                    # חיפוש תיקיית היום ותיקיית ההשלמה תחת התוכנית
                    for mf in month_folders:
                        # בדיקה האם זו תיקיית השלמה
                        if 'השלמה' in mf['name']:
                            completion_folder_id = mf['id']
                            
                        week_folders = get_subfolders(drive_service, mf['id'])
                        for wf in week_folders:
                            day_folders = get_subfolders(drive_service, wf['id'])
                            for df_folder in day_folders:
                                if target_day_name in df_folder['name']:
                                    day_folder_id = df_folder['id']
                    
                    # טעינת הפלייליסט המלא (יומי + השלמה אוטומטית)
                    playlist = get_program_playlist_with_fallback(drive_service, day_folder_id, completion_folder_id)
                    
                    if playlist:
                        print(f" -> מתחיל להזרים סך הכל {len(playlist)} שירים לשרת הרדיו...")
                        for s in playlist:
                            stream_song(s['id'], s['name'])
                    else:
                        print(" -> אזהרה: לא נמצאו קבצים בתיקיות היום או ההשלמה.")
            
            print("----------------------------------------")
            last_played_program = current_program

        time.sleep(60)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(60)