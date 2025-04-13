# guess_unused_resource

AWS 비용 데이터를 분석하여 최근 사용량이 급감한 리소스를 식별하는 Lambda 함수입니다. 이를 통해 잠재적으로 사용되지 않는 리소스를 찾아 비용 최적화에 활용할 수 있습니다.

## 동작 방식

1.  **비용 데이터 로드**: 지정된 S3 버킷에서 일별 비용 데이터 CSV 파일을 읽어옵니다. 파일 이름은 `YYMMDD{FILE_SUFFIX}` 형식을 따릅니다. (예: `231026_sorted_costs.csv`)
2.  **기간 정의**:
    *   **최근 기간**: 함수 실행일 기준 전날부터 `RECENT_PERIOD_DAYS` 이전까지의 기간입니다.
    *   **비교 기간**: 최근 기간 시작일 전날부터 `COMPARISON_PERIOD_DAYS` 이전까지의 기간입니다.
3.  **비용 집계**: 각 기간에 대해 "Service::Operation" 조합별 총 비용을 집계합니다.
4.  **미사용 리소스 추정**: 비교 기간에는 비용이 발생했지만(> 0), 최근 기간에는 비용이 `비교 기간 비용 * (COST_THRESHOLD_PERCENTAGE / 100.0)` 미만인 리소스를 "잠재적 미사용 리소스"로 식별합니다.

## 설정 (환경 변수)

Lambda 함수 또는 로컬 실행 시 다음 환경 변수를 설정해야 합니다.

| 변수 이름                  | 설명                                                                                                | 기본값                  |
| :------------------------- | :-------------------------------------------------------------------------------------------------- | :---------------------- |
| `S3_BUCKET_NAME`           | 비용 데이터 CSV 파일이 저장된 S3 버킷 이름. **반드시 실제 버킷 이름으로 변경해야 합니다.**              | `your-cost-data-bucket-name` |
| `RECENT_PERIOD_DAYS`       | 최근 비용을 확인할 기간 (일).                                                                        | `7`                     |
| `COMPARISON_PERIOD_DAYS`   | 비교할 과거 비용 기간 (일).                                                                         | `30`                    |
| `COST_THRESHOLD_PERCENTAGE`| 비교 기간 비용 대비 최근 기간 비용의 허용 비율 (%). 이 비율 미만이면 미사용 리소스로 간주.           | `1.0`                   |
| `FILE_SUFFIX`              | S3에서 읽어올 비용 데이터 파일의 접미사.                                                            | `_sorted_costs.csv`     |

## 실행 방법

### AWS Lambda

1.  `lambda_function.py` 파일을 Lambda 함수로 배포합니다.
2.  Lambda 함수 설정에서 위 환경 변수들을 구성합니다.
3.  Lambda 함수 실행 역할(Role)에 대상 S3 버킷에 대한 `s3:GetObject` 권한을 부여합니다.
4.  필요에 따라 CloudWatch Events (EventBridge) 등을 사용하여 주기적으로 함수를 실행하도록 트리거를 설정합니다.

### 로컬 테스트

1.  스크립트가 있는 디렉토리로 이동합니다.
2.  필요한 환경 변수를 설정합니다. 특히 `S3_BUCKET_NAME`은 필수입니다.
    ```bash
    # 예시 (PowerShell)
    $env:S3_BUCKET_NAME = "your-actual-bucket-name"
    $env:RECENT_PERIOD_DAYS = "7"
    # ... 다른 변수들도 필요에 따라 설정
    ```
3.  로컬 환경에 AWS 자격 증명(Access Key, Secret Key, Session Token 또는 IAM Role)이 구성되어 있어야 합니다. (예: `~/.aws/credentials` 파일 또는 환경 변수 `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
4.  Python 스크립트를 직접 실행합니다.
    ```bash
    python lambda_function.py
    ```

## 입력 데이터 형식 (S3 CSV)

*   S3 버킷 루트에 `YYMMDD{FILE_SUFFIX}` 형식의 파일 이름으로 저장되어야 합니다. (예: `231026_sorted_costs.csv`)
*   각 CSV 파일은 UTF-8 인코딩이어야 합니다.
*   첫 번째 행은 헤더이며, 대소문자를 구분하지 않고 `Service`, `Operation`, `Cost` 열을 포함해야 합니다. 다른 열이 있어도 무방합니다.
*   `Cost` 열의 값은 숫자로 변환 가능해야 합니다.

**예시 CSV 내용:**

```csv
Service,Operation,Cost,UsageQuantity,ResourceId,etc
Amazon Elastic Compute Cloud,RunInstances,1.23,1,i-0123456789abcdef0,some_info
AWS Key Management Service,Decrypt,0.05,10,/alias/my-key,other_info
Amazon Simple Storage Service,PutObject,0.10,5,my-data-bucket,another_info
```

## 출력 형식 (Lambda 반환값)

Lambda 함수는 다음과 같은 구조의 JSON 객체를 반환합니다.

```json
{
  "statusCode": 200,
  "body": {
    "potentially_unused_resources": [
      {
        "resource": "Service::Operation",
        "comparison_period_cost": 15.75,
        "recent_period_cost": 0.10
      },
      // ... 다른 잠재적 미사용 리소스들
    ],
    "comparison_period": "YYYY-MM-DD to YYYY-MM-DD",
    "recent_period": "YYYY-MM-DD to YYYY-MM-DD"
  }
}
```