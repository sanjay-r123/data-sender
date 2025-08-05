from flask import Flask, request, render_template_string, jsonify, redirect, make_response
import os
from dotenv import load_dotenv
import base64
import json
from datetime import datetime

load_dotenv()
app = Flask(__name__)

content_store = []
screenshot_store = []  # New: Store screenshots
submission_locked = False
screenshot_capture_requested = False  # New: Flag for screenshot requests
SECRET_KEY = os.getenv("SECRET_KEY", "my-secret-2025")

FORM_RENDER = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content & Screenshot Manager</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="container mx-auto p-4">
        <!-- Header -->
        <div class="bg-white p-6 rounded-lg shadow-lg mb-6">
            <h1 class="text-3xl font-bold mb-4 text-gray-800">Content & Screenshot Manager</h1>
            
            <div id="status" class="mb-6 p-4 bg-{% if locked %}yellow-100{% else %}green-100{% endif %} rounded">
                <p class="text-sm font-medium">
                    Status: {% if locked %}
                        <span class="text-yellow-700">Locked - Waiting for typing acknowledgement</span>
                    {% else %}
                        <span class="text-green-700">Ready to accept submissions</span>
                    {% endif %}
                </p>
                <p class="text-sm">Content queue size: <span id="queue-size">{{ queue_size }}</span></p>
                <p class="text-sm">Screenshots collected: <span id="screenshot-count">{{ screenshot_count }}</span></p>
            </div>
        </div>

        <!-- Content Submission Form -->
        <div class="bg-white p-6 rounded-lg shadow-lg mb-6">
            <h2 class="text-xl font-semibold mb-4 text-gray-800">Submit Content</h2>
            <form id="submit-form" method="POST" action="/submit" class="space-y-4">
                <div>
                    <label for="content" class="block text-sm font-medium text-gray-700">Content</label>
                    <textarea id="content" name="content" rows="6" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50" required></textarea>
                </div>
                <div class="flex space-x-4">
                    <button type="submit" class="bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2" {% if locked %}disabled{% endif %}>
                        {% if locked %}Submission Locked{% else %}Submit Content{% endif %}
                    </button>
                    <button type="button" onclick="clearQueue()" class="bg-orange-600 text-white py-2 px-4 rounded-md hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2">
                        Clear Queue
                    </button>
                </div>
            </form>
            <div class="mt-4 text-sm text-gray-600">
                <p><strong>Note:</strong> Press ESC while typing to interrupt the current task. The task will be removed from the queue and you'll need to resubmit it.</p>
            </div>
        </div>

        <!-- Screenshot Controls -->
        <div class="bg-white p-6 rounded-lg shadow-lg mb-6">
            <h2 class="text-xl font-semibold mb-4 text-gray-800">Screenshot Controls</h2>
            <div class="flex space-x-4">
                <button onclick="requestScreenshot()" class="bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2">
                    Capture Screenshot
                </button>
                <button onclick="clearScreenshots()" class="bg-red-600 text-white py-2 px-4 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2">
                    Clear All Screenshots
                </button>
            </div>
        </div>

        <!-- Screenshot Gallery -->
        <div class="bg-white p-6 rounded-lg shadow-lg mb-6">
            <h2 class="text-xl font-semibold mb-4 text-gray-800">Screenshot Gallery</h2>
            <div id="screenshot-gallery" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {% if screenshots %}
                    {% for screenshot in screenshots %}
                        <div class="border rounded-lg p-3 bg-gray-50">
                            <img src="data:image/png;base64,{{ screenshot.data }}" alt="Screenshot {{ loop.index }}" class="w-full h-48 object-cover rounded cursor-pointer" onclick="openModal('{{ screenshot.data }}', '{{ screenshot.timestamp }}')">
                            <p class="text-xs text-gray-500 mt-2">{{ screenshot.timestamp }}</p>
                        </div>
                    {% endfor %}
                {% else %}
                    <p class="text-gray-500 col-span-full text-center py-8">No screenshots captured yet</p>
                {% endif %}
            </div>
        </div>

        <!-- Recent Content Submissions -->
        <div class="bg-white p-6 rounded-lg shadow-lg">
            <h2 class="text-xl font-semibold mb-4 text-gray-800">Recent Content Submissions</h2>
            {% if recent_items %}
                <ul class="space-y-2">
                    {% for item in recent_items %}
                        <li class="text-sm text-gray-600 bg-gray-50 p-3 rounded">{{ item[:200] }}{% if item|length > 200 %}...{% endif %}</li>
                    {% endfor %}
                </ul>
            {% else %}
                <p class="text-sm text-gray-500">No submissions yet</p>
            {% endif %}
        </div>

        {% if locked %}
            <div class="mt-6 text-center">
                <a href="/force_unlock?key={{ secret_key }}" class="text-sm text-red-600 hover:text-red-800">Emergency Force Unlock</a>
            </div>
        {% endif %}
    </div>

    <!-- Screenshot Modal -->
    <div id="screenshot-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50" onclick="closeModal()">
        <div class="bg-white p-4 rounded-lg max-w-4xl max-h-full overflow-auto" onclick="event.stopPropagation()">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold">Screenshot Details</h3>
                <button onclick="closeModal()" class="text-gray-500 hover:text-gray-700">&times;</button>
            </div>
            <img id="modal-image" src="" alt="Full size screenshot" class="max-w-full h-auto">
            <p id="modal-timestamp" class="text-sm text-gray-500 mt-2"></p>
        </div>
    </div>

    <script>
        function updateStatus() {
            fetch('/status?key={{ secret_key }}')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Status update:', data);
                    const statusDiv = document.getElementById('status');
                    const queueSizeSpan = document.getElementById('queue-size');
                    const screenshotCountSpan = document.getElementById('screenshot-count');
                    const submitButton = document.querySelector('form button');

                    queueSizeSpan.textContent = data.queue_size;
                    screenshotCountSpan.textContent = data.screenshot_count || 0;
                    
                    if (data.locked) {
                        statusDiv.classList.remove('bg-green-100');
                        statusDiv.classList.add('bg-yellow-100');
                        statusDiv.querySelector('p:first-child').innerHTML = '<span class="text-yellow-700">Locked - Waiting for typing acknowledgement</span>';
                        submitButton.disabled = true;
                        submitButton.textContent = 'Submission Locked';
                    } else {
                        statusDiv.classList.remove('bg-yellow-100');
                        statusDiv.classList.add('bg-green-100');
                        statusDiv.querySelector('p:first-child').innerHTML = '<span class="text-green-700">Ready to accept submissions</span>';
                        submitButton.disabled = false;
                        submitButton.textContent = 'Submit Content';
                    }
                })
                .catch(error => {
                    console.error('Status update failed:', error);
                });
        }

        function requestScreenshot() {
            fetch('/request_screenshot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `key={{ secret_key }}`
            })
            .then(response => response.text())
            .then(data => {
                alert('Screenshot request sent to client');
                setTimeout(() => location.reload(), 2000); // Reload after 2 seconds
            })
            .catch(error => {
                console.error('Error requesting screenshot:', error);
                alert('Failed to request screenshot');
            });
        }

        function clearScreenshots() {
            if (confirm('Are you sure you want to clear all screenshots?')) {
                fetch('/clear_screenshots', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `key={{ secret_key }}`
                })
                .then(response => response.text())
                .then(data => {
                    alert('Screenshots cleared');
                    location.reload();
                })
                .catch(error => {
                    console.error('Error clearing screenshots:', error);
                    alert('Failed to clear screenshots');
                });
            }
        }

        function openModal(imageData, timestamp) {
            const modal = document.getElementById('screenshot-modal');
            const modalImage = document.getElementById('modal-image');
            const modalTimestamp = document.getElementById('modal-timestamp');
            
            modalImage.src = 'data:image/png;base64,' + imageData;
            modalTimestamp.textContent = 'Captured: ' + timestamp;
            modal.classList.remove('hidden');
        }

        function closeModal() {
            const modal = document.getElementById('screenshot-modal');
            modal.classList.add('hidden');
        }

        function clearQueue() {
            if (confirm('Are you sure you want to clear the entire content queue?')) {
                fetch('/clear_queue', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `key={{ secret_key }}`
                })
                .then(response => response.text())
                .then(data => {
                    alert('Content queue cleared');
                    location.reload();
                })
                .catch(error => {
                    console.error('Error clearing queue:', error);
                    alert('Failed to clear queue');
                });
            }
        }

        setInterval(updateStatus, 5000);
        updateStatus();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    print("Rendering index page")
    response = make_response(render_template_string(
        FORM_RENDER,
        locked=submission_locked,
        queue_size=len(content_store),
        screenshot_count=len(screenshot_store),
        secret_key=SECRET_KEY,
        recent_items=content_store[-5:] if content_store else [],
        screenshots=screenshot_store[-10:] if screenshot_store else []  # Show last 10 screenshots
    ))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

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
    
    return redirect('/', code=302)

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
    print(f"Acknowledgment processed. Submissions unlocked. New queue size: {len(content_store)}")
    
    return "Acknowledgement received. New submissions allowed."

@app.route('/interrupt_acknowledge', methods=['POST'])
def interrupt_acknowledge():
    global submission_locked, content_store
    
    print("Received INTERRUPT ACK request")
    
    key = request.form.get('key')
    if not key:
        print("Interrupt ACK rejected: Missing key parameter")
        return "Missing key parameter", 400
    
    if key != SECRET_KEY:
        print(f"Interrupt ACK rejected: Invalid key provided: {key}")
        return "Invalid key", 403
    
    print(f"Interrupt ACK validated. Current queue size: {len(content_store)}, Locked: {submission_locked}")
    
    if content_store:
        interrupted_content = content_store.pop(-1)
        print(f"Interrupted and removed content: {interrupted_content[:50]}...")
        print("Task was interrupted by user (ESC key) and removed from queue")
    else:
        print("No content in queue to remove")
    
    submission_locked = False
    print(f"Interrupt acknowledgment processed. Submissions unlocked. New queue size: {len(content_store)}")
    
    return "Interrupt acknowledgement received. Task removed from queue. New submissions allowed."

# New screenshot-related endpoints
@app.route('/request_screenshot', methods=['POST'])
def request_screenshot():
    global screenshot_capture_requested
    
    print("Received screenshot request")
    key = request.form.get('key')
    
    if not key or key != SECRET_KEY:
        print(f"Screenshot request rejected: Invalid key provided: {key}")
        return "Invalid key", 403
    
    screenshot_capture_requested = True
    print("Screenshot capture requested")
    
    return "Screenshot request sent to client"

@app.route('/check_screenshot_command', methods=['GET'])
def check_screenshot_command():
    global screenshot_capture_requested
    
    key = request.args.get('key')
    
    if not key or key != SECRET_KEY:
        return "Invalid key", 403
    
    capture_requested = screenshot_capture_requested
    screenshot_capture_requested = False  # Reset flag after checking
    
    return jsonify({"capture_requested": capture_requested})

@app.route('/upload_screenshot', methods=['POST'])
def upload_screenshot():
    print("Received screenshot upload")
    
    try:
        data = request.get_json()
        key = data.get('key')
        
        if not key or key != SECRET_KEY:
            print(f"Screenshot upload rejected: Invalid key provided: {key}")
            return "Invalid key", 403
        
        screenshot_data = data.get('screenshot')
        timestamp = data.get('timestamp', datetime.now().isoformat())
        
        if not screenshot_data:
            print("Screenshot upload rejected: Missing screenshot data")
            return "Missing screenshot data", 400
        
        # Store screenshot with metadata
        screenshot_entry = {
            'data': screenshot_data,
            'timestamp': timestamp,
            'size': len(screenshot_data)
        }
        
        screenshot_store.append(screenshot_entry)
        print(f"Screenshot stored successfully. Total screenshots: {len(screenshot_store)}")
        
        return "Screenshot uploaded successfully"
        
    except Exception as e:
        print(f"Error processing screenshot upload: {e}")
        return f"Error processing screenshot: {str(e)}", 500

@app.route('/clear_screenshots', methods=['POST'])
def clear_screenshots():
    global screenshot_store
    
    print("Received clear screenshots request")
    key = request.form.get('key')
    
    if not key or key != SECRET_KEY:
        print(f"Clear screenshots rejected: Invalid key provided: {key}")
        return "Invalid key", 403
    
    screenshot_store.clear()
    print("Screenshots cleared successfully")
    
    return "Screenshots cleared successfully"

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
    
    return redirect('/', code=302)

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
        "screenshot_count": len(screenshot_store),
        "latest_preview": content_store[-1][:100] + "..." if content_store else "No content"
    }
    print(f"Status response: {status_info}")
    response = jsonify(status_info)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

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
    print("Screenshot functionality enabled")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
