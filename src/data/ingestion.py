"""
Data ingestion utilities for Marine Ecosystem Health & Species Presence Prediction Platform
"""

import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OBISDataIngester:
    """Ocean Biogeographic Information System (OBIS) data ingestion"""
    
    def __init__(self, base_url: str = "https://api.obis.org/v3"):
        self.base_url = base_url
    
    def get_species_occurrences(
        self, 
        region: Dict[str, float], 
        start_date: str, 
        end_date: str,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Fetch species occurrences from OBIS API
        
        Args:
            region: Dict with 'west', 'east', 'south', 'north' boundaries
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            limit: Maximum number of records to return
            
        Returns:
            List of occurrence records
        """
        endpoint = f"{self.base_url}/occurrence"
        
        # Create polygon geometry
        geometry = (
            f"POLYGON(({region['west']} {region['south']},"
            f"{region['east']} {region['south']},"
            f"{region['east']} {region['north']},"
            f"{region['west']} {region['north']},"
            f"{region['west']} {region['south']}))"
        )
        
        params = {
            'geometry': geometry,
            'startdate': start_date,
            'enddate': end_date,
            'size': limit
        }
        
        try:
            response = requests.get(endpoint, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            occurrences = data.get('results', [])
            
            logger.info(f"Retrieved {len(occurrences)} OBIS occurrences")
            return occurrences
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching OBIS data: {e}")
            return []


class NOAABuoyIngester:
    """NOAA National Data Buoy Center data ingestion"""
    
    def __init__(self, base_url: str = "https://www.ndbc.noaa.gov"):
        self.base_url = base_url
    
    def get_buoy_data(self, station_id: str, data_type: str = "realtime2") -> Optional[pd.DataFrame]:
        """
        Fetch buoy data for a specific station
        
        Args:
            station_id: NOAA buoy station ID
            data_type: Type of data ('realtime2', 'historical')
            
        Returns:
            DataFrame with buoy measurements or None if failed
        """
        url = f"{self.base_url}/data/{data_type}/{station_id}.txt"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse the fixed-width format
            lines = response.text.strip().split('\n')
            
            if len(lines) < 3:
                logger.warning(f"Insufficient data for station {station_id}")
                return None
            
            headers = lines[0].split()
            units = lines[1].split()
            
            # Parse data rows
            data_rows = []
            for line in lines[2:]:
                values = line.split()
                if len(values) == len(headers):
                    data_rows.append(values)
            
            if not data_rows:
                logger.warning(f"No data rows found for station {station_id}")
                return None
            
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            
            # Add metadata
            df.attrs['station_id'] = station_id
            df.attrs['units'] = dict(zip(headers, units))
            df.attrs['source'] = 'NOAA NDBC'
            
            logger.info(f"Retrieved {len(df)} records from buoy {station_id}")
            return df
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching buoy data for {station_id}: {e}")
            return None


class ArgoFloatIngester:
    """Argo float data ingestion from Argovis API"""
    
    def __init__(self, base_url: str = "https://argovis.colorado.edu"):
        self.base_url = base_url
    
    def get_profiles(
        self, 
        region: Dict[str, float], 
        start_date: str, 
        end_date: str,
        limit: int = 500
    ) -> List[Dict]:
        """
        Fetch Argo float profiles from Argovis API
        
        Args:
            region: Geographic boundaries
            start_date: Start date
            end_date: End date
            limit: Maximum profiles to return
            
        Returns:
            List of Argo profile records
        """
        endpoint = f"{self.base_url}/selection/profiles"
        
        # Create polygon shape for API
        shape = [
            [
                [region['west'], region['south']],
                [region['east'], region['south']],
                [region['east'], region['north']],
                [region['west'], region['north']],
                [region['west'], region['south']]
            ]
        ]
        
        params = {
            'startDate': start_date,
            'endDate': end_date,
            'shape': str(shape).replace("'", '"')
        }
        
        try:
            response = requests.get(endpoint, params=params, timeout=120)
            response.raise_for_status()
            
            profiles = response.json()
            
            # Limit results
            if len(profiles) > limit:
                profiles = profiles[:limit]
            
            logger.info(f"Retrieved {len(profiles)} Argo profiles")
            return profiles
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Argo data: {e}")
            return []


class DataValidator:
    """Validate ingested marine data"""
    
    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> bool:
        """Validate latitude and longitude ranges"""
        return -90 <= lat <= 90 and -180 <= lon <= 180
    
    @staticmethod
    def validate_date_range(start_date: str, end_date: str) -> bool:
        """Validate date range format and logic"""
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            return start <= end
        except ValueError:
            return False
    
    @staticmethod
    def validate_species_record(record: Dict) -> bool:
        """Validate a species occurrence record"""
        required_fields = ['species', 'decimalLatitude', 'decimalLongitude']
        return all(field in record for field in required_fields)
    
    @staticmethod
    def validate_buoy_record(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate buoy data DataFrame
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        if df.empty:
            issues.append("DataFrame is empty")
            return False, issues
        
        # Check for essential columns
        essential_cols = ['YY', 'MM', 'DD', 'hh', 'mm']
        missing_cols = [col for col in essential_cols if col not in df.columns]
        if missing_cols:
            issues.append(f"Missing time columns: {missing_cols}")
        
        # Check for data types and ranges
        if 'WVHT' in df.columns:  # Wave height
            try:
                wave_heights = pd.to_numeric(df['WVHT'], errors='coerce')
                if wave_heights.max() > 30:  # Unusually high waves
                    issues.append("Suspicious wave height values detected")
            except:
                issues.append("Cannot parse wave height data")
        
        return len(issues) == 0, issues


def create_data_catalog(ingested_data: Dict) -> Dict:
    """
    Create a data catalog for all ingested datasets
    
    Args:
        ingested_data: Dictionary containing all ingested datasets
        
    Returns:
        Data catalog with metadata
    """
    catalog = {
        'created_at': datetime.now().isoformat(),
        'datasets': {},
        'summary': {
            'total_datasets': 0,
            'total_records': 0,
            'data_sources': []
        }
    }
    
    for category, datasets in ingested_data.items():
        if not datasets:
            continue
            
        catalog['datasets'][category] = {}
        
        for dataset_name, data in datasets.items():
            if data is None:
                continue
                
            dataset_info = {
                'name': dataset_name,
                'type': type(data).__name__,
                'status': 'available'
            }
            
            # Add specific metadata based on data type
            if isinstance(data, list):
                dataset_info['record_count'] = len(data)
                catalog['summary']['total_records'] += len(data)
            elif isinstance(data, pd.DataFrame):
                dataset_info['record_count'] = len(data)
                dataset_info['columns'] = list(data.columns)
                catalog['summary']['total_records'] += len(data)
            elif hasattr(data, 'dims'):  # xarray Dataset
                dataset_info['dimensions'] = dict(data.dims)
                dataset_info['variables'] = list(data.data_vars)
            
            catalog['datasets'][category][dataset_name] = dataset_info
            catalog['summary']['total_datasets'] += 1
        
        if catalog['datasets'][category]:
            catalog['summary']['data_sources'].append(category)
    
    return catalog
