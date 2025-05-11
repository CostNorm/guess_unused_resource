import os
import logging
import json
from .s3_handler import get_costs_for_period, calculate_date_ranges
from .athena_query_handler import get_resource_ids_with_cost
import boto3
from typing import List, Dict, Any

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO').upper())




class UnusedAnalyzer:
    def __init__(self):
        # UnusedAnalyzer 클래스의 인스턴스를 초기화합니다. 환경변수에서 설정값을 읽어옵니다.
        self.potentially_unused_resource_details = []
        self.found_resource_ids = []
        # 환경 변수 읽기 (기본값 설정 포함)
        self.S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'day-by-day')
        self.RECENT_PERIOD_DAYS = int(os.environ.get('RECENT_PERIOD_DAYS', 7))
        self.COMPARISON_PERIOD_DAYS = int(os.environ.get('COMPARISON_PERIOD_DAYS', 30))
        self.COST_THRESHOLD_PERCENTAGE = float(os.environ.get('COST_THRESHOLD_PERCENTAGE', 1.0))
        self.MIN_COMPARISON_COST = float(os.environ.get('MIN_COMPARISON_COST', 0.01))
        

    def __identify_unused_resources(self,comparison_costs, recent_costs):
        """
        S3 비용 데이터 기반으로, 비교 기간 대비 최근 기간의 비용이 현저히 감소한 리소스(Service::Operation 쌍)를 잠재적 미사용 리소스로 식별합니다.
        """
        unused_resources = []
        cost_threshold_ratio = self.COST_THRESHOLD_PERCENTAGE / 100.0

        # 비교 기간 비용 데이터 기준으로 반복
        for resource, comp_cost in comparison_costs.items():
            # Criteria 1: Significant cost decrease (and comparison cost meets minimum)
            if comp_cost >= self.MIN_COMPARISON_COST:
                recent_cost = recent_costs.get(resource, 0.0)
                if recent_cost <= 0:
                    continue
            
                if recent_cost < (comp_cost * cost_threshold_ratio):
                    unused_info = {
                        "resource": resource,
                        "comparison_period_cost": comp_cost,
                        "recent_period_cost": recent_cost
                        # "reason" 키 제거
                    }
                    unused_resources.append(unused_info)
                    # 디버깅을 위한 상세 정보 출력 (단순화)
                    logger.debug(f"  [Potential Unused] Resource: {resource}")
                    logger.debug(f"    - Comparison Period Cost: ${comp_cost:.4f} (>= ${self.MIN_COMPARISON_COST:.4f})")
                    logger.debug(f"    - Recent Period Cost    : ${recent_cost:.4f} (< {self.COST_THRESHOLD_PERCENTAGE}% of comparison cost)")
                    
        
        return unused_resources

    def find_potentially_unused_resources_list(self) -> List[Dict[str, Any]]:
        """
        S3 비용 데이터를 분석하여 잠재적으로 사용되지 않는 리소스 목록을 반환합니다.
        """
        # 환경 변수 유효성 검사
        if not self.S3_BUCKET_NAME or 'your-cost-data-bucket-name' in self.S3_BUCKET_NAME:
            raise ValueError("Error: S3_BUCKET_NAME environment variable is not set correctly.")
        # MIN_COMPARISON_COST 유효성 검사 (선택사항이지만 추가)
        if self.MIN_COMPARISON_COST < 0:
            logger.warning(f"Warning: MIN_COMPARISON_COST ({self.MIN_COMPARISON_COST}) is negative. Using 0.0 instead.")
            # 음수 값 방지 위해 0으로 설정하거나 에러 발생 시킬 수 있음
            # 전역 변수 수정 위해 필요
            self.MIN_COMPARISON_COST = 0.0


        # 날짜 범위 계산
        recent_start_date, recent_end_date, comparison_start_date, comparison_end_date = \
            calculate_date_ranges(self.RECENT_PERIOD_DAYS, self.COMPARISON_PERIOD_DAYS)

        # 비용 계산
        comparison_costs = get_costs_for_period(self.S3_BUCKET_NAME, comparison_start_date, comparison_end_date)
        
        recent_costs = get_costs_for_period(self.S3_BUCKET_NAME, recent_start_date, recent_end_date)

        # 미사용 리소스 식별
        unused_resources = self.__identify_unused_resources(
            comparison_costs, recent_costs
        )

        self.potentially_unused_resource_details = unused_resources

        return unused_resources
    
    def find_unused_resource_ids(self) -> List[str]:
        """
        Athena 쿼리를 통해 잠재적 미사용 리소스의 실제 리소스 ID 목록을 조회합니다.
        """
        self.found_resource_ids = get_resource_ids_with_cost(
                self.potentially_unused_resource_details
            )
        return self.found_resource_ids


def find_unused_resource():
    """
    S3 비용 데이터와 Athena 쿼리를 활용하여 미사용 리소스를 종합적으로 분석하고 결과를 반환하는 함수입니다.
    """
    try:
        unused_analyzer = UnusedAnalyzer()
        
        # 1. 잠재적 미사용 리소스 식별
        unused_analyzer.find_potentially_unused_resources_list()

        # 2. Athena 쿼리 실행 (잠재적 미사용 리소스가 있을 경우)
        if not unused_analyzer.potentially_unused_resource_details:
            
            message = "No resource IDs to query."
            status_code = 200
        else:
            unused_analyzer.find_unused_resource_ids()
            message = f"Found {len(unused_analyzer.found_resource_ids)} unique resource IDs with costs for the associated services."
            status_code = 200

    except ValueError as ve: # 환경 변수 오류 등
        message = f"Configuration error: {ve}"
        logger.error(message)
        status_code = 400 # 설정 오류는 Bad Request 로 처리
    except Exception as e: # 비용 분석 또는 Athena 쿼리 중 발생한 모든 예외
            message = f"An error occurred: {e}"
            logger.error(f"Error during execution: {e}")
            
            status_code = 500 # 내부 서버 오류

        # 최종 응답 반환
    return {
        'statusCode': status_code,
        'body': json.dumps({
            'message': message,
            # 'potentially_unused_resource_details': unused_analyzer.potentially_unused_resource_details,
            'resource_ids_with_cost': unused_analyzer.found_resource_ids
        }, indent=2)
    }