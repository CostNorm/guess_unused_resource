import json
import logging
import os
from analyzer.unattach_analyzer import find_unattached_resources
from analyzer.unused_analyzer import find_unused_resource

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO').upper())


def lambda_handler(event, context):
    """
    AWS Lambda 함수 핸들러.
    API Gateway 또는 직접 호출을 통해 트리거됩니다.

    event (dict): 입력 이벤트 객체. 다음 키를 포함해야 함:
        - operation (str): 수행할 작업 ('analyze' 또는 'execute').
        - (선택) arn_id (str): eip, eni ID (analyze 및 execute에 사용).
        
    """
    
    logger.info(f"Received event: {json.dumps(event)}")

    operation = event.get('operation')
    
    if not operation:
        logger.error("필수 파라미터 누락: 'operation'과 'region'이 필요합니다.")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': "Missing required parameters: operation, region"})
        }

    try:
        if operation == 'analyze':
            unattach_id = find_unattached_resources()
            unused_id = find_unused_resource()
            status_code = 200
            response_body = {
                'unattach_id': unattach_id,
                'unused_id': unused_id
            }
        else:
            logger.error(f"지원되지 않는 작업 유형: {operation}")
            status_code = 400
            response_body = {'error': f"Unsupported operation: {operation}"}

        
    except Exception as e:
        logger.error(f"처리 중 예외 발생: {str(e)}", exc_info=True)
        status_code = 500
        response_body = {'error': f"Internal server error: {str(e)}"}
        return {
            'statusCode': status_code,
            'body': json.dumps(response_body)
        }

    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps(response_body)
    } 

    

    