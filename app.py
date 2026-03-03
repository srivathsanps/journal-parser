"""
Revit Journal Analyzer - Flask Web Application
Analyzes Revit journal files for crash diagnosis, errors, and performance issues.
"""
# testing branch protection
# testing branch protection
# testing branch protection
# testing branch protection
import os
from pathlib import Path
from flask import Flask, request, jsonify, render_template, Response

from parser import JournalParser, parse_journal
from pdf_generator import generate_pdf

app = Flask(__name__)
# No file size limit - journal files can be large

# Disable caching during development to ensure JavaScript updates are loaded
@app.after_request
def add_header(response):
    """Add headers to prevent caching during development."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Initialize parser with XML patterns
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

    # Check file extension
    allowed_extensions = {'.txt', '.log', '.journal'}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_extensions:
        return jsonify({
            "error": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        }), 400

    try:
        # Read and decode file content
        content = file.read().decode("utf-8", errors="ignore")

        if not content.strip():
            return jsonify({"error": "File is empty"}), 400

        # Parse the journal file
        result = parser.parse(content)

        # Add filename to result
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

        # Generate PDF
        pdf_bytes = generate_pdf(data)

        # Create response with PDF
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
    """Handle file too large error (if server has limits)."""
    return jsonify({"error": "File too large for server to process."}), 413


@app.errorhandler(500)
def server_error(e):
    """Handle server errors."""
    return jsonify({"error": "Internal server error"}), 500


# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":
    # Enable debug mode for development
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    port = int(os.environ.get('PORT', 5001))

    print("=" * 60)
    print("🚀 Revit Journal Analyzer - Server Starting")
    print("=" * 60)
    print(f"📊 Patterns loaded: {len(parser.patterns)}")
    print(f"\n🌐 Access the application at:")
    print(f"   • Local:   http://localhost:{port}")
    print(f"   • Network: http://10.10.40.201:{port}")
    print(f"\n⚠️  Make sure Windows Firewall allows port {port}")
    print("=" * 60)

    app.run(debug=debug_mode, host='0.0.0.0', port=port)
    # This is our new line