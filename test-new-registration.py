import boto3
import json

def test_new_registration():
    """
    Test if new registrations are working properly
    """
    try:
        rekognition = boto3.client('rekognition', region_name='us-east-1')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        collection_id = 'face-collection'
        
        print("🔍 Testing New Registration System...")
        print("=" * 50)
        
        # Check Rekognition collection
        try:
            response = rekognition.describe_collection(CollectionId=collection_id)
            print(f"✅ Collection face count: {response['FaceCount']}")
        except Exception as e:
            print(f"❌ Collection error: {str(e)}")
            return
        
        # List faces in collection
        print(f"\n📋 Faces in Rekognition Collection:")
        try:
            list_response = rekognition.list_faces(CollectionId=collection_id)
            faces = list_response.get('Faces', [])
            
            for i, face in enumerate(faces, 1):
                print(f"   {i}. Face ID: {face['FaceId']}")
                print(f"      External ID: {face.get('ExternalImageId', 'N/A')}")
                print(f"      Confidence: {face.get('Confidence', 'N/A')}")
        except Exception as e:
            print(f"❌ Error listing faces: {str(e)}")
        
        # Check DynamoDB records
        print(f"\n📋 DynamoDB Records:")
        try:
            table = dynamodb.Table('face-metadata')
            response = table.scan()
            items = response.get('Items', [])
            
            indexed_count = 0
            for item in items:
                face_id = item.get('faceId', 'N/A')
                name = f"{item.get('firstName', 'N/A')} {item.get('lastName', 'N/A')}"
                rekognition_id = item.get('rekognitionFaceId', 'N/A')
                status = item.get('status', 'N/A')
                
                print(f"   - {name}")
                print(f"     Face ID: {face_id}")
                print(f"     Rekognition ID: {rekognition_id}")
                print(f"     Status: {status}")
                
                if rekognition_id != 'N/A' and status == 'indexed':
                    indexed_count += 1
                    print(f"     ✅ Properly indexed")
                else:
                    print(f"     ❌ NOT indexed")
            
            print(f"\n📊 Summary: {indexed_count}/{len(items)} faces properly indexed")
            
        except Exception as e:
            print(f"❌ DynamoDB error: {str(e)}")
        
        print("\n" + "=" * 50)
        if indexed_count > 0:
            print("✅ Registration system is working!")
        else:
            print("❌ Registration system needs fixing")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_new_registration()
