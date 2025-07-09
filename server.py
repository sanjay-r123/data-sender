from flask import Flask, request, render_template_string
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

content_store = []
submission_locked = False
SECRET_KEY = os.getenv("SECRET_KEY", "my-secret-2025")

FORM_RENDER = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Submit Content</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
    <div class="bg-white p-8 rounded-lg shadow-lg max-w-2xl w-full">
        <h1 class="text-2xl font-bold mb-6 text-gray-800">Submit Code Content</h1>
        
        {% if content_store %}
            <div class="mb-6 p-4 bg-{% if locked %}yellow-100{% else %}green-100{% endif %} rounded">
                <p class="text-sm font-medium">
                    Status: {% if locked %}
                        <span class="text-yellow-700">Locked - Waiting for typing acknowledgement</span>
                    {% else %}
                        <span class="text-green-700">Ready to accept submissions</span>
                    {% endif %}
                </p>
                <p class="text-sm">Current queue size: {{ queue_size }}</p>
            </div>
        {% else %}
            <div class="mb-6 p-4 bg-green-100 rounded">
                <p class="text-sm font-medium text-green-700">Ready to accept submissions</p>
                <p class="text-sm">Current queue size: {{ queue_size }}</p>
            </div>
        {% endif %}

        <form method="POST" action="/submit" class="space-y-4">
            <div>
                <label for="content" class="block text-sm font-medium text-gray-700">Content</label>
                <textarea id="content" name="content" rows="8" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50" required></textarea>
            </div>
            <button type="submit" class="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2" {% if locked %}disabled{% endif %}>
                {% if locked %}Submission Locked{% else %}Submit Content{% endif %}
            </button>
        </form>

        {% if locked %}
            <div class="mt-4 text-center">
                <a href="/force_unlock?key={{ secret_key }}" class="text-sm text-red-600 hover:text-red-800">Emergency Force Unlock</a>
            </div>
        {% endif %}

        <hr class="my-6 border-gray-200">

        <h2 class="text-lg font-semibold mb-4 text-gray-800">Recent Submissions</h2>
        {% if recent_items %}
            <ul class="space-y-2">
                {% for item in recent_items %}
                    <li class="text-sm text-gray-600 bg-gray-50 p-2 rounded">{{ item[:100] }}{% if item|length > 100 %}...{% endif %}</li>
                {% endfor %}
            </ul>
        {% else %}
            <p class="text-sm text-gray-500">No submissions yet</p>
        {% endif %}
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(
        FORM_RENDER,
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
    
    content = request.form.get('content')
    
    if not content:
        return "Missing content", 400
    
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
    
    return content_store[-1]

@app.route('/acknowledge', methods=['POST'])
def acknowledge():
    global submission_locked, content_store
    
    key = request.form.get('key') or request.json.get('key') or request.args.get('key')
    
    if not key:
        return "Missing key parameter", 400
    
    if key != SECRET_KEY:
        return "Invalid key", 403
    
    if content_store:
        processed_content = content_store.pop(-1)
        print(f"Processed and removed content: {processed_content[:50]}...")
    
    submission_locked = False
    print("Acknowledgment received. Submissions unlocked.")
    
    return "Acknowledgement received. New submissions allowed."

@app.route('/force_unlock', methods=['GET'])
def force_unlock():
    """Emergency unlock"""
    global submission_locked
    
    key = request.args.get('key')
    
    if not key or key != SECRET_KEY:
        return "Invalid key", 403
    
    submission_locked = False
    
    return "Submission unlocked successfully."

@app.route('/status', methods=['GET'])
def status():
    """Debug endpoint"""
    key = request.args.get('key')
    
    if not key or key != SECRET_KEY:
        return "Invalid key", 403
    
    return {
        "status": submission_locked,
        "queue_size": len(content_store),
        "latest_preview": content_store[-1][:100] + "..." if content_store else "No content"
    }

@app.route('/clear_queue', methods=['POST'])
def clear_queue():
    """Clear content queue"""
    global content_store, submission_locked
    
    key = request.form.get('key') or request.args.get('key')
    
    if not key or key != SECRET_KEY:
        return "Invalid key", 403
    
    content_store.clear()
    submission_locked = False
    
    return "Queue cleared successfully."

@app.route('/')
if __name__ == "__main__":
    print(f"Secret key loaded: {SECRET_KEY:'Yes' if SECRET_KEY or else 'No'})
    print(f"Secret key loaded: {SECRET_KEY}")
    app.run(debug=True, host='0.0.0',.0, port=int(os.environ.get('PORT', 5000)))
