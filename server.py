from flask import Flask, request, render_template_string
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Global variables
content_store = []  # List to store submissions (latest at end)
submission_locked = False  # Lock submissions until acknowledgement
SECRET_KEY = os.getenv("SECRET_KEY", "my-secret-2025")  # Fallback if .env not found

FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Submit Code</title>
    <meta charset="utf-8">
</head>
<body>
    <h2>Submit Code</h2>
    {% if locked %}
        <p style="color: orange;">Submission locked. Waiting for typing acknowledgement.</p>
        <p>Current queue size: {{ queue_size }}</p>
    {% else %}
        <p style="color: green;">Ready to accept submissions</p>
        <p>Current queue size: {{ queue_size }}</p>
        <form method="post" action="/submit">
            <label>Secret Key: <input type="password" name="key" required></label><br><br>
            <label>Content: <textarea name="content" rows="10" cols="80" required></textarea></label><br><br>
            <input type="submit" value="Submit">
        </form>
    {% endif %}
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(FORM_HTML, locked=submission_locked, queue_size=len(content_store))

@app.route('/submit', methods=['POST'])
def submit():
    global submission_locked
    
    if submission_locked:
        return "Submission locked. Wait for typing acknowledgement.", 403
    
    key = request.form.get('key')
    content = request.form.get('content')
    
    if not key or not content:
        return "Missing key or content", 400
    
    if key != SECRET_KEY:
        return "Invalid key", 403
    
    content_store.append(content.strip())
    submission_locked = True
    
    return f"Content stored successfully. Queue position: {len(content_store)}. Waiting for typing acknowledgement."

@app.route('/latest', methods=['GET'])
def get_latest():
    key = request.args.get('key')
    
    if not key:
        return "Missing key parameter", 400
    
    if key != SECRET_KEY:
        return "Invalid key", 403
    
    if not content_store:
        return "No content available", 404
    
    return content_store[-1]  # Return latest content

@app.route('/acknowledge', methods=['POST'])
def acknowledge():
    global submission_locked
    
    key = request.form.get('key')
    
    if not key:
        return "Missing key parameter", 400
    
    if key != SECRET_KEY:
        return "Invalid key", 403
    
    submission_locked = False
    return "Acknowledgement received. New submissions allowed."

@app.route('/status', methods=['GET'])
def status():
    """Debug endpoint to check system status"""
    key = request.args.get('key')
    
    if not key or key != SECRET_KEY:
        return "Invalid key", 403
    
    return {
        "locked": submission_locked,
        "queue_size": len(content_store),
        "latest_preview": content_store[-1][:100] + "..." if content_store else "No content"
    }

if __name__ == "__main__":
    print(f"Secret key loaded: {'Yes' if SECRET_KEY else 'No'}")
    print(f"Secret key value: {SECRET_KEY}")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
