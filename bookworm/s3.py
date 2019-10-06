import boto3
import botocore

def client():
    config = botocore.client.Config(connect_timeout=3, read_timeout=3, retries={'max_attempts': 0})
    session = boto3.session.Session(profile_name='bookworm')
    return session.client(service_name='s3', endpoint_url='http://localhost:9000', config=config)
