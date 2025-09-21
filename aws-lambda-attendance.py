import json
import boto3
from datetime import datetime
from decimal import Decimal

# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
TABLE_NAME = "attendance-records"   # 👈 Change if your table name is different
table = dynamodb.Table(TABLE_NAME)

# ✅ Custom encoder for Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # Convert Decimal to float for JSON response
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    try:
        print("🔍 Incoming event:", json.dumps(event))

        # Parse body
        body = event.get("body", "{}")
        if isinstance(body, str):
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                print("❌ Failed to decode body JSON:", body)
                data = {}
        else:
            data = body

        action = data.get("action", "")
        print(f"👉 Action received: {action}")

        if action == "mark_attendance":
            return mark_attendance(data)
        elif action == "get_records":
            return get_attendance_records()
        elif action == "get_stats":
            return get_attendance_stats()
        else:
            return response_json(400, {"success": False, "error": "Invalid action specified"})

    except Exception as e:
        print("❌ Lambda error:", str(e))
        return response_json(500, {"success": False, "error": str(e)})

def mark_attendance(data):
    try:
        face_id = data.get("faceId")
        person_data = data.get("person", {})
        attendance_type = data.get("type", "checkin")

        confidence = data.get("confidence", None)
        confidence_value = Decimal(str(confidence)) if confidence is not None else None

        if not face_id:
            return response_json(400, {"success": False, "error": "Face ID is required"})

        timestamp = datetime.utcnow().isoformat()
        date = timestamp.split("T")[0]
        time = timestamp.split("T")[1].split(".")[0]
        attendance_id = f"att_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{face_id}"

        attendance_record = {
            "attendanceId": attendance_id,
            "faceId": face_id,
            "firstName": person_data.get("firstName", "Unknown"),
            "lastName": person_data.get("lastName", "Unknown"),
            "dateOfBirth": person_data.get("dateOfBirth", ""),
            "phoneNumber": person_data.get("phoneNumber", ""),
            "type": attendance_type,
            "confidence": confidence_value,
            "timestamp": timestamp,
            "date": date,
            "time": time,
            "createdAt": timestamp
        }

        print("📝 Inserting record:", attendance_record)
        table.put_item(Item=attendance_record)
        print("✅ Inserted successfully")

        return response_json(200, {
            "success": True,
            "attendanceId": attendance_id,
            "record": attendance_record,
            "message": f"Attendance {attendance_type} recorded successfully"
        })

    except Exception as e:
        print("❌ Error inserting attendance:", str(e))
        return response_json(500, {"success": False, "error": f"Failed to mark attendance: {str(e)}"})

def get_attendance_records():
    try:
        response = table.scan()
        records = response.get("Items", [])
        return response_json(200, {"success": True, "count": len(records), "records": records})
    except Exception as e:
        print("❌ Error getting records:", str(e))
        return response_json(500, {"success": False, "error": str(e)})

def get_attendance_stats():
    # Placeholder for stats (like daily checkins, etc.)
    return response_json(200, {"success": True, "message": "Stats placeholder"})

def response_json(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body_dict, cls=DecimalEncoder)
    }
