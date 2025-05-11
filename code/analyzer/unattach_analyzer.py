import logging
import os
import boto3
import concurrent.futures
from typing import Dict, List

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO').upper())


class UnattachAnalyzer:

    def __init__(self, region):
        # UnattachAnalyzer 인스턴스를 초기화하고, 지정된 리전의 EC2 클라이언트를 생성합니다.
        self.region = region
        self.ec2_client = boto3.client('ec2', region_name=region)
        

    def __analyze_eni(self):
        """
        미사용(available) 상태의 ENI(Network Interface) ID 목록을 조회합니다.
        """
        unused_enis = []
        enis = self.ec2_client.describe_network_interfaces(
                Filters=[{'Name': 'status', 'Values': ['available']}]
            )['NetworkInterfaces']
            
        for eni in enis:
            eni_id = eni['NetworkInterfaceId']
            unused_enis.append(eni_id)
    
        return unused_enis
    
    def __analyze_eip(self):
        """
        미할당(어태치되지 않은) EIP(Elastic IP) ID 목록을 조회합니다.
        """
        unused_eips = []
        addresses = self.ec2_client.describe_addresses()['Addresses']
        for address in addresses:
                if 'InstanceId' not in address and 'NetworkInterfaceId' not in address:
                    eip_id = address['AllocationId']
                    unused_eips.append(eip_id)
        return unused_eips
    

    def search_region_resources(self):
        """
        해당 리전에서 미사용 EIP와 ENI를 모두 조회하여 결과를 반환합니다.
        """
        try:
            # Search for unattached EIPs
            unused_eips = self.__analyze_eip()
            
            # Search for unattached ENIs
            unused_enis = self.__analyze_eni()
            

            result = {
                'region': self.region,
                'eips': unused_eips,
                'enis': unused_enis
            }
            return result
                    
        except Exception as e:
            logger.error(f"Error occurred while searching region {self.region}: {str(e)}")
            return {
                'region': self.region,
                'eips': [],
                'enis': [],
                'error': str(e)
            }

def get_all_regions():
    """Returns a list of all AWS regions."""
    ec2_client = boto3.client('ec2')

    regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    return regions
    

def find_unattached_resources() -> Dict[str, Dict[str, List[str]] ]:
    """Asynchronously finds unattached resources across all regions."""
    all_regions = get_all_regions()
    
    all_results = []
    
    # Use ThreadPoolExecutor for parallel region search
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit tasks for each region using UnattachAnalyzer instance
        future_to_region = {
            executor.submit(UnattachAnalyzer(region).search_region_resources): region
            for region in all_regions
        }
        
        # Collect results
        for future in concurrent.futures.as_completed(future_to_region):
            region = future_to_region[future]
            try:
                result = future.result()
                all_results.append(result)
            except Exception as e:
                all_results.append({
                    'region': region,
                    'eips': [],
                    'enis': [],
                    'error': str(e)
                })

    # Process results into the new format: {"eips": {"region": [...]}...}
    all_unused_resources = {}
    
    for result in all_results:
        region = result['region']
        if 'error' not in result:
            if result['eips']:
                if "eips" not in all_unused_resources:
                    all_unused_resources["eips"] = {}
                all_unused_resources["eips"][region] = result['eips']
            if result['enis']:
                if "enis" not in all_unused_resources:
                    all_unused_resources["enis"] = {}
                all_unused_resources["enis"][region] = result['enis']
    
    return all_unused_resources
    
