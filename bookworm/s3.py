import boto3
import botocore

def client():
    config = botocore.client.Config(connect_timeout=3, read_timeout=3, retries={'max_attempts': 0})
    session = boto3.session.Session()
    return session.client(
        service_name='s3',
        aws_access_key_id='3207900NM6AZ01AN02O1',
        aws_secret_access_key='pmWuVRye20yiPbRk5tau1L6ggSueeaU5KXh2n0aZ',
        endpoint_url='http://localhost:9000',
        config=config
    )
