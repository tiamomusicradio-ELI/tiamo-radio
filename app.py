from datetime import datetime
import os
from flask import Flask, jsonify, render_template, request, send_file
import pandas as pd
import pytz

app = Flask(__name__)

EXCEL_FILENAME = 'עדכון תוכנית שידורים TIAMO - שבועי.xlsx'


@app.route('/')
def index():
  return render_template('index.html')


@app.route('/get_full_schedule')
def get_full_schedule():
  try:
    if not os.path.exists(EXCEL_FILENAME):
      return {
          'success': False,
          'error': 'קובץ האקסל אינו موجود בשרת',
      }, 404

    df = pd.read_excel(EXCEL_FILENAME, sheet_name='תוכנית חודשית')
    data = df.values.tolist()
    return {'success': True, 'data': data}
  except Exception as e:
    return {'success': False, 'error': str(e)}, 500


@app.route('/get_current_program_status')
def get_current_program_status():
  try:
    if not os.path.exists(EXCEL_FILENAME):
      return {'success': True, 'program': 'שדרן אוטומטי', 'end_time': '24:00'}

    df = pd.read_excel(EXCEL_FILENAME, sheet_name='תוכנית חודשית')

    tz = pytz.timezone('Asia/Jerusalem')
    now = datetime.now(tz)
    day_name = now.strftime('%A')  # Sunday, Monday, Tuesday, etc.

    # מיפוי עמודות באקסל לפי ימות השבוע
    # ראשון: 1,2 | שני: 3,4 | שלישי: 5,6 | רביעי: 7,8 | חמישי: 9,10 | שישי: 11,12 | שבת: 13,14
    col_map = {
        'Sunday': (1, 2),
        'Monday': (3, 4),
        'Tuesday': (5, 6),
        'Wednesday': (7, 8),
        'Thursday': (9, 10),
        'Friday': (11, 12),
        'Saturday': (13, 14),
    }

    prog_col, time_col = col_map.get(day_name, (1, 2))
    current_hour = now.hour

    current_program = 'משדר חי'
    end_time_str = '--:--'

    for i in range(1, len(df)):
      time_val = str(df.iloc[i, time_col]).strip()
      prog_name = str(df.iloc[i, prog_col]).strip()

      if '-' in time_val:
        try:
          parts = time_val.split('-')
          start_h = int(parts[0].strip().split(':')[0])
          end_h = int(parts[1].strip().split(':')[0])
          if end_h == 0:
            end_h = 24

          if start_h <= current_hour < end_h:
            current_program = prog_name if prog_name != 'nan' else 'שידור רציף'
            end_time_str = parts[1].strip()
            break
        except Exception:
          pass

    return {
        'success': True,
        'program': current_program,
        'end_time': end_time_str,
    }
  except Exception as e:
    return {'success': False, 'error': str(e)}, 500


@app.route('/get_whatsapp_requests')
def get_whatsapp_requests():
  # דוגמה לשליפת בקשות וואצאפ (ניתן להתאים למסד הנתונים או Firebase שלך)
  sample_requests = [{
      'time': datetime.now().strftime('%H:%M %d/%m/%Y'),
      'phone': '050-0000000',
      'song': 'אייל גולן - צליל מיתר',
      'parsed_songs': [{'artist': 'אייל גולן', 'song': 'צליל מיתר'}],
  }]
  return {'success': True, 'requests': sample_requests}


@app.route('/get_main_programs')
def get_main_programs():
  # רשימת תיקיות ראשיות לדוגמה מ-Google Drive
  folders = [
      {'id': 'folder_1', 'name': 'תוכניות אוקטובר 2026'},
      {'id': 'folder_2', 'name': 'אוספים מזרחיים'},
      {'id': 'folder_3', 'name': 'שירים חסידיים ופיוטים'},
  ]
  return jsonify(folders)


@app.route('/get_sub_items')
def get_sub_items():
  folder_id = request.args.get('folder_id')
  # דוגמה לתתי-תיקיות וקבצים בתיקייה
  return jsonify({'folders': [], 'files': []})


if __name__ == '__main__':
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)