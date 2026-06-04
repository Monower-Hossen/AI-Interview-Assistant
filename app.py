from flask import Flask, render_template, request, jsonify, send_from_directory, session
from flask_cors import CORS
import os
from ai_interview_assistant import logger
from ai_interview_assistant.utils.common import clean_directory, extract_text_from_pdf
from pathlib import Path
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24) # Required for Flask sessions
CORS(app)

@app.before_request
def ensure_user_session():
    """Ensures that a unique session ID exists for every request."""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

def get_pipeline():
    """Lazy initialization of the InterviewerPipeline to handle startup errors gracefully."""
    if not hasattr(app, 'pipeline'):
        try:
            from ai_interview_assistant.pipeline.interviewer_pipeline import InterviewerPipeline
            app.pipeline = InterviewerPipeline()
        except Exception as e:
            logger.error(f"Failed to initialize InterviewerPipeline: {e}")
            raise e
    return app.pipeline

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    """Initializes the interview and returns the first question."""
    try:
        data = request.get_json(silent=True) or {}
        job_role = data.get('job_role', 'Software Engineer')
        language = data.get('language', 'bn')
        resume_text = session.get('resume_text', '')
        
        result = get_pipeline().start_interview(session['user_id'], job_role, resume_text, language=language)
        return jsonify({
            "ai_response": result["ai_response"],
            "audio_url": f"/audio/{os.path.basename(result['audio_path'])}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/interview", methods=["POST"])
def interview():
    """
    Endpoint to receive audio from the frontend, process it through the pipeline,
    and return the transcribed text, AI response, and audio file path.
    """
    try:
        pipeline_instance = get_pipeline()
        input_path = None
        candidate_text = None

        # Check if audio is provided
        if 'audio' in request.files:
            audio_file = request.files['audio']
            unique_id = str(uuid.uuid4())[:8]
            input_path = Path(pipeline_instance.audio_store) / f"input_{unique_id}.wav"
            input_path.parent.mkdir(parents=True, exist_ok=True)
            audio_file.save(str(input_path))
        
        # Check for text input (either from form or JSON)
        if request.is_json:
            data = request.get_json()
            candidate_text = data.get('text')
            job_role = data.get('job_role', 'Software Engineer')
            language = data.get('language', 'bn')
        else:
            candidate_text = request.form.get('text')
            job_role = request.form.get('job_role', 'Software Engineer')
            language = request.form.get('language', 'bn')

        if not input_path and not candidate_text:
            return jsonify({"error": "No input provided"}), 400
            
        resume_text = session.get('resume_text', '')
        
        # Run pipeline with either audio path or direct text
        result = pipeline_instance.run_interview_step(input_path, candidate_text=candidate_text, session_id=session['user_id'], job_role=job_role, resume_text=resume_text, language=language)
        
        metrics = result.get("metrics", {})
        logger.info(f"Interview Metrics: Emotion={metrics.get('detected_emotion')}, Proctoring={metrics.get('proctoring')}")

        return jsonify({
            "candidate_text": result["candidate_text"],
            "ai_response": result["ai_response"],
            "audio_url": f"/audio/{os.path.basename(result['audio_path'])}",
            "metrics": metrics
        })
        
    except Exception as e:
        logger.error(f"Error in /interview endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/upload_resume", methods=["POST"])
def upload_resume():
    """Endpoint to upload and parse a candidate's resume."""
    try:
        if 'resume' not in request.files:
            return jsonify({"error": "No resume file provided"}), 400
        
        resume_file = request.files['resume']
        unique_id = str(uuid.uuid4())[:8]
        pipeline_instance = get_pipeline()
        root_dir = Path(pipeline_instance.artifacts_config.root_dir)
        root_dir.mkdir(parents=True, exist_ok=True)
        resume_path = root_dir / f"resume_{unique_id}.pdf"
        
        resume_file.save(str(resume_path))
        text = extract_text_from_pdf(resume_path)
        session['resume_text'] = text
        
        logger.info("Resume uploaded and parsed successfully.")
        return jsonify({"message": "Resume uploaded successfully!"})
    except Exception as e:
        logger.error(f"Error in /upload_resume: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/reset", methods=["POST"])
def reset():
    """Clears the session memory and triggers a cleanup of old audio files."""
    try:
        user_id = session.get('user_id')
        if user_id:
            pipeline_instance = get_pipeline()
            pipeline_instance.llm.clear_session_memory(user_id)
        
            # Clean up files older than 1 hour
            clean_directory(Path(pipeline_instance.audio_store), older_than_seconds=3600)
        
        return jsonify({"message": "Interview reset and old files cleaned."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/feedback", methods=["GET"])
def feedback():
    """Generates an evaluation report of the interview."""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "No active session found"}), 400
        
        report = get_pipeline().llm.generate_feedback(user_id)
        return jsonify({"report": report})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/audio/<filename>")
def get_audio(filename):
    return send_from_directory(str(get_pipeline().audio_store), filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)