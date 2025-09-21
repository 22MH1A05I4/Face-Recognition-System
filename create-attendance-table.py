import boto3
import json

def create_attendance_table():
    """
    Create DynamoDB table for attendance records
    """
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    table_name = 'attendance-records'
    
    try:
        # Check if table already exists
        existing_tables = dynamodb.meta.client.list_tables()['TableNames']
        if table_name in existing_tables:
            print(f"Table {table_name} already exists.")
            return
        
        # Create table
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'attendanceId',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'attendanceId',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'faceId',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'date',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'faceId-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'faceId',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    'IndexName': 'date-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'date',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        print(f"Creating table {table_name}...")
        
        # Wait for table to be created
        table.wait_until_exists()
        print(f"Table {table_name} created successfully!")
        
        # Print table details
        print(f"Table ARN: {table.table_arn}")
        print(f"Table status: {table.table_status}")
        
    except Exception as e:
        print(f"Error creating table: {str(e)}")

if __name__ == "__main__":
    create_attendance_table()
