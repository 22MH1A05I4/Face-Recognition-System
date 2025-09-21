import json
import boto3
import base64
import os

rekognition = boto3.client("rekognition")
dynamodb = boto3.resource("dynamodb")
TABLE_NAME = "face-metadata"   # <-- your DynamoDB table

def lambda_handler(event, context):
    try:
        print("🔍 Incoming event:", json.dumps(event))

        # Parse body (API Gateway proxy integration sends JSON string)
        if "body" in event:
            body = event["body"]
            if isinstance(body, str):
                body = json.loads(body)
        else:
            body = event

        # Validate input
        if "image" not in body or not body["image"]:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": False,
                    "message": "No image provided"
                })
            }

        # Extract base64 image data (strip "data:image/jpeg;base64," if present)
        image_data = body["image"]
        if "," in image_data:
            image_data = image_data.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        # Search for face in Rekognition
        response = rekognition.search_faces_by_image(
            CollectionId="face-collection",
            Image={"Bytes": image_bytes},
            MaxFaces=1,
            FaceMatchThreshold=80
        )

        print("✅ Rekognition response:", response)

        if not response.get("FaceMatches"):
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": True,
                    "match": False,
                    "confidence": 0,
                    "message": "No matching face found"
                })
            }

        # Extract match details
        face_match = response["FaceMatches"][0]
        rekognition_face_id = face_match["Face"]["FaceId"]
        confidence = face_match["Similarity"]

        # Lookup DynamoDB using rekognitionFaceId (not faceId PK directly)
        table = dynamodb.Table(TABLE_NAME)
        db_response = table.scan(
            FilterExpression="rekognitionFaceId = :r",
            ExpressionAttributeValues={":r": rekognition_face_id}
        )

        print("✅ DynamoDB response:", db_response)

        if db_response.get("Items"):
            person = db_response["Items"][0]
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": True,
                    "match": True,
                    "confidence": confidence,
                    "faceId": person.get("faceId"),
                    "person": {
                        "firstName": person.get("firstName", "Unknown"),
                        "lastName": person.get("lastName", "Unknown"),
                        "dateOfBirth": person.get("dateOfBirth", "Unknown"),
                        "phoneNumber": person.get("phoneNumber", "Unknown")
                    }
                })
            }
        else:
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": True,
                    "match": False,
                    "confidence": confidence,
                    "message": "Face found but no person data in DynamoDB"
                })
            }

    except Exception as e:
        print("❌ Error:", str(e))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "success": False,
                "message": f"System error: {str(e)}"
            })
        }
