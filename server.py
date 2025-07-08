from flask import Flask, request, render_template_string
import uuid

app = Flask(__name__)
content_store = {}  # In-memory storage (use SQLite for persistence)
SECRET_KEY = str(uuid.uuid4())  # Unique key, printed on local run

# HTML form for submitting content
FORM_HTML = """
<!DOCTYPE html>
<html>
<body>
    <h2>Submit Code</h2>
    <form method="post" action="/submit">
        <label>Secret Key: <input type="text" name="key" required></label><br><br>
        <label>Content: <textarea name="content" rows="5" cols="50" required></textarea></label><br><br>
        <input type="submit" value="Submit">
    </form>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(FORM_HTML)

@app.route('/submit', methods=['POST'])
def submit():
    key = request.form.get('key')
    content = request.form.get('content')
    if key != SECRET_KEY or not content:
        return "Invalid key or empty content", 403
    content_id = str(uuid.uuid4())
    content_store[content_id] = content
    return f"Content stored. Retrieve at /get/{content_id} with secret key: {SECRET_KEY}"

@app.route('/get/<content_id>', methods=['GET'])
def get_content(content_id):
    key = request.args.get('key')
    if key != SECRET_KEY or content_id not in content_store:
        return "Invalid key or content ID", 403
    content = content_store[content_id]
    del content_store[content_id]  # One-time retrieval
    return content

if __name__ == '__main__':
    print(f"Secret Key: {SECRET_KEY}")
    app.run(host='0.0.0.0', port=5000)