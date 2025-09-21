import boto3
import json

def remove_faces():
    """
    Remove faces from both Rekognition collection and DynamoDB
    """
    try:
        rekognition = boto3.client('rekognition', region_name='us-east-1')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        s3_client = boto3.client('s3', region_name='us-east-1')
        
        collection_id = 'face-collection'
        bucket_name = 'facial-recognition-data-bucket'
        
        print("🗑️ Face Removal Tool")
        print("=" * 50)
        
        # Get all faces from Rekognition
        print("1. Getting faces from Rekognition collection...")
        try:
            list_response = rekognition.list_faces(CollectionId=collection_id)
            rekognition_faces = list_response.get('Faces', [])
            print(f"   Found {len(rekognition_faces)} faces in Rekognition")
            
            for i, face in enumerate(rekognition_faces, 1):
                print(f"   {i}. Face ID: {face['FaceId']}")
                print(f"      External ID: {face.get('ExternalImageId', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return
        
        # Get all records from DynamoDB
        print("\n2. Getting records from DynamoDB...")
        try:
            table = dynamodb.Table('face-metadata')
            response = table.scan()
            db_records = response.get('Items', [])
            print(f"   Found {len(db_records)} records in DynamoDB")
            
            for i, record in enumerate(db_records, 1):
                name = f"{record.get('firstName', 'N/A')} {record.get('lastName', 'N/A')}"
                face_id = record.get('faceId', 'N/A')
                rekognition_id = record.get('rekognitionFaceId', 'N/A')
                print(f"   {i}. {name}")
                print(f"      Face ID: {face_id}")
                print(f"      Rekognition ID: {rekognition_id}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return
        
        # Show removal options
        print("\n3. Removal Options:")
        print("   a) Remove ALL faces (nuclear option)")
        print("   b) Remove specific face by name")
        print("   c) Remove specific face by Face ID")
        print("   d) Remove unindexed faces only")
        print("   e) Exit")
        
        choice = input("\nEnter your choice (a/b/c/d/e): ").lower().strip()
        
        if choice == 'a':
            remove_all_faces(rekognition, dynamodb, s3_client, collection_id, bucket_name)
        elif choice == 'b':
            remove_by_name(dynamodb, rekognition, s3_client, collection_id, bucket_name, db_records)
        elif choice == 'c':
            remove_by_face_id(dynamodb, rekognition, s3_client, collection_id, bucket_name, db_records)
        elif choice == 'd':
            remove_unindexed_faces(dynamodb, s3_client, bucket_name, db_records)
        elif choice == 'e':
            print("Exiting...")
            return
        else:
            print("Invalid choice. Exiting...")
            return
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def remove_all_faces(rekognition, dynamodb, s3_client, collection_id, bucket_name):
    """Remove all faces"""
    print("\n🗑️ Removing ALL faces...")
    
    confirm = input("⚠️  WARNING: This will delete ALL faces. Type 'DELETE ALL' to confirm: ")
    if confirm != 'DELETE ALL':
        print("❌ Operation cancelled")
        return
    
    try:
        # Delete collection (removes all faces)
        rekognition.delete_collection(CollectionId=collection_id)
        print("✅ Rekognition collection deleted")
        
        # Recreate empty collection
        rekognition.create_collection(CollectionId=collection_id)
        print("✅ New empty collection created")
        
        # Delete all DynamoDB records
        table = dynamodb.Table('face-metadata')
        response = table.scan()
        items = response.get('Items', [])
        
        for item in items:
            face_id = item['faceId']
            s3_key = item.get('s3Key', f'faces/{face_id}.jpg')
            
            # Delete from DynamoDB
            table.delete_item(Key={'faceId': face_id})
            print(f"✅ Deleted DynamoDB record: {face_id}")
            
            # Delete from S3
            try:
                s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
                print(f"✅ Deleted S3 object: {s3_key}")
            except:
                print(f"⚠️  S3 object not found: {s3_key}")
        
        print("\n🎉 ALL faces removed successfully!")
        
    except Exception as e:
        print(f"❌ Error removing all faces: {str(e)}")

def remove_by_name(dynamodb, rekognition, s3_client, collection_id, bucket_name, db_records):
    """Remove face by name"""
    print("\n🔍 Available faces:")
    for i, record in enumerate(db_records, 1):
        name = f"{record.get('firstName', 'N/A')} {record.get('lastName', 'N/A')}"
        print(f"   {i}. {name}")
    
    try:
        choice = int(input("\nEnter the number of the face to remove: ")) - 1
        if 0 <= choice < len(db_records):
            record = db_records[choice]
            remove_single_face(dynamodb, rekognition, s3_client, collection_id, bucket_name, record)
        else:
            print("❌ Invalid choice")
    except ValueError:
        print("❌ Invalid input")

def remove_by_face_id(dynamodb, rekognition, s3_client, collection_id, bucket_name, db_records):
    """Remove face by Face ID"""
    face_id = input("\nEnter the Face ID to remove: ").strip()
    
    # Find the record
    record = None
    for r in db_records:
        if r.get('faceId') == face_id:
            record = r
            break
    
    if record:
        remove_single_face(dynamodb, rekognition, s3_client, collection_id, bucket_name, record)
    else:
        print(f"❌ Face ID {face_id} not found")

def remove_unindexed_faces(dynamodb, s3_client, bucket_name, db_records):
    """Remove unindexed faces only"""
    print("\n🗑️ Removing unindexed faces...")
    
    unindexed = [r for r in db_records if r.get('rekognitionFaceId') == 'N/A' or r.get('status') != 'indexed']
    
    if not unindexed:
        print("✅ No unindexed faces found")
        return
    
    print(f"Found {len(unindexed)} unindexed faces:")
    for i, record in enumerate(unindexed, 1):
        name = f"{record.get('firstName', 'N/A')} {record.get('lastName', 'N/A')}"
        print(f"   {i}. {name}")
    
    confirm = input(f"\nRemove {len(unindexed)} unindexed faces? (y/n): ").lower()
    if confirm == 'y':
        table = dynamodb.Table('face-metadata')
        for record in unindexed:
            face_id = record['faceId']
            s3_key = record.get('s3Key', f'faces/{face_id}.jpg')
            
            # Delete from DynamoDB
            table.delete_item(Key={'faceId': face_id})
            print(f"✅ Deleted: {face_id}")
            
            # Delete from S3
            try:
                s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
            except:
                pass
        
        print("✅ Unindexed faces removed!")

def remove_single_face(dynamodb, rekognition, s3_client, collection_id, bucket_name, record):
    """Remove a single face"""
    face_id = record['faceId']
    name = f"{record.get('firstName', 'N/A')} {record.get('lastName', 'N/A')}"
    rekognition_id = record.get('rekognitionFaceId')
    s3_key = record.get('s3Key', f'faces/{face_id}.jpg')
    
    print(f"\n🗑️ Removing: {name}")
    print(f"   Face ID: {face_id}")
    print(f"   Rekognition ID: {rekognition_id}")
    
    try:
        # Delete from Rekognition
        if rekognition_id and rekognition_id != 'N/A':
            rekognition.delete_faces(
                CollectionId=collection_id,
                FaceIds=[rekognition_id]
            )
            print(f"✅ Deleted from Rekognition: {rekognition_id}")
        
        # Delete from DynamoDB
        table = dynamodb.Table('face-metadata')
        table.delete_item(Key={'faceId': face_id})
        print(f"✅ Deleted from DynamoDB: {face_id}")
        
        # Delete from S3
        try:
            s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
            print(f"✅ Deleted from S3: {s3_key}")
        except:
            print(f"⚠️  S3 object not found: {s3_key}")
        
        print(f"🎉 Successfully removed: {name}")
        
    except Exception as e:
        print(f"❌ Error removing face: {str(e)}")

if __name__ == "__main__":
    remove_faces()
