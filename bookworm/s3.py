import boto3
import botocore

def client():
    config = botocore.client.Config(connect_timeout=3, read_timeout=3, retries={'max_attempts': 0})
    session = boto3.session.Session()
    return session.client(
        service_name='s3',
        aws_access_key_id='LBSBQ46DB9S160XIW438',
        aws_secret_access_key='7nVT+TwGzPoC02AIIY4+1fVNdj07RQt+ntd55S+I',
        endpoint_url='http://localhost:9000',
        config=config
    )
