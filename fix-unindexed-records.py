import boto3
import json

def fix_unindexed_records():
    """
    Fix existing unindexed records by re-indexing them
    """
    try:
        rekognition = boto3.client('rekognition', region_name='us-east-1')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        s3_client = boto3.client('s3', region_name='us-east-1')
        
        collection_id = 'face-collection'
        bucket_name = 'facial-recognition-data-bucket'
        
        print("🔧 Fixing Unindexed Records...")
        print("=" * 50)
        
        # Get all unindexed records
        table = dynamodb.Table('face-metadata')
        response = table.scan()
        items = response.get('Items', [])
        
        unindexed_items = [item for item in items if item.get('rekognitionFaceId') == 'N/A' or item.get('status') != 'indexed']
        
        print(f"Found {len(unindexed_items)} unindexed records")
        
        for i, item in enumerate(unindexed_items, 1):
            face_id = item['faceId']
            name = f"{item.get('firstName', 'N/A')} {item.get('lastName', 'N/A')}"
            s3_key = f"faces/{face_id}.jpg"
            
            print(f"\n{i}. Fixing: {name}")
            print(f"   Face ID: {face_id}")
            print(f"   S3 Key: {s3_key}")
            
            try:
                # Check if S3 object exists
                try:
                    s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                    print("   ✅ S3 object exists")
                except:
                    print("   ❌ S3 object not found - skipping")
                    continue
                
                # Try to index the face
                try:
                    index_response = rekognition.index_faces(
                        CollectionId=collection_id,
                        Image={'S3Object': {'Bucket': bucket_name, 'Name': s3_key}},
                        ExternalImageId=face_id,
                        MaxFaces=1,
                        QualityFilter='AUTO',
                        DetectionAttributes=['ALL']
                    )
                    
                    if index_response['FaceRecords']:
                        rekognition_face_id = index_response['FaceRecords'][0]['Face']['FaceId']
                        print(f"   ✅ Face indexed: {rekognition_face_id}")
                        
                        # Update DynamoDB record
                        table.update_item(
                            Key={'faceId': face_id},
                            UpdateExpression='SET rekognitionFaceId = :rek_id, #status = :status, s3Key = :s3_key',
                            ExpressionAttributeNames={'#status': 'status'},
                            ExpressionAttributeValues={
                                ':rek_id': rekognition_face_id,
                                ':status': 'indexed',
                                ':s3_key': s3_key
                            }
                        )
                        print(f"   ✅ DynamoDB record updated")
                    else:
                        print(f"   ❌ No face detected in image")
                        
                except Exception as e:
                    print(f"   ❌ Indexing failed: {str(e)}")
                    
            except Exception as e:
                print(f"   ❌ Error processing record: {str(e)}")
        
        print("\n" + "=" * 50)
        print("✅ Fix complete!")
        print("💡 Run the test again to verify all records are indexed")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    fix_unindexed_records()
