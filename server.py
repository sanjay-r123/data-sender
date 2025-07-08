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
    <meta http-equiv="refresh" content="5">
</head>
<body>
    <h2>Submit Code</h2>
    {% if locked %}
        <p style="color: orange;">Submission locked. Waiting for typing acknowledgement.</p>
        <p>Current queue size: {{ queue_size }}</p>
        <a href="/force_unlock?key={{ secret_key }}">Force Unlock (Emergency)</a>
    {% else %}
        <p style="color: green;">Ready to accept submissions</p>
        <p>Current queue size: {{ queue_size }}</p>
        <form method="post" action="/submit">
            <label>Secret Key: <input type="password" name="key" required></label><br><br>
            <label>Content: <textarea name="content" rows="10" cols="80" required></textarea></label><br><br>
            <input type="submit" value="Submit">
        </form>
    {% endif %}
    
    <hr>
    <h3>Recent Submissions:</h3>
    <ul>
    {% for item in recent_items %}
        <li>{{ item[:100] }}{% if item|length > 100 %}...{% endif %}</li>
    {% endfor %}
    </ul>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(
        FORM_HTML, 
        locked=submission_locked, 
        queue_size=len(content_store),
        secret_key=SECRET_KEY,
        recent_items=content_store[-5:] if content_store else []
    )

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
    
    print(f"Content submitted and locked. Queue size: {len(content_store)}")
    
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
    global submission_locked, content_store
    
    # Fixed the key extraction logic
    key = None
    if request.form.get('key'):
        key = request.form.get('key')
    elif request.json and request.json.get('key'):
        key = request.json.get('key')
    elif request.args.get('key'):
        key = request.args.get('key')
    
    if not key:
        return "Missing key parameter", 400
    
    if key != SECRET_KEY:
        return "Invalid key", 403
    
    # Remove the processed content from queue
    if content_store:
        processed_content = content_store.pop(-1)  # Remove latest content
        print(f"Processed and removed content: {processed_content[:50]}...")
    
    submission_locked = False
    print("Acknowledgment received. Submissions unlocked.")
    
    return "Acknowledgement received. New submissions allowed."

@app.route('/force_unlock', methods=['GET'])
def force_unlock():
    """Emergency unlock in case acknowledgment fails"""
    global submission_locked
    
    key = request.args.get('key')
    
    if not key or key != SECRET_KEY:
        return "Invalid key", 403
    
    submission_locked = False
    print("Force unlock executed.")
    
    return "Force unlock successful. <a href='/'>Back to home</a>"

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

@app.route('/clear_queue', methods=['POST'])
def clear_queue():
    """Clear the content queue"""
    global content_store, submission_locked
    
    key = request.form.get('key') or request.args.get('key')
    
    if not key or key != SECRET_KEY:
        return "Invalid key", 403
    
    content_store.clear()
    submission_locked = False
    
    return "Queue cleared successfully."

if __name__ == "__main__":
    print(f"Secret key loaded: {'Yes' if SECRET_KEY else 'No'}")
    print(f"Secret key value: {SECRET_KEY}")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
