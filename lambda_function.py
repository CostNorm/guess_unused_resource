import boto3
import csv
import io
import os
from datetime import datetime, timedelta

# 환경 변수에서 설정값 가져오기 (기본값 설정)
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'your-cost-data-bucket-name') # 실제 버킷 이름으로 변경 필요
RECENT_PERIOD_DAYS = int(os.environ.get('RECENT_PERIOD_DAYS', 7))
COMPARISON_PERIOD_DAYS = int(os.environ.get('COMPARISON_PERIOD_DAYS', 30))
COST_THRESHOLD_PERCENTAGE = float(os.environ.get('COST_THRESHOLD_PERCENTAGE', 1.0)) # 이전 기간 대비 비용 비율 (%)
FILE_SUFFIX = os.environ.get('FILE_SUFFIX', '_sorted_costs.csv') # 파일 이름 접미사

s3_client = boto3.client('s3')

def get_costs_for_period(bucket, start_date, end_date):
    """지정된 기간 동안의 비용 데이터를 S3에서 읽어 집계합니다."""
    costs = {} # {"Service::Operation": total_cost}
    current_date = start_date
    print(f"Fetching data from {start_date.strftime('%y%m%d')} to {end_date.strftime('%y%m%d')}")

    while current_date <= end_date:
        file_name = f"{current_date.strftime('%y%m%d')}{FILE_SUFFIX}"
        try:
            print(f"Attempting to get object: {file_name} from bucket: {bucket}")
            response = s3_client.get_object(Bucket=bucket, Key=file_name)
            content = response['Body'].read().decode('utf-8')
            csv_reader = csv.reader(io.StringIO(content))
            header = next(csv_reader) # 헤더 건너뛰기

            # 컬럼 인덱스 찾기 (대소문자 구분 없이)
            try:
                service_col = next(i for i, col in enumerate(header) if col.lower() == 'service')
                operation_col = next(i for i, col in enumerate(header) if col.lower() == 'operation')
                cost_col = next(i for i, col in enumerate(header) if col.lower() == 'cost')
            except StopIteration:
                print(f"Error: Required columns (Service, Operation, Cost) not found in {file_name}")
                continue # 다음 파일 처리

            for row in csv_reader:
                # 행 길이 확인 및 데이터 유효성 검사
                if len(row) > max(service_col, operation_col, cost_col):
                    try:
                        service = row[service_col]
                        operation = row[operation_col]
                        cost_str = row[cost_col]
                        cost = float(cost_str)
                        resource_key = f"{service}::{operation}"
                        costs[resource_key] = costs.get(resource_key, 0.0) + cost
                    except ValueError:
                        print(f"Warning: Could not parse cost '{cost_str}' in row: {row} from file {file_name}. Skipping row.")
                    except IndexError:
                         print(f"Warning: Row {row} in file {file_name} does not have enough columns. Skipping row.")
                else:
                     print(f"Warning: Row {row} in file {file_name} does not have enough columns. Skipping row.")


        except s3_client.exceptions.NoSuchKey:
            print(f"Info: File not found for date {current_date.strftime('%y%m%d')}: {file_name}")
        except Exception as e:
            print(f"Error reading file {file_name}: {e}")

        current_date += timedelta(days=1)

    print(f"Finished fetching data. Found {len(costs)} distinct resources.")
    return costs

def lambda_handler(event, context):
    """Lambda 함수 핸들러"""
    today = datetime.today().date()

    # 최근 기간 정의
    recent_end_date = today - timedelta(days=1) # 오늘 제외, 어제까지
    recent_start_date = recent_end_date - timedelta(days=RECENT_PERIOD_DAYS - 1)

    # 비교 기간 정의
    comparison_end_date = recent_start_date - timedelta(days=1)
    comparison_start_date = comparison_end_date - timedelta(days=COMPARISON_PERIOD_DAYS - 1)

    print("Calculating costs for comparison period...")
    comparison_costs = get_costs_for_period(S3_BUCKET_NAME, comparison_start_date, comparison_end_date)

    print("Calculating costs for recent period...")
    recent_costs = get_costs_for_period(S3_BUCKET_NAME, recent_start_date, recent_end_date)

    unused_resources = []
    cost_threshold_ratio = COST_THRESHOLD_PERCENTAGE / 100.0

    print("Identifying potentially unused resources...")
    for resource, comp_cost in comparison_costs.items():
        if comp_cost > 0: # 비교 기간에 비용이 발생한 리소스만 확인
            recent_cost = recent_costs.get(resource, 0.0)
            # 최근 비용이 0이거나, 비교 기간 비용의 임계 비율 미만인 경우
            if recent_cost < (comp_cost * cost_threshold_ratio):
                unused_resources.append({
                    "resource": resource,
                    "comparison_period_cost": comp_cost,
                    "recent_period_cost": recent_cost
                })
                print(f"  - Found potential unused resource: {resource} (Recent: {recent_cost:.6f}, Comparison: {comp_cost:.6f})")

    print(f"Identified {len(unused_resources)} potentially unused resources.")

    return {
        'statusCode': 200,
        'body': {
            'potentially_unused_resources': unused_resources,
            'comparison_period': f"{comparison_start_date.strftime('%Y-%m-%d')} to {comparison_end_date.strftime('%Y-%m-%d')}",
            'recent_period': f"{recent_start_date.strftime('%Y-%m-%d')} to {recent_end_date.strftime('%Y-%m-%d')}"
        }
    }

# 로컬 테스트용 (Lambda 환경에서는 실행되지 않음)
if __name__ == '__main__':
    # 테스트를 위해 S3_BUCKET_NAME 환경 변수 설정 필요
    # 예: os.environ['S3_BUCKET_NAME'] = 'your-test-bucket'
    # 로컬에 AWS 자격 증명이 설정되어 있어야 함
    if 'S3_BUCKET_NAME' not in os.environ or os.environ['S3_BUCKET_NAME'] == 'your-cost-data-bucket-name':
         print("Please set the 'S3_BUCKET_NAME' environment variable for local testing.")
    else:
        result = lambda_handler(None, None)
        import json
        print("--- Function Result ---")
        print(json.dumps(result, indent=2)) 