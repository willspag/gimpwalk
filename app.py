


import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import google.generativeai as genai
from moviepy.editor import VideoFileClip
import tempfile
from functools import partial


# Load environment variables
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB limit
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'flv', 'wmv'}

# Environment variables
PASSWORD = os.environ.get('PASSWORD')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

genai.configure(api_key=GOOGLE_API_KEY)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'})
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # Convert to MP4
                mp4_filepath = os.path.splitext(filepath)[0] + '.mp4'
                video = VideoFileClip(filepath)
                
                # Use partial to create a callback function
                def callback(t):
                    print(f"Processing video: {t:.2f}%", flush=True)
                
                video.write_videofile(mp4_filepath, codec='libx264', audio_codec='aac', 
                                      progress_bar=False, verbose=False, logger=None,
                                      callback=partial(callback))
                video.close()
                
                # Delete original file if it's not MP4
                if os.path.splitext(filepath)[1].lower() != '.mp4':
                    os.remove(filepath)
                
                # Check password
                password = request.form.get('password')
                if password != PASSWORD:
                    return jsonify({'error': 'Not authorized'})
                
                # Query Gemini API
                model = genai.GenerativeModel('gemini-pro-vision')
                with open(mp4_filepath, 'rb') as f:
                    video_bytes = f.read()
                response = model.generate_content([video_bytes, "Enter prompt here"])
                
                return jsonify({'response': response.text})
            except Exception as e:
                return jsonify({'error': f'An error occurred: {str(e)}'})
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)