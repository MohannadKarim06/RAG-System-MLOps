import logging
import boto3
from datetime import datetime
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# CloudWatch handler (optional)
try:
    cloudwatch = boto3.client(
        'logs',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )
    
    def send_to_cloudwatch(message: str, level: str = "INFO"):
        try:
            cloudwatch.put_log_events(
                logGroupName='/aws/rag-system',
                logStreamName=datetime.now().strftime('%Y-%m-%d'),
                logEvents=[
                    {
                        'timestamp': int(datetime.now().timestamp() * 1000),
                        'message': f"[{level}] {message}"
                    }
                ]
            )
        except Exception as e:
            print(f"Failed to send log to CloudWatch: {e}")
    
except Exception:
    def send_to_cloudwatch(message: str, level: str = "INFO"):
        pass

