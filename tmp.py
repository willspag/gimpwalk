from google.cloud import aiplatform
import vertexai
from vertexai.generative_models import GenerativeModel
import os

# TODO(developer): Update and un-comment below line
# project_id = "PROJECT_ID"

vertexai.init(project=os.environ.get("GCLOUD_PROJECT_ID"))

model = GenerativeModel(model_name="gemini-1.5-flash-001")

response = model.generate_content(
    "What's a good name for a flower shop that specializes in selling bouquets of dried flowers?"
)

print(response.text)