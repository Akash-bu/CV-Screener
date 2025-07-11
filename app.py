from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename 
import os 
import json
from openai import OpenAI 
from PyPDF2 import PdfReader

app = Flask(__name__, template_folder='template')
client = OpenAI()

UPLOAD_FOLDER = "uploads"
ALLOWED_EXT = {'.pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER 
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """
    Check if the uploaded file has an allowed extension.
    """
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXT

def extract_text(filepath):
    reader = PdfReader(filepath)
    text = '\n'.join(page.extract_text() or '' for page in reader.pages)
    return text 
    

@app.route('/', methods = ['GET', 'POST'])
def index():
    error = None 
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        file = request.files.get('resume')

        if not (name and phone and email and allowed_file(file.filename)):
            error = 'Please fill in all the fields and upload only a PDF file'
            return render_template('index.html', error=error)
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        cv_text = extract_text(filepath)

        system_prompt = (
            'You are an expert recruiter screening resumes for AI positions. ' 
            'Given the CV text, analyze the text to find key words related to AI in skills and respond with a JSON object with keys: "verdict" (either "Pass" or "Fail") ' 
            'and "feedback" (an array of improvement suggestions).'  
        )

        messages = [
            {
                'role':'system', 'content': system_prompt
            },
            {
                'role': 'user', 'content': cv_text
            }
        ]

        response = client.chat.completions.create(
            model = 'gpt-4.1',
            messages = messages,
            temperature = 0.3
        )

        try:
            result_json = response.choices[0].message.content
            result = json.loads(result_json)
        except Exception:
            result = {
                'verdict': 'Error',
                'feedback': ['Could not parse openai response']
            }

        return render_template('review.html', name=name, 
                               verdict = result.get('verdict',''),
                               feedback = result.get('feedback', []))


    return render_template('index.html', error=error)

if __name__ == '__main__':
    app.run(debug=True, port = 5000)