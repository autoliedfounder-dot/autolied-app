#!/usr/bin/env python3
"""
Simple web interface for Sheet Music to PowerPoint converter - Lambda version
"""

import os
import subprocess
import sys
import json
import tempfile
import shutil

from flask import Flask, render_template_string, request, send_file, jsonify, make_response
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max

# Configuration - Use /tmp in Lambda
UPLOAD_FOLDER = '/tmp/uploads'
OUTPUT_FOLDER = '/tmp/outputs'

# Ensure folders exist - do this in each request for Lambda
def ensure_folders():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Call at module level for initialization
ensure_folders()

# HTML Template with improved form handling
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Sheet Music to PowerPoint</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f0f0f0;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="file"],
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            width: 100%;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        .message {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .results {
            margin-top: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
            display: none;
        }
        .lyrics-display {
            background-color: white;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin: 20px 0;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-line;
            font-family: Georgia, serif;
            font-size: 16px;
            line-height: 1.6;
        }
        .download-btn {
            background-color: #2196F3;
            margin-top: 10px;
        }
        .download-btn:hover {
            background-color: #0b7dda;
        }
        .section-header {
            font-weight: bold;
            color: #666;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 Sheet Music to PowerPoint</h1>
        
        <div id="message"></div>
        
        <form id="uploadForm">
            <div class="form-group">
                <label>PDF File:</label>
                <input type="file" name="file" id="fileInput" accept=".pdf" required>
            </div>
            
            <div class="form-group">
                <label>Title:</label>
                <input type="text" name="title" id="titleInput" placeholder="e.g., Le Secret" required>
            </div>
            
            <div class="form-group">
                <label>OpenAI API Key:</label>
                <input type="password" name="api_key" id="apiKeyInput" placeholder="sk-..." required>
            </div>
            
            <button type="submit" id="submitBtn">Convert to PowerPoint</button>
        </form>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Processing your sheet music... This may take a moment.</p>
        </div>
        
        <div class="results" id="results">
            <h2>✅ Conversion Complete!</h2>
            
            <h3>Extracted Lyrics:</h3>
            <div class="lyrics-display" id="lyricsDisplay"></div>
            
            <button class="download-btn" onclick="downloadPowerPoint()">
                📥 Download PowerPoint Presentation
            </button>
            
            <button class="download-btn" onclick="copyLyrics()">
                📋 Copy Lyrics to Clipboard
            </button>
        </div>
    </div>
    
    <script>
    let currentPptxPath = '';
    let currentLyricsText = '';
    
    document.getElementById('uploadForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const fileInput = document.getElementById('fileInput');
        const titleInput = document.getElementById('titleInput');
        const apiKeyInput = document.getElementById('apiKeyInput');
        const messageDiv = document.getElementById('message');
        const loadingDiv = document.getElementById('loading');
        const resultsDiv = document.getElementById('results');
        const submitBtn = document.getElementById('submitBtn');
        
        // Validate inputs
        if (!fileInput.files[0]) {
            showMessage('Please select a PDF file', 'error');
            return;
        }
        
        // Show loading, hide results
        loadingDiv.style.display = 'block';
        resultsDiv.style.display = 'none';
        messageDiv.innerHTML = '';
        submitBtn.disabled = true;
        
        // Create form data
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('title', titleInput.value);
        formData.append('api_key', apiKeyInput.value);
        
        try {
            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            loadingDiv.style.display = 'none';
            submitBtn.disabled = false;
            
            if (data.success) {
                // Show results
                currentPptxPath = data.pptx_path;
                currentLyricsText = data.lyrics_text;
                
                document.getElementById('lyricsDisplay').innerHTML = data.lyrics_html;
                resultsDiv.style.display = 'block';
                
                // Clear form
                fileInput.value = '';
                titleInput.value = '';
                apiKeyInput.value = '';
            } else {
                showMessage('Error: ' + (data.error || 'Processing failed'), 'error');
            }
        } catch (error) {
            loadingDiv.style.display = 'none';
            submitBtn.disabled = false;
            showMessage('Error: ' + error.message, 'error');
        }
    });
    
    function showMessage(text, type) {
        const messageDiv = document.getElementById('message');
        messageDiv.innerHTML = `<div class="message ${type}">${text}</div>`;
    }
    
    function downloadPowerPoint() {
        if (currentPptxPath) {
            window.location.href = '/download/' + encodeURIComponent(currentPptxPath);
        }
    }
    
    function copyLyrics() {
        if (currentLyricsText) {
            navigator.clipboard.writeText(currentLyricsText).then(function() {
                alert('Lyrics copied to clipboard!');
            }).catch(function(err) {
                // Fallback for older browsers
                const textArea = document.createElement("textarea");
                textArea.value = currentLyricsText;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                alert('Lyrics copied to clipboard!');
            });
        }
    }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process', methods=['POST'])
def process():
    try:
        print("=== Processing request ===")
        
        # Ensure folders exist for Lambda
        ensure_folders()
        
        # Check if file exists
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        
        if not file or not file.filename.endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Please upload a PDF file'})
        
        # Get form data
        title = request.form.get('title', 'Unknown')
        api_key = request.form.get('api_key', '')
        
        if not api_key:
            return jsonify({'success': False, 'error': 'Please provide an OpenAI API key'})
        
        # Save uploaded file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, f"{timestamp}_{filename}")
        
        file.save(input_path)
        print(f"File saved to: {input_path}")
        
        # Output paths
        output_path = os.path.join(OUTPUT_FOLDER, f"{timestamp}_output.pptx")
        
        # Import and use the processing function directly
        try:
            from run_gpt4 import process_sheet_music_with_gpt4
            
            # Process the sheet music
            processor = process_sheet_music_with_gpt4(
                pdf_path=input_path,
                output_pptx=output_path,
                api_key=api_key,
                title=title,
                max_lines_per_slide=1,
                export_text=True
            )
            
            # Read the lyrics file
            lyrics_path = output_path.replace('.pptx', '_lyrics.txt')
            lyrics_text = ""
            lyrics_html = ""
            
            if os.path.exists(lyrics_path):
                with open(lyrics_path, 'r', encoding='utf-8') as f:
                    lyrics_text = f.read()
                
                # Convert to HTML with section formatting
                lines = lyrics_text.split('\n')
                for line in lines:
                    if line.strip().startswith('[') and line.strip().endswith(']'):
                        lyrics_html += f'<div class="section-header">{line.strip()}</div>'
                    elif line.strip():
                        lyrics_html += f'{line}<br>'
                    else:
                        lyrics_html += '<br>'
            
            # Clean up input file
            if os.path.exists(input_path):
                os.remove(input_path)
            
            return jsonify({
                'success': True,
                'lyrics_text': lyrics_text,
                'lyrics_html': lyrics_html,
                'pptx_path': os.path.basename(output_path)
            })
            
        except Exception as e:
            print(f"Processing error: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Clean up on error
            if os.path.exists(input_path):
                os.remove(input_path)
            
            return jsonify({
                'success': False,
                'error': f'Processing failed: {str(e)}'
            })
            
    except Exception as e:
        print(f"Request error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': f'Request failed: {str(e)}'
        })

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        
        if not os.path.exists(file_path):
            return "File not found", 404
        
        # Read file and create response
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        response = make_response(file_data)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        response.headers['Content-Disposition'] = f'attachment; filename=lyrics_presentation.pptx'
        
        # Clean up the file after sending
        os.remove(file_path)
        
        # Also remove the lyrics file if it exists
        lyrics_path = file_path.replace('.pptx', '_lyrics.txt')
        if os.path.exists(lyrics_path):
            os.remove(lyrics_path)
        
        return response
        
    except Exception as e:
        print(f"Download error: {str(e)}")
        return "Error downloading file", 500

@app.route('/health')
def health():
    """Health check endpoint for Lambda"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/test')
def test():
    """Test endpoint to verify Lambda environment"""
    import platform
    
    # Test folder creation
    ensure_folders()
    
    info = {
        'status': 'ok',
        'platform': platform.system(),
        'python_version': platform.python_version(),
        'tmp_writable': os.access('/tmp', os.W_OK),
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'output_folder_exists': os.path.exists(OUTPUT_FOLDER),
        'dependencies': {}
    }
    
    # Check if key dependencies are available
    try:
        import fitz
        info['dependencies']['PyMuPDF'] = fitz.__version__
    except ImportError as e:
        info['dependencies']['PyMuPDF'] = f'Not installed: {str(e)}'
    
    try:
        import openai
        info['dependencies']['openai'] = openai.__version__
    except ImportError as e:
        info['dependencies']['openai'] = f'Not installed: {str(e)}'
    
    try:
        from pptx import Presentation
        info['dependencies']['python-pptx'] = 'Installed'
    except ImportError as e:
        info['dependencies']['python-pptx'] = f'Not installed: {str(e)}'
    
    return jsonify(info)

if __name__ == '__main__':
    # For local testing only
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)