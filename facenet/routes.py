import os
import io
import json
import base64
import bcrypt
from flask import request, jsonify
from PIL import Image
from datetime import datetime, date, timedelta
import numpy as np
from database import Student

ADMIN_PATH = "data/admin.json"

# Ensure admin exist
if not os.path.exists(ADMIN_PATH):
    with open(ADMIN_PATH, "w") as f:
        hashed_pw = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        json.dump({"password": hashed_pw}, f)

def get_admin_password():
    with open(ADMIN_PATH, "r") as f:
        return json.load(f)["password"]

def set_admin_password(new_password):
    hashed_pw = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    with open(ADMIN_PATH, "w") as f:
        json.dump({"password": hashed_pw}, f)

def register_routes(app, db, Attendance, detector, embedder):

    def update_face(student, new_embedding):
        """Update existing student's face embedding in DB."""
        try:
            student.embedding = new_embedding
            db.session.commit()
            return True, f"Updated facial data for {student.name}"
        except Exception as e:
            db.session.rollback()
            return False, str(e)
        
    @app.route("/enroll", methods=["POST"])
    def enroll():
        try:
            data = request.json
            name = data["name"]
            mobile = data.get("mobile")
            email = data.get("email")
            image_data = data["image"].split(",")[1]
            image = Image.open(io.BytesIO(base64.b64decode(image_data)))

            faces = detector.detect_faces(np.array(image))

            if not faces:
                return jsonify({"error": "No face detected"}), 400

            if len(faces) > 1:
                return jsonify({
                    "error": "Multiple faces detected. Please provide an image with a single face."
                }), 400

            # Single face
            x, y, w, h = faces[0]["box"]
            face_crop = image.crop((x, y, x + w, y + h))
            embedding = embedder.embeddings([np.array(face_crop)])[0].tolist()

            # Check if student exists
            student = Student.query.filter_by(name=name).first()
            if student:
                # Instead of auto-update, prompt admin
                return jsonify({
                    "message": f"Student '{name}' already exists. Do you want to update facial data?",
                    "student_exists": True
                })

            # Create new student
            new_student = Student(
                name=name,
                mobile=mobile,
                email=email,
                embedding=embedding
            )
            db.session.add(new_student)
            db.session.commit()

            return jsonify({
                "message": f"User '{name}' enrolled successfully.",
                "faces_detected": 1,
                "updated": False
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        
    @app.route("/update-face", methods=["POST"])
    def update_face_route():
        try:
            data = request.json
            name = data["name"]
            image_data = data["image"].split(",")[1]
            image = Image.open(io.BytesIO(base64.b64decode(image_data)))

            faces = detector.detect_faces(np.array(image))
            if not faces:
                return jsonify({"error": "No face detected"}), 400

            if len(faces) > 1:
                return jsonify({
                    "error": "Multiple faces detected. Please provide an image with a single face."
                }), 400

            student = Student.query.filter_by(name=name).first()
            if not student:
                return jsonify({"error": f"Student '{name}' not found."}), 404

            # Single face crop
            x, y, w, h = faces[0]["box"]
            face_crop = image.crop((x, y, x + w, y + h))
            new_embedding = embedder.embeddings([np.array(face_crop)])[0].tolist()

            # Update embedding
            student.embedding = new_embedding
            db.session.commit()

            return jsonify({
                "message": f"Facial data for student '{name}' updated successfully.",
                "updated": True
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500


    @app.route("/recognize", methods=["POST"])
    def recognize():
        try:
            data = request.json
            image_data = data["image"].split(",")[1]
            image = Image.open(io.BytesIO(base64.b64decode(image_data)))

            faces = detector.detect_faces(np.array(image))
            if not faces:
                return jsonify({"error": "No face detected"}), 400
            
            students = Student.query.all()
            student_embeddings = {
                student.name: np.array(student.embedding) for student in students
            }
            results = []

            today = date.today().strftime("%Y-%m-%d")
            current_time = datetime.now().strftime("%H:%M:%S")

            THRESHOLD = 0.1

            for face in faces:
                x, y, w, h = face["box"]
                face_crop = image.crop((x, y, x + w, y + h))
                emb = embedder.embeddings([np.array(face_crop)])[0]

                match_name = "Unknown"
                min_dist = 1.0

                for name, stored_emb in student_embeddings.items():
                    dist = np.linalg.norm(emb - stored_emb)
                    if dist < min_dist:
                        min_dist = dist
                        match_name = name

                if min_dist > THRESHOLD:
                    match_name = "Unknown"
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {match_name}: distance={min_dist:.3f}")

                if match_name != "Unknown":
                    try:
                        existing_record = Attendance.query.filter_by(student=match_name, date=today).first()
                        if existing_record:
                            existing_record.outtime = current_time
                        else:
                            new_entry = Attendance(
                                student=match_name,
                                date=today,
                                intime=current_time,
                                outtime=current_time
                            )
                            db.session.add(new_entry)
                        db.session.commit()
                    except Exception as db_err:
                        db.session.rollback()
                        print("DB error:", db_err)

                results.append({
                    "name": match_name,
                    "bbox": [x, y, w, h],
                    "time": current_time
                })

            return jsonify({"faces": results})

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route("/api/verify", methods=["POST"])
    def verify_password():
        data = request.json
        input_pw = data.get("password", "")
        stored_hashed_pw = get_admin_password().encode("utf-8")
        if bcrypt.checkpw(input_pw.encode("utf-8"), stored_hashed_pw):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False}), 401

    @app.route("/api/update-password", methods=["POST"])
    def update_password():
        data = request.json
        old_pw = data.get("old_password", "")
        new_pw = data.get("new_password", "")
        stored_hashed_pw = get_admin_password().encode("utf-8")
        if bcrypt.checkpw(old_pw.encode("utf-8"), stored_hashed_pw):
            set_admin_password(new_pw)
            return jsonify({"message": "Password updated successfully!"})
        else:
            return jsonify({"error": "Old password is incorrect"}), 401
    
    @app.route("/api/students-today", methods=["GET"])
    def students_today():
        today_str = date.today().isoformat()  # "YYYY-MM-DD"
        try:
            count = Attendance.query.filter_by(date=today_str).count()
            return jsonify({"count": count})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
    @app.route("/api/total-students", methods=["GET"])
    def total_students():
        try:
            count = Student.query.count()
            return jsonify({"count": count})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/weekly-attendance", methods=["GET"])
    def weekly_attendance():
        """
        Returns attendance count for the selected week.
        Query param: offset (integer)
        - offset=0 → current week
        - offset=-1 → last week
        - offset=1 → next week
        Response:
        {
          "dates": ["2025-10-06", "2025-10-07", ...],
          "counts": [5, 8, 7, 3, 9, 2, 0]
        }
        """
        try:
            offset = int(request.args.get("offset", 0))

            today = date.today()
            start_of_week = today - timedelta(days=today.weekday())  # Monday of current week
            target_start = start_of_week + timedelta(weeks=offset)
            target_end = target_start + timedelta(days=6)

            # Prepare a mapping for 7 days in the target week
            daily_counts = {
                (target_start + timedelta(days=i)): 0 for i in range(7)
            }

            # Fetch attendance records for this week
            records = (
                Attendance.query
                .filter(Attendance.date >= target_start.strftime("%Y-%m-%d"))
                .filter(Attendance.date <= target_end.strftime("%Y-%m-%d"))
                .all()
            )

            # Count attendance per day
            for record in records:
                record_date = datetime.strptime(record.date, "%Y-%m-%d").date()
                if record_date in daily_counts:
                    daily_counts[record_date] += 1

            # Build response
            response = {
                "dates": [d.strftime("%Y-%m-%d") for d in daily_counts.keys()],
                "counts": list(daily_counts.values())
            }

            return jsonify(response)

        except Exception as e:
            print("Error in /api/weekly-attendance:", e)
            return jsonify({"error": str(e)}), 500


        
    @app.route("/api/students-absent-today", methods=["GET"])
    def students_absent_today():
        try:
            today_str = date.today().strftime("%Y-%m-%d")

            # Get all students
            all_students = Student.query.all()
            all_names = set(student.name for student in all_students)

            # Get students who have attendance today
            present_records = Attendance.query.filter_by(date=today_str).all()
            present_names = set(record.student for record in present_records)

            # Absent students = all - present
            absent_names = all_names - present_names
            absent_count = len(absent_names)

            return jsonify({"count": absent_count, "absent_students": list(absent_names)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        

    @app.route("/api/attendance-all", methods=["GET"])
    def get_all_attendance():
        records = Attendance.query.all()
        data = [
        {
            "student": r.student,
            "date": r.date,
            "intime": r.intime,
            "outtime": r.outtime,
        }
        for r in records
    ]
    return jsonify({"records": data})

    


        