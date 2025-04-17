import boto3
import os
import json

# --- 설정 (필요시 환경 변수 또는 직접 값으로 수정) ---
CUR_REPORT_NAME = os.environ.get('CUR_REPORT_NAME', 'MyProgrammaticCUR')
# CUR 데이터를 저장할 S3 버킷 이름 (필수)
CUR_S3_BUCKET = os.environ.get('CUR_S3_BUCKET', 'your-cur-s3-bucket-name') # 반드시 실제 버킷 이름으로 변경!
CUR_S3_PREFIX = os.environ.get('CUR_S3_PREFIX', 'cur-reports') # S3 내 저장 경로 접두사 (선택 사항)
CUR_S3_REGION = os.environ.get('CUR_S3_REGION', 'ap-northeast-2') # S3 버킷이 있는 리전
TIME_UNIT = os.environ.get('TIME_UNIT', 'HOURLY') # HOURLY, DAILY, MONTHLY
REPORT_FORMAT = os.environ.get('REPORT_FORMAT', 'textORcsv') # textORcsv, Parquet
COMPRESSION = os.environ.get('COMPRESSION', 'GZIP') # GZIP, ZIP, Parquet
# Athena 통합 등 추가 설정 (필요시 주석 해제 및 수정)
ADDITIONAL_ARTIFACTS = ['ATHENA'] # 'REDSHIFT', 'QUICKSIGHT'
# -----------------------------------------------------

# CUR 클라이언트 생성 (CUR API는 us-east-1 리전만 지원)
cur_client = boto3.client('cur', region_name='us-east-1')

def lambda_handler(event, context):
    """
    AWS Cost and Usage Report (CUR) 정의를 생성하거나 업데이트하는 Lambda 함수 핸들러.
    """
    print(f"CUR 정의 생성/업데이트 시도: ReportName={CUR_REPORT_NAME}, S3Bucket={CUR_S3_BUCKET}")

    if CUR_S3_BUCKET == 'your-cur-s3-bucket-name':
        error_message = "오류: 환경 변수 'CUR_S3_BUCKET' 또는 코드 내 'CUR_S3_BUCKET' 변수에 실제 S3 버킷 이름을 설정해야 합니다."
        print(error_message)
        return {
            'statusCode': 400,
            'body': json.dumps({'error': error_message})
        }

    try:
        report_definition = {
            'ReportName': CUR_REPORT_NAME,
            'TimeUnit': TIME_UNIT,
            'Format': REPORT_FORMAT,
            'Compression': COMPRESSION,
            'AdditionalSchemaElements': [
                'RESOURCES',
            ],
            'S3Bucket': CUR_S3_BUCKET,
            'S3Prefix': CUR_S3_PREFIX,
            'S3Region': CUR_S3_REGION,
            # --- 아래 두 개 다시 활성화 ---
            'RefreshClosedReports': True,
            'ReportVersioning': 'OVERWRITE_REPORT'
            # --- Athena 통합은 다시 주석 처리 ---
            # 'AdditionalArtifacts': ADDITIONAL_ARTIFACTS
        }

        # --- AdditionalArtifacts 조건문은 이제 불필요하므로 제거하거나 주석처리 해도 됩니다. ---
        # if ADDITIONAL_ARTIFACTS:
        #     report_definition['AdditionalArtifacts'] = ADDITIONAL_ARTIFACTS

        response = cur_client.put_report_definition(
            ReportDefinition=report_definition
        )
        print("CUR 정의 생성/수정 성공:", response)
        return {
            'statusCode': 200,
            'body': json.dumps({'message': f"CUR report definition '{CUR_REPORT_NAME}' created/updated successfully."})
        }

    except Exception as e:
        error_message = f"CUR 정의 생성/수정 오류: {e}"
        print(error_message)

        error_details = {'exception_type': type(e).__name__, 'exception_args': e.args}
        if hasattr(e, 'response'):
            print("Boto3 응답 상세 정보:", e.response) # 전체 응답 구조 출력
            error_details['response'] = e.response
            if 'Error' in e.response:
                 error_details['error_code'] = e.response['Error'].get('Code')
                 error_details['error_message'] = e.response['Error'].get('Message')

        print("오류 상세 정보:", json.dumps(error_details)) # JSON 형태로 상세 정보 출력

        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_message, 'details': error_details}) # 반환값에도 포함
        }

# 로컬 테스트용 (Lambda 환경에서는 이 부분이 직접 실행되지 않음)
# if __name__ == '__main__':
#     # 로컬에서 테스트하려면 환경 변수를 설정하거나 위 설정 변수를 직접 수정하세요.
#     # 예: os.environ['CUR_S3_BUCKET'] = 'my-actual-cur-bucket'
#     result = lambda_handler(None, None)
#     print("\n--- 로컬 테스트 결과 ---")
#     print(json.dumps(result, indent=2))
