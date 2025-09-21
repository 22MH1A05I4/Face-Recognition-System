# AWS Facial Recognition System - Complete Deployment Guide

## 🎯 **System Architecture**
```
User → API Gateway → Lambda Functions → AWS Services
                    ├── Register → S3 + DynamoDB
                    ├── Create Index → Rekognition + DynamoDB  
                    └── Verify → Rekognition + DynamoDB
```

## 📋 **Prerequisites**
1. AWS CLI installed and configured
2. AWS Academy account with proper permissions
3. Python 3.9+ for Lambda functions

## 🚀 **Step-by-Step Deployment**

### **Step 1: Create S3 Bucket**
```bash
aws s3 mb s3://facial-recognition-data-bucket --region us-east-1
```

### **Step 2: Create DynamoDB Table**
```bash
    aws dynamodb create-table --table-name face-metadata --attribute-definitions AttributeName=faceId,AttributeType=S --key-schema AttributeName=faceId,KeyType=HASH --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 --region us-east-1
```

### **Step 3: Create Rekognition Collection**
```bash
    aws rekognition create-collection --collection-id face-collection --region us-east-1
```


4️⃣ IAM Role for Lambda

Go to IAM → Roles → Create role.

Select Lambda as the trusted entity → click Next.

Attach policy AWSLambdaBasicExecutionRole → click Next.

Name the role: FacialRecognitionLambdaRole.

Click Create role.

Add Custom Permissions

Click on the role → Add inline policy → JSON tab.

Paste this policy (update your bucket name and DynamoDB table):

{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject"],
            "Resource": ["arn:aws:s3:::facial-recognition-data-bucket/*"]
        },
        {
            "Effect": "Allow",
            "Action": ["s3:ListBucket"],
            "Resource": ["arn:aws:s3:::facial-recognition-data-bucket"]
        },
        {
            "Effect": "Allow",
            "Action": [
                "rekognition:IndexFaces",
                "rekognition:SearchFaces",
                "rekognition:DetectFaces",
                "rekognition:CreateCollection",
                "rekognition:ListCollections"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": "arn:aws:dynamodb:us-east-1:*:table/face-metadata"
        }
    ]
}


Click Review policy → Create policy.

5️⃣ Lambda Functions (Register / Create Index / Verify)

Go to AWS Lambda → Create function → Author from scratch.

Function name: e.g., facial-recognition-register.

Runtime: Python 3.9.

Role: Use existing role → FacialRecognitionLambdaRole.

Click Create function.

Repeat for facial-recognition-create-index and facial-recognition-verify.

Upload Code

Go to Code tab → Upload from .zip or edit inline.

Set handler: register.lambda_handler (or the corresponding script).

Save changes.

6️⃣ API Gateway (Create REST API)

Go to API Gateway → Create API → REST API → Build.

API Name: facial-recognition-api.

Create resources:

/register → Add POST method → Lambda integration → select facial-recognition-register.

/create-index → POST → Lambda → facial-recognition-create-index.

/verify → POST → Lambda → facial-recognition-verify.

Deploy API → Create stage: prod.

✅ You now have endpoints like:

https://<API_ID>.execute-api.us-east-1.amazonaws.com/prod/register

7️⃣ Lambda Permissions for API Gateway

Go to each Lambda → Configuration → Permissions → Add permission.

Allow API Gateway to invoke this Lambda.

Example for /register Lambda
Field	Value
Statement ID	apigateway-register
Principal	apigateway.amazonaws.com
Source ARN	arn:aws:execute-api:us-east-1:883111487967:API_ID/*/POST/register
Action	lambda:InvokeFunction

Field	Value
Statement ID	apigateway-create-index
Principal	apigateway.amazonaws.com
Source ARN	arn:aws:execute-api:us-east-1:883111487967:ob9dfh1e03/prod/POST/create-index
Action	lambda:InvokeFunction

Field	Value
Statement ID	apigateway-verify
Principal	apigateway.amazonaws.com
Source ARN	arn:aws:execute-api:us-east-1:883111487967:ob9dfh1e03/prod/POST/verify
Action	lambda:InvokeFunction

need to keep api_gateway url in register.js and verify.js