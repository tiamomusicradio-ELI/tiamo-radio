import os
import glob
from flask import Blueprint, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import yt_dlp

playlist_bp = Blueprint('playlist_bp', __name__)

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'credentials.json'

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def find_or_create_folder(service, folder_name, parent_id=None):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])
    
    if files:
        return files[0]['id']
    
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        folder_metadata['parents'] = [parent_id]
        
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')

def upload_file_to_drive(service, file_path, file_name, folder_id):
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, mimetype='audio/mpeg')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

@playlist_bp.route('/process_playlist', methods=['POST'])
def process_playlist_route():
    data = request.json
    listener_name = data.get('listenerName')
    songs = data.get('songs', [])
    
    if not listener_name or not songs:
        return jsonify({'success': False, 'message': 'Missing listener name or songs'}), 400

    download_dir = 'downloads_temp'
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        service = get_drive_service()
        
        # 1. יצירה או מציאה של תיקיית האב 'בקשות מאזינים'
        root_folder_id = find_or_create_folder(service, 'בקשות מאזינים')
        
        # 2. יצירת תיקייה אישית למאזין תחת תיקיית 'בקשות מאזינים'
        listener_folder_id = find_or_create_folder(service, listener_name, root_folder_id)
        
        processed_count = 0
        
        for item in songs:
            artist = item.get('artist', '')
            song = item.get('song', '')
            query_str = f"{artist} - {song}"
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'default_search': 'ytsearch1',
                'quiet': True
            }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([query_str])
            except Exception as download_err:
                print(f"Download error for {query_str}: {download_err}")
                continue
                
        mp3_files = glob.glob(os.path.join(download_dir, '*.mp3'))
        for file_path in mp3_files:
            file_name = os.path.basename(file_path)
            upload_file_to_drive(service, file_path, file_name, listener_folder_id)
            processed_count += 1
            try:
                os.remove(file_path)
            except:
                pass
                
        return jsonify({
            'success': True, 
            'message': f'Successfully processed and uploaded {processed_count} songs to Google Drive!'
        })
        
    except Exception as e:
        print(f"Drive process error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500