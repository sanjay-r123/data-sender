from flask import Flask, request, render_template_string
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
content_store = []  # List to store submissions (latest at end)
submission_locked = False  # Lock submissions until acknowledgement

SECRET_KEY = os.getenv("SECRET_KEY")  # From .env

FORM_HTML = """
<!DOCTYPE html>
<html>
<body>
    <h2>Submit Code</h2>
    {% if locked %}
        <p>Submission locked. Waiting for typing acknowledgement.</p>
    {% else %}
        <form method="post" action="/submit">
            <label>Secret Key: <input type="text" name="key" required></label><br><br>
            <label>Content: <textarea name="content" rows="5" cols="50" required></textarea></label><br><br>
            <input type="submit" value="Submit">
        </form>
    {% endif %}
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(FORM_HTML, locked=submission_locked)

@app.route('/submit', methods=['POST'])
def submit():
    global submission_locked
    if submission_locked:
        return "Submission locked. Wait for typing acknowledgement.", 403
    key = request.form.get('key')
    content = request.form.get('content')
    if key != SECRET_KEY or not content:
        return "Invalid key or empty content", 403
    content_store.append(content)
    submission_locked = True
    return "Content stored. Waiting for typing acknowledgement."

@app.route('/latest', methods=['GET'])
def get_latest():
    key = request.args.get('key')
    if key != SECRET_KEY or not content_store:
        return "Invalid key or no content", 403
    return content_store[-1]  # Return latest content

@app.route('/acknowledge', methods=['POST'])
def acknowledge():
    global submission_locked
    key = request.form.get('key')
    if key != SECRET_KEY:
        return "Invalid key", 403
    submission_locked = False
    return "Acknowledgement received. New submissions allowed."
