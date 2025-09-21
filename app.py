from flask import Flask, request, jsonify
import boto3
import base64
import uuid
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # allow frontend requests

# AWS setup
s3 = boto3.client("s3", region_name="us-east-1")  # S3 client
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("face-metadata")  # DynamoDB table
bucket_name = "facial-recognition-data-bucket"  # S3 bucket

# ✅ Homepage route
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Server running ✅"})

# ✅ Register route
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()

        first_name = data.get("firstName")
        last_name = data.get("lastName")
        dob = data.get("dateOfBirth")
        phone = data.get("phoneNumber")
        image_data = data.get("image")  # base64 string

        if not all([first_name, last_name, dob, phone, image_data]):
            return jsonify({"error": "Missing fields"}), 400

        # Generate unique faceId
        face_id = str(uuid.uuid4())

        # Decode base64 image
        if "," in image_data:
            image_data = image_data.split(",")[1]
        image_bytes = base64.b64decode(image_data)
        image_key = f"faces/{face_id}.jpg"

        # Upload to S3
        s3.put_object(
            Bucket=bucket_name,
            Key=image_key,
            Body=image_bytes,
            ContentType="image/jpeg"
        )

        # Insert into DynamoDB
        table.put_item(
            Item={
                "faceId": face_id,
                "firstName": first_name,
                "lastName": last_name,
                "dateOfBirth": dob,
                "phoneNumber": phone,
                "imageKey": image_key
            }
        )

        return jsonify({"message": "Registration successful ✅", "faceId": face_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ✅ Optional: Fetch face metadata by faceId
@app.route("/get_face/<face_id>", methods=["GET"])
def get_face(face_id):
    try:
        response = table.get_item(Key={"faceId": face_id})
        item = response.get("Item")
        if not item:
            return jsonify({"error": "Face not found"}), 404
        return jsonify(item)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Attendance endpoints
@app.route("/attendance", methods=["POST"])
def mark_attendance():
    try:
        data = request.get_json()
        
        face_id = data.get("faceId")
        person_data = data.get("person", {})
        attendance_type = data.get("type", "checkin")
        confidence = data.get("confidence", 0.0)
        
        if not face_id:
            return jsonify({"error": "Face ID is required"}), 400
        
        # Create attendance record
        attendance_id = f"att_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{face_id}"
        timestamp = datetime.utcnow().isoformat()
        date = timestamp.split('T')[0]
        time = timestamp.split('T')[1].split('.')[0]
        
        attendance_record = {
            "attendanceId": attendance_id,
            "faceId": face_id,
            "firstName": person_data.get("firstName", "Unknown"),
            "lastName": person_data.get("lastName", "Unknown"),
            "dateOfBirth": person_data.get("dateOfBirth", ""),
            "phoneNumber": person_data.get("phoneNumber", ""),
            "type": attendance_type,
            "confidence": confidence,
            "timestamp": timestamp,
            "date": date,
            "time": time,
            "createdAt": timestamp
        }
        
        # Save to DynamoDB (using a separate attendance table)
        attendance_table = dynamodb.Table("attendance-records")
        attendance_table.put_item(Item=attendance_record)
        
        return jsonify({
            "success": True,
            "attendanceId": attendance_id,
            "record": attendance_record,
            "message": f"Attendance {attendance_type} recorded successfully"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/attendance/records", methods=["GET"])
def get_attendance_records():
    try:
        date_filter = request.args.get("date")
        status_filter = request.args.get("status", "all")
        limit = int(request.args.get("limit", 100))
        
        attendance_table = dynamodb.Table("attendance-records")
        
        # Build scan parameters
        scan_params = {"Limit": limit}
        
        # Add filters
        filter_expressions = []
        expression_values = {}
        
        if date_filter:
            filter_expressions.append("date = :date")
            expression_values[":date"] = date_filter
        
        if status_filter != "all":
            filter_expressions.append("#type = :type")
            expression_values[":type"] = status_filter
            expression_values["#type"] = "type"  # 'type' is a reserved word
        
        if filter_expressions:
            scan_params["FilterExpression"] = " AND ".join(filter_expressions)
            scan_params["ExpressionAttributeValues"] = expression_values
        
        # Scan table
        response = attendance_table.scan(**scan_params)
        records = response.get("Items", [])
        
        # Sort by timestamp (newest first)
        records.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return jsonify({
            "success": True,
            "records": records,
            "count": len(records)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/attendance/stats", methods=["GET"])
def get_attendance_stats():
    try:
        date_filter = request.args.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
        
        attendance_table = dynamodb.Table("attendance-records")
        
        # Get records for the specified date
        response = attendance_table.scan(
            FilterExpression="date = :date",
            ExpressionAttributeValues={":date": date_filter}
        )
        
        records = response.get("Items", [])
        
        # Calculate statistics
        total_records = len(records)
        checkin_count = len([r for r in records if r["type"] == "checkin"])
        checkout_count = len([r for r in records if r["type"] == "checkout"])
        
        # Count unique people who checked in today
        unique_people = len(set(r["faceId"] for r in records if r["type"] == "checkin"))
        
        # Count currently checked in (people whose last record is check-in)
        last_records_by_person = {}
        for record in records:
            face_id = record["faceId"]
            if face_id not in last_records_by_person or record["timestamp"] > last_records_by_person[face_id]["timestamp"]:
                last_records_by_person[face_id] = record
        
        currently_checked_in = len([r for r in last_records_by_person.values() if r["type"] == "checkin"])
        
        stats = {
            "date": date_filter,
            "totalRecords": total_records,
            "checkinCount": checkin_count,
            "checkoutCount": checkout_count,
            "uniquePeople": unique_people,
            "currentlyCheckedIn": currently_checked_in
        }
        
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
