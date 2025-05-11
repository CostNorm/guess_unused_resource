
import boto3
import csv
import io
from datetime import datetime, timedelta, timezone
import os
import logging

FILE_SUFFIX = os.environ.get('FILE_SUFFIX', '_sorted_costs.csv')
s3_client = boto3.client('s3', 'ap-northeast-2')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO').upper())

def calculate_date_ranges(recent_period_days, comparison_period_days):
    """비용 비교를 위한 최근 기간과 비교 기간의 시작/종료 날짜를 계산합니다."""
    today = datetime.now(timezone.utc).date()
    recent_end_date = today - timedelta(days=1)
    recent_start_date = recent_end_date - timedelta(days=recent_period_days - 1)
    comparison_end_date = recent_start_date - timedelta(days=1)
    comparison_start_date = comparison_end_date - timedelta(days=comparison_period_days - 1)
    print(f"Date ranges calculated: Recent ({recent_start_date} to {recent_end_date}), Comparison ({comparison_start_date} to {comparison_end_date})")
    return recent_start_date, recent_end_date, comparison_start_date, comparison_end_date

def get_costs_for_period(bucket, start_date, end_date):
    """지정된 기간 동안의 비용 데이터를 S3에서 읽어 집계합니다."""
    costs = {} # {"Service::Operation": total_cost}
    current_date = start_date
    

    while current_date <= end_date:
        file_name = f"{current_date.strftime('%y%m%d')}{FILE_SUFFIX}"
        try:
            response = s3_client.get_object(Bucket=bucket, Key=file_name)
            content = response['Body'].read().decode('utf-8')
            csv_reader = csv.reader(io.StringIO(content))
            header = next(csv_reader)
            try:
                service_col = next(i for i, col in enumerate(header) if col.lower() == 'service')
                operation_col = next(i for i, col in enumerate(header) if col.lower() == 'operation')
                cost_col = next(i for i, col in enumerate(header) if col.lower() == 'cost')
            except StopIteration:
                logger.warning(f"Warning: Required columns (Service, Operation, Cost) not found in {file_name}. Skipping file.")
                current_date += timedelta(days=1)
                continue

            for row in csv_reader:
                if len(row) > max(service_col, operation_col, cost_col):
                    try:
                        service = row[service_col]
                        operation = row[operation_col]
                        cost_str = row[cost_col]
                        cost = float(cost_str)
                        resource_key = f"{service}::{operation}"
                        costs[resource_key] = costs.get(resource_key, 0.0) + cost
                    except ValueError:
                        logger.warning(f"Warning: Could not parse cost '{cost_str}' in row: {row} from file {file_name}. Skipping row.")
                    except IndexError:
                         logger.warning(f"Warning: Row {row} in file {file_name} does not have enough columns. Skipping row.")

        except s3_client.exceptions.NoSuchKey:
            logger.info(f"Info: File not found for date {current_date.strftime('%y%m%d')}: {file_name}")
        except Exception as e:
            logger.error(f"Error reading file {file_name}: {e}")

        current_date += timedelta(days=1)

    return costs


