


import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import google.generativeai as genai
from moviepy.editor import VideoFileClip
import tempfile
from functools import partial


import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.cloud import storage
import json
import uuid

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# TODO(developer): Update and un-comment below line
# project_id = "PROJECT_ID"

print("Imports complete")

# copy a file from gcloud
def copy_from_gcloud(
            gcloud_file_path,
            destination_file_path,
            gcloud_bucket_name,
            GOOGLE_CLOUD_SERVICE_ACCOUNT_INFO_JSON
            ):
    
    storage_client = storage.Client.from_service_account_info(json.loads(GOOGLE_CLOUD_SERVICE_ACCOUNT_INFO_JSON))
    
    source_bucket = storage_client.bucket(gcloud_bucket_name)
    source_blob = source_bucket.blob(gcloud_file_path)

    source_blob.download_to_filename(destination_file_path)
    
    print("\nSource File: " + gcloud_bucket_name + "/" + gcloud_file_path + " Copied to: " + destination_file_path + " Successfully!")


# copy a file to gcloud
def copy_to_gcloud(
            file_path,
            destination_file_path,
            gcloud_bucket_name,
            GOOGLE_CLOUD_SERVICE_ACCOUNT_INFO_JSON
            ):
    
    storage_client = storage.Client.from_service_account_info(json.loads(GOOGLE_CLOUD_SERVICE_ACCOUNT_INFO_JSON))
    
    destination_bucket = storage_client.bucket(gcloud_bucket_name)
    blob = destination_bucket.blob(destination_file_path)
    
    blob.upload_from_filename(file_path)
    
    print("\nSource File: " + file_path + " Sent to Destination: " + gcloud_bucket_name + "/" + destination_file_path + " Successfully!")


vertexai.init(project=os.environ.get("GCLOUD_PROJECT_ID"))
print("Vertex AI initialized")


app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB limit
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'flv', 'wmv'}

# Environment variables
PASSWORD = os.environ.get('PASSWORD')

gimpwalk_prompt = "Watch this video frame by frame and observe in detail the walking/running form of the person in the video. Your goal is to analyze their gait and the form of their steps to identify whether or not they are limping and review their overall form. If they are limping, you must provide a detailed gait analysis, explanation of the limp, what the error is, and what needs to be improved. This person is recovering from an injury and working closely with their physical therapist to regain their walking/running capabilities, so the physical therapist has requested your frame-by-frame analysis in order to help improve her prognosis for the patient. Therefore, you should use medical terminology and be robust in your answer as it is intended for review by the medical professional. After your analysis, please provide a step-by-step recovery plan for the patient detailing exercises, stretches, or other approaches to improve their walking/running capabilities specifically catered to their unique gait analysis. For each recommendation, provide an explanation of your reasoning for the recommendation and how it will help them in relation to specific aspects of their current walking/running form discovered in your gait analysis."

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        
        # Check password
        password = request.form.get('password')
        additional_notes = request.form.get('notes')
        if password != PASSWORD:
            return jsonify({'error': 'Incorrect Password'})
            
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'})
        if file and allowed_file(file.filename):
            print(f"\n\n\n{os.path.splitext(file.filename)[1]}\n\n\n")
            filename = secure_filename(f"{os.path.splitext(file.filename)[0]}_{uuid.uuid4()}{os.path.splitext(file.filename)[1]}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if not os.path.exists("uploads/"):
                os.makedirs("uploads/")
            file.save(filepath)
            print(f"Original Video file saved to {filepath}")
            
            
            video = VideoFileClip(filepath)
            if video.duration > int(os.environ.get("MAX_VIDEO_LENGTH", 30)):
                        return jsonify({
                            "error": f"Video length exceeds maximum allowed length of {os.environ.get('MAX_VIDEO_LENGTH', 10)} seconds. Your video is {video.duration:.2f} seconds long."
                        })
            
            # Convert to MP4
            if os.path.splitext(file.filename)[1] == ".mp4":
                mp4_filepath = filepath
            else:
                mp4_filepath = os.path.splitext(filepath)[0] + '.mp4'
                video.write_videofile(mp4_filepath)
                print(f"Video file saved as MP4 to {mp4_filepath}")
            video.close()
                
            # Delete original file if it's not MP4
            if os.path.splitext(filepath)[1].lower() != '.mp4':
                os.remove(filepath)
            
            # Copy video to Cloud Storage Bucket
            cloud_filepath = f"GimpWalk_Video_{uuid.uuid4()}.mp4"
            copy_to_gcloud(
                file_path = mp4_filepath,
                destination_file_path = cloud_filepath,
                gcloud_bucket_name = os.environ.get('GCLOUD_BUCKET_NAME', 'gimpwalk-bucket'),
                GOOGLE_CLOUD_SERVICE_ACCOUNT_INFO_JSON = os.environ.get('GOOGLE_CLOUD_SERVICE_ACCOUNT_INFO_JSON')
            )
            
            # Remove local files:
            if os.path.exists(filepath):
                os.remove(filepath)
            if os.path.exists(mp4_filepath):
                os.remove(mp4_filepath)
                
            cloud_file_uri = f"gs://{os.environ.get('GCLOUD_BUCKET_NAME', 'gimpwalk-bucket')}/{cloud_filepath}"
            # Query Gemini API
            video_file = Part.from_uri(cloud_file_uri, mime_type="video/mp4")
            model = GenerativeModel(model_name=os.environ.get("GEMINI_MODEL", "gemini-1.5-pro-001"))
            print("Model initialized")
            response = model.generate_content(
                [
                    video_file,
                    f"Additional Notes From Patient:\n\n{additional_notes}",
                    gimpwalk_prompt
                    ])
                
            return jsonify({'response': response.text})
        
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True, port=8080)