import boto3
import datetime

def extract_ts_segments(bucket_name, start_time, end_time, output_file):
    """Extracts .ts segments between two specified datetimes from an AWS S3 bucket and converts them into one .wav or .flac file.

    Args:
        bucket_name (str): The name of the AWS S3 bucket.
        start_time (datetime): The start datetime.
        end_time (datetime): The end datetime.
        output_file (str): The path to the output .wav or .flac file.
    """

    # Get the S3 client.
#    s3 = boto3.client('s3')

    # List the contents of the bucket.
    
    files = s3.list_objects(bucket_name)

    # Extract the .ts files.
    for file in files['Contents']:
        if file['Key'].endswith('.ts'):
            if start_time <= datetime.datetime(file['Key']) < end_time:
                with open(output_file, 'wb') as f:
                    f.write(s3.download_object(bucket_name, file['Key']).content)

if __name__ == '__main__':
    # Get the AWS S3 credentials.
    aws_access_key_id = 'tj#6mU5DZXk33d&%TmDyFY8xj3VL@i6'
    aws_secret_access_key = 'AKIAZN2WCXIF4EU64M5X,TkCEW2rkK5RIsP8Vfjrtr3uDruLUF3WZbZ+fCUzL'

    # Create the AWS S3 client.
    s3 = boto3.client('s3')#, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

    # Get the bucket name.
    bucket_name = 'streaming-orcasound-net'

    # Get the output file path.
    output_file = 'output.wav'

    # Extract the .ts segments between two specified datetimes.
    extract_ts_segments(bucket_name, '2023-03-25T09:00:00Z', '2023-03-25T09:10:00Z', output_file)