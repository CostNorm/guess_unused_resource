import boto3

def delete_eip(region, eip_id):
    """
    EIP(Elastic IP)를 해제합니다.
    
    Args:
        ec2_client: boto3 EC2 클라이언트
        eip_id: 해제할 EIP의 AllocationId (예: 'eip-12345')
        
    Raises:
        Exception: EIP 해제 중 오류가 발생한 경우
    """
    try:
        # EIP 해제
        ec2_client = boto3.client('ec2', region_name=region)
        ec2_client.release_address(AllocationId=eip_id)
        print(f"✅ EIP {eip_id} 해제 성공")
        return True
    except Exception as e:
        print(f"❌ EIP {eip_id} 해제 실패: {str(e)}")
        # 예외를 다시 발생시켜 상위 함수에서 처리하도록 함
        raise

def delete_eni(region, eni_id):
    """
    ENI(Elastic Network Interface)를 삭제합니다.
    
    Args:
        ec2_client: boto3 EC2 클라이언트
        eni_id: 삭제할 ENI의 ID (예: 'eni-12345')
        
    Raises:
        Exception: ENI 삭제 중 오류가 발생한 경우
    """
    try:
        # ENI 삭제
        ec2_client = boto3.client('ec2', region_name=region)
        ec2_client.delete_network_interface(NetworkInterfaceId=eni_id)
        print(f"✅ ENI {eni_id} 삭제 성공")
        return True
    except Exception as e:
        print(f"❌ ENI {eni_id} 삭제 실패: {str(e)}")
        # 예외를 다시 발생시켜 상위 함수에서 처리하도록 함
        raise


def delete_handler(region, arn_id):
    if arn_id.startswith('eni'):
        delete_eni(region, arn_id)
    elif arn_id.startswith('eip'):
        delete_eip(region, arn_id)
    else:
        raise ValueError(f"지원되지 않는 리소스 유형: {arn_id}")