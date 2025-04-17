import boto3
import os

# --- 설정 (삭제할 CUR 보고서 이름) ---
# 환경 변수에서 읽거나 직접 지정
CUR_REPORT_NAME = os.environ.get('CUR_REPORT_NAME', 'MyProgrammaticCUR')
# -------------------------------------

# CUR 클라이언트 생성 (CUR API는 us-east-1 리전만 지원)
cur_client = boto3.client('cur', region_name='us-east-1')

def delete_cur_report(report_name):
    """지정된 이름의 CUR 보고서 정의를 삭제합니다."""
    print(f"Attempting to delete CUR report definition: {report_name}")
    try:
        response = cur_client.delete_report_definition(
            ReportName=report_name
        )
        print(f"Successfully submitted deletion request for report definition '{report_name}'.", response)
        return True
    except cur_client.exceptions.ValidationException as e:
        # 이미 삭제되었거나 존재하지 않는 경우 ValidationException 발생
        if "Unable to find Report Definition" in str(e) or "not found" in str(e).lower():
             print(f"Report definition '{report_name}' not found or already deleted.")
             return True # 이미 없으므로 성공으로 간주
        else:
             print(f"Validation error deleting report definition '{report_name}': {e}")
             return False
    except Exception as e:
        print(f"An unexpected error occurred while deleting '{report_name}': {e}")
        return False

if __name__ == '__main__':
    print("--- Starting CUR Definition Deletion Script ---")
    if not CUR_REPORT_NAME:
        print("Error: CUR_REPORT_NAME is not set. Please set the environment variable or edit the script.")
    else:
        if delete_cur_report(CUR_REPORT_NAME):
            print(f"\nDeletion process for '{CUR_REPORT_NAME}' initiated or confirmed.")
        else:
            print(f"\nDeletion process for '{CUR_REPORT_NAME}' failed. Check the logs above.")
    print("--- CUR Definition Deletion Script Finished ---") 