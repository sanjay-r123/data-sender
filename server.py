from flask import Flask, request, render_template_string, jsonify
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
        
        <div id="status" class="mb-6 p-4 bg-{% if locked %}yellow-100{% else %}green-100{% endif %} rounded">
            <p class="text-sm font-medium">
                Status: {% if locked %}
                    <span class="text-yellow-700">Locked - Waiting for typing acknowledgement</span>
                {% else %}
                    <span class="text-green-700">Ready to accept submissions</span>
                {% endif %}
            </p>
            <p class="text-sm">Current queue size: <span id="queue-size">{{ queue_size }}</span></p>
        </div>

        <form id="submit-form" method="POST" action="/submit" class="space-y-4">
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
    <script>
        // Periodically check server status without reloading the page
        function updateStatus() {
            fetch('/status?key={{ secret_key }}')
                .then(response => response.json())
                .then(data => {
                    const statusDiv = document.getElementById('status');
                    const queueSizeSpan = document.getElementById('queue-size');
                    const submitButton = document.querySelector('form button');
                    const forceUnlockLink = document.querySelector('a[href^="/force_unlock"]');

                    queueSizeSpan.textContent = data.queue_size;
                    if (data.locked) {
                        statusDiv.classList.remove('bg-green-100');
                        statusDiv.classList.add('bg-yellow-100');
                        statusDiv.querySelector('p:first-child').innerHTML = '<span class="text-yellow-700">Locked - Waiting for typing acknowledgement</span>';
                        submitButton.disabled = true;
                        submitButton.textContent = 'Submission Locked';
                        if (!forceUnlockLink) {
                            const div = document.createElement('div');
                            div.className = 'mt-4 text-center';
                            div.innerHTML = '<a href="/force_unlock?key={{ secret_key }}" class="text-sm text-red-600 hover:text-red-800">Emergency Force Unlock</a>';
                            document.querySelector('form').after(div);
                        }
                    } else {
                        statusDiv.classList.remove('bg-yellow-100');
                        statusDiv.classList.add('bg-green-100');
                        statusDiv.querySelector('p:first-child').innerHTML = '<span class="text-green-700">Ready to accept submissions</span>';
                        submitButton.disabled = false;
                        submitButton.textContent = 'Submit Content';
                        if (forceUnlockLink) {
                            forceUnlockLink.parentElement.remove();
                        }
                    }
                })
                .catch(error => console.error('Status update failed:', error));
        }

        // Check status every 5 seconds
        setInterval(updateStatus, 5000);
        // Initial check
        updateStatus();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    print("Rendering index page")
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
    
    print("Received submit request")
    if submission_locked:
        print("Submission rejected: Form is locked")
        return "Submission locked. Wait for typing acknowledgement.", 403
    
    content = request.form.get('content')
    
    if not content:
        print("Submission rejected: Missing content")
        return "Missing content", 400
    
    content_store.append(content.strip())
    submission_locked = True
    
    print(f"Content submitted and locked. Queue size: {len(content_store)}")
    
    return f"Content stored successfully. Queue position: {len(content_store)}. Waiting for typing acknowledgement."

@app.route('/latest', methods=['GET'])
def get_latest():
    key = request.args.get('key')
    
    print("Received latest request")
    if not key:
        print("Latest request rejected: Missing key")
        return "Missing key parameter", 400
    
    if key != SECRET_KEY:
        print(f"Latest request rejected: Invalid key provided: {key}")
        return "Invalid key", 403
    
    if not content_store:
        print("Latest request: No content available")
        return "No content available", 404
    
    print(f"Returning latest content: {content_store[-1][:50]}...")
    return content_store[-1]

@app.route('/acknowledge', methods=['POST'])
def acknowledge():
    global submission_locked, content_store
    
    print("Received ACK request")
    
    key = request.form.get('key')
    if not key:
        print("ACK rejected: Missing key parameter")
        return "Missing key parameter", 400
    
    if key != SECRET_KEY:
        print(f"ACK rejected: Invalid key provided: {key}")
        return "Invalid key", 403
    
    print(f"ACK validated. Current queue size: {len(content_store)}, Locked: {submission_locked}")
    
    if content_store:
        processed_content = content_store.pop(-1)
        print(f"Processed and removed content: {processed_content[:50]}...")
    else:
        print("No content in queue to process")
    
    submission_locked = False
    print("Acknowledgment processed. Submissions unlocked. New queue size: {len(content_store)}")
    
    return "Acknowledgement received. New submissions allowed."

@app.route('/force_unlock', methods=['GET'])
def force_unlock():
    global submission_locked
    
    print("Received force unlock request")
    key = request.args.get('key')
    
    if not key or key != SECRET_KEY:
        print(f"Force unlock rejected: Invalid key provided: {key}")
        return "Invalid key", 403
    
    submission_locked = False
    print("Force unlock executed.")
    
    return "Submission unlocked successfully."

@app.route('/status', methods=['GET'])
def status():
    key = request.args.get('key')
    
    print("Received status request")
    if not key or key != SECRET_KEY:
        print(f"Status request rejected: Invalid key provided: {key}")
        return "Invalid key", 403
    
    status_info = {
        "locked": submission_locked,
        "queue_size": len(content_store),
        "latest_preview": content_store[-1][:100] + "..." if content_store else "No content"
    }
    print(f"Status response: {status_info}")
    return jsonify(status_info)

@app.route('/clear_queue', methods=['POST'])
def clear_queue():
    global content_store, submission_locked
    
    print("Received clear queue request")
    key = request.form.get('key') or request.args.get('key')
    
    if not key or key != SECRET_KEY:
        print(f"Clear queue rejected: Invalid key provided: {key}")
        return "Invalid key", 403
    
    content_store.clear()
    submission_locked = False
    print("Queue cleared successfully.")
    
    return "Queue cleared successfully."

if __name__ == "__main__":
    print(f"Secret key loaded: {'Yes' if SECRET_KEY else 'No'}")
    print(f"Secret key value: {SECRET_KEY}")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
