The Face Recognition System is an automated face-based identification and attendance management solution that leverages AWS cloud services. The system enables new users to register by capturing their facial image, which is securely stored in Amazon S3, indexed in an AWS Rekognition collection, and linked with user details stored in Amazon DynamoDB.
During recognition, the system verifies a user’s identity by matching the captured image with the stored collection, instantly displaying their details. The system also integrates an attendance feature: when a registered face is detected for the first time, it is marked as Check-In, and on the second detection, it is marked as Check-Out.
By combining cloud-based image recognition with real-time data storage and retrieval, this project provides a reliable, scalable, and efficient solution for automated identity verification and attendance tracking.

Services Used:
1.AWS S3
2.AWS DYNAMODB
3.AWS REKOGNITION
4.LAMBDA
5.API GATEWAY
6.IAM ROLE
7.AWS AMPLIFY(for deploying)

Project Demo:https://drive.google.com/file/d/1v1wlZ8JmEVLnNXnbAQ9jIqY6Tt0FWQNw/view?usp=sharing




