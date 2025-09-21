import json
import boto3
import base64
import uuid
from datetime import datetime

def lambda_handler(event, context):
    """
    Fixed Lambda function to register faces with better error handling
    """
    try:
        # Parse request body
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(event['body']).decode('utf-8')
        else:
            body = event.get('body', '{}')
        
        data = json.loads(body)
        
        # Extract data
        first_name = data.get('firstName', '')
        last_name = data.get('lastName', '')
        date_of_birth = data.get('dateOfBirth', '')
        phone_number = data.get('phoneNumber', '')
        image_data = data.get('image', '')
        
        print(f"Registering face for: {first_name} {last_name}")
        
        # Generate unique face ID
        face_id = str(uuid.uuid4())
        
        # Initialize AWS services
        s3_client = boto3.client('s3', region_name='us-east-1')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        rekognition = boto3.client('rekognition', region_name='us-east-1')
        
        # Configuration
        bucket_name = 'facial-recognition-data-bucket'
        collection_id = 'face-collection'
        
        # Decode and upload image to S3
        print("Uploading image to S3...")
        image_bytes = base64.b64decode(image_data.split(',')[1])
        s3_key = f"faces/{face_id}.jpg"
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=image_bytes,
            ContentType='image/jpeg'
        )
        print(f"Image uploaded to S3: {s3_key}")
        
        # Ensure collection exists
        print(f"Ensuring collection '{collection_id}' exists...")
        try:
            rekognition.describe_collection(CollectionId=collection_id)
            print("Collection already exists")
        except rekognition.exceptions.ResourceNotFoundException:
            print("Creating collection...")
            rekognition.create_collection(CollectionId=collection_id)
            print("Collection created successfully")
        
        # Index face in Rekognition collection
        print("Indexing face in Rekognition...")
        rekognition_face_id = None
        indexing_success = False
        
        try:
            # First, try to detect faces in the image
            detect_response = rekognition.detect_faces(
                Image={'Bytes': image_bytes},
                Attributes=['ALL']
            )
            
            print(f"Face detection response: {json.dumps(detect_response, default=str)}")
            
            if not detect_response['FaceDetails']:
                print("No faces detected in the image")
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'success': False,
                        'error': 'No face detected in the uploaded image. Please ensure your face is clearly visible and well-lit.'
                    })
                }
            
            # If faces are detected, proceed with indexing
            index_response = rekognition.index_faces(
                CollectionId=collection_id,
                Image={'S3Object': {'Bucket': bucket_name, 'Name': s3_key}},
                ExternalImageId=face_id,
                MaxFaces=1,
                QualityFilter='AUTO',
                DetectionAttributes=['ALL']
            )
            
            print(f"Index response: {json.dumps(index_response, default=str)}")
            
            if index_response['FaceRecords']:
                rekognition_face_id = index_response['FaceRecords'][0]['Face']['FaceId']
                indexing_success = True
                print(f"Face indexed successfully. Rekognition Face ID: {rekognition_face_id}")
            else:
                print("No face records returned from indexing")
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'success': False,
                        'error': 'Failed to index face. Please try with a clearer image.'
                    })
                }
                
        except Exception as rekognition_error:
            print(f"Rekognition error: {str(rekognition_error)}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': f'Rekognition error: {str(rekognition_error)}'
                })
            }
        
        # Store metadata in DynamoDB
        print("Storing metadata in DynamoDB...")
        table = dynamodb.Table('face-metadata')
        
        # Determine status based on indexing success
        status = 'indexed' if indexing_success else 'failed_indexing'
        
        table.put_item(Item={
            'faceId': face_id,
            'rekognitionFaceId': rekognition_face_id or 'N/A',
            'userId': f"{first_name}_{last_name}_{phone_number}",
            'firstName': first_name,
            'lastName': last_name,
            'dateOfBirth': date_of_birth,
            'phoneNumber': phone_number,
            's3Key': s3_key,
            'createdAt': datetime.utcnow().isoformat(),
            'status': status
        })
        
        print(f"Metadata stored with status: {status}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'faceId': face_id,
                'rekognitionFaceId': rekognition_face_id,
                's3Key': s3_key,
                'bucketName': bucket_name,
                'status': status,
                'message': f'Face registered successfully. Status: {status}'
            })
        }
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': f'Registration failed: {str(e)}'
            })
        }
