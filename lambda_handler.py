import serverless_wsgi
from simple_web import app

# Configure serverless-wsgi to handle binary content
serverless_wsgi.TEXT_MIME_TYPES = []

def handler(event, context):
    """AWS Lambda handler function with CORS support"""
    # Debug logging
    print(f"Original path: {event.get('path', 'Unknown')}")
    
    # Normalize paths - remove /Prod prefix if present
    if event.get('path', '').startswith('/Prod'):
        event['path'] = event['path'][5:]  # Remove '/Prod'
        print(f"Normalized path: {event['path']}")
    
    # Handle OPTIONS requests for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Max-Age': '86400'
            },
            'body': ''
        }
    
    # Handle the request
    response = serverless_wsgi.handle_request(app, event, context)
    
    # Ensure CORS headers are present
    if 'headers' not in response:
        response['headers'] = {}
    
    response['headers']['Access-Control-Allow-Origin'] = '*'
    response['headers']['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response['headers']['Access-Control-Allow-Headers'] = 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
    
    return response
