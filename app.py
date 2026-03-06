"""
Revit Journal Analyzer - Flask Web Application
Analyzes Revit journal files for crash diagnosis, errors, and performance issues.
"""

import os
from pathlib import Path
from flask import Flask, request, jsonify, render_template, Response

from parser import JournalParser, parse_journal
from pdf_generator import generate_pdf

# Azure Blob Storage
from azure.storage.blob import BlobServiceClient

app = Flask(__name__)

# -----------------------------
# AZURE BLOB STORAGE SETUP
# -----------------------------
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

blob_service_client = None
container_client = None

if connection_string:
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client("demo-files")
        print("✅ Azure Blob Storage connected")
    except Exception as e:
        print(f"⚠️ Azure Blob connection failed: {e}")
else:
    print("⚠️ No Azure storage connection string found")


def upload_to_blob(file_bytes, filename):
    """Upload file to Azure Blob Storage."""
    if not container_client:
        return

    try:
        blob_client = container_client.get_blob_client(filename)
        blob_client.upload_blob(file_bytes, overwrite=True)
        print(f"☁️ Uploaded to Azure Blob: {filename}")
    except Exception as e:
        print(f"Azure upload failed: {e}")


# -----------------------------
# DISABLE CACHE DURING DEV
# -----------------------------
@app.after_request
def add_header(response):
    """Add headers to prevent caching during development."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


# -----------------------------
# JOURNAL PARSER INIT
# -----------------------------
XML_PATTERN_FILE = Path(__file__).parent / "Search_v8_b.xml"
parser = JournalParser(str(XML_PATTERN_FILE) if XML_PATTERN_FILE.exists() else None)


# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def index():
    """Render the main analysis page."""
    return render_template("index.html")


# -----------------------------
# FILE UPLOAD & ANALYSIS
# -----------------------------
@app.route("/upload", methods=["POST"])
def upload():
    """Handle file upload and return analysis results."""
    file = request.files.get("file")

    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    allowed_extensions = {'.txt', '.log', '.journal'}
    ext = Path(file.filename).suffix.lower()

    if ext not in allowed_extensions:
        return jsonify({
            "error": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        }), 400

    try:
        file_bytes = file.read()

        if not file_bytes.strip():
            return jsonify({"error": "File is empty"}), 400

        # Upload original file to Azure
        upload_to_blob(file_bytes, file.filename)

        # Decode for parsing
        content = file_bytes.decode("utf-8", errors="ignore")

        result = parser.parse(content)

        result['filename'] = file.filename

        return jsonify(result)

    except Exception as e:
        app.logger.error(f"Error parsing file: {e}")
        return jsonify({"error": f"Error parsing file: {str(e)}"}), 500


# -----------------------------
# GENERATE PDF REPORT
# -----------------------------
@app.route("/generate-pdf", methods=["POST"])
def generate_pdf_report():
    """Generate PDF report from analysis data."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        pdf_bytes = generate_pdf(data)

        filename = data.get('filename', 'journal_analysis')
        if filename.endswith('.txt'):
            filename = filename[:-4]

        response = Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}_report.pdf"',
                'Content-Type': 'application/pdf'
            }
        )

        return response

    except Exception as e:
        app.logger.error(f"Error generating PDF: {e}")
        return jsonify({"error": f"Error generating PDF: {str(e)}"}), 500


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "patterns_loaded": len(parser.patterns)
    })


# -----------------------------
# ERROR HANDLERS
# -----------------------------
@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large for server to process."}), 413


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":

    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    port = int(os.environ.get('PORT', 5001))

    print("=" * 60)
    print("🚀 Revit Journal Analyzer - Server Starting")
    print("=" * 60)
    print(f"📊 Patterns loaded: {len(parser.patterns)}")

    if connection_string:
        print("☁️ Azure Blob Storage ENABLED")
    else:
        print("⚠️ Azure Blob Storage DISABLED")

    print("=" * 60)

    app.run(debug=debug_mode, host='0.0.0.0', port=port)