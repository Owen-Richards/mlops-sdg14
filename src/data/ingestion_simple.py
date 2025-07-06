"""
Simplified Marine Data Ingestion Module for Testing
Core functionality without heavy dependencies
"""

import os
import requests
import pandas as pd
import json
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
        """Fetch species occurrences from OBIS API"""
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
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            occurrences = data.get('results', [])
            
            logger.info(f"Retrieved {len(occurrences)} OBIS occurrences")
            return occurrences
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching OBIS data: {e}")
            return []


class GBIFSpeciesIngester:
    """Global Biodiversity Information Facility (GBIF) data ingestion"""
    
    def __init__(self, base_url: str = "https://api.gbif.org/v1"):
        self.base_url = base_url
    
    def get_species_occurrences(
        self, 
        region: Dict[str, float], 
        start_date: str, 
        end_date: str,
        taxon_key: Optional[int] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """Fetch species occurrences from GBIF API"""
        endpoint = f"{self.base_url}/occurrence/search"
        
        params = {
            'decimalLatitude': f"{region['south']},{region['north']}",
            'decimalLongitude': f"{region['west']},{region['east']}",
            'eventDate': f"{start_date},{end_date}",
            'hasCoordinate': 'true',
            'hasGeospatialIssue': 'false',
            'limit': min(limit, 300),  # GBIF API limit
            'basisOfRecord': 'OBSERVATION'
        }
        
        if taxon_key:
            params['taxonKey'] = taxon_key
        
        try:
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            occurrences = data.get('results', [])
            
            logger.info(f"Retrieved {len(occurrences)} GBIF occurrences")
            return occurrences
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching GBIF data: {e}")
            return []


class NOAABuoyIngester:
    """NOAA National Data Buoy Center data ingestion"""
    
    def __init__(self, base_url: str = "https://www.ndbc.noaa.gov"):
        self.base_url = base_url
    
    def get_buoy_data(self, station_id: str, data_type: str = "realtime2") -> Optional[pd.DataFrame]:
        """Fetch buoy data for a specific station"""
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


class ERDDAPIngester:
    """Environmental Research Division's Data Access Program (ERDDAP) ingestion"""
    
    def __init__(self, base_url: str = "https://coastwatch.pfeg.noaa.gov/erddap"):
        self.base_url = base_url
    
    def search_datasets(self, keywords: str) -> List[Dict]:
        """Search for available datasets"""
        endpoint = f"{self.base_url}/search/index.json"
        
        params = {
            'page': 1,
            'itemsPerPage': 100,
            'searchFor': keywords
        }
        
        try:
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            datasets = []
            
            # Parse ERDDAP search results
            if 'table' in data and 'rows' in data['table']:
                for row in data['table']['rows']:
                    if len(row) >= 3:
                        datasets.append({
                            'dataset_id': row[0],
                            'title': row[2] if len(row) > 2 else 'Unknown',
                            'summary': row[3] if len(row) > 3 else '',
                            'institution': row[4] if len(row) > 4 else ''
                        })
            
            logger.info(f"Found {len(datasets)} ERDDAP datasets for '{keywords}'")
            return datasets
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching ERDDAP datasets: {e}")
            return []


class MarineDataAggregator:
    """Simplified Marine Data Aggregator"""
    
    def __init__(self):
        self.obis = OBISDataIngester()
        self.gbif = GBIFSpeciesIngester()
        self.erddap = ERDDAPIngester()
        self.buoy = NOAABuoyIngester()
    
    def comprehensive_data_collection(
        self,
        region: Dict[str, float],
        start_date: str,
        end_date: str,
        target_species: Optional[List[str]] = None,
        include_environmental: bool = True,
        max_workers: int = 5
    ) -> Dict:
        """Collect comprehensive marine data from available sources"""
        results = {
            'biodiversity': {},
            'environmental': {},
            'physical_oceanography': {},
            'metadata': {
                'region': region,
                'date_range': {'start': start_date, 'end': end_date},
                'collection_timestamp': datetime.now().isoformat(),
                'data_sources': []
            }
        }
        
        # Collect OBIS data
        try:
            obis_data = self.obis.get_species_occurrences(region, start_date, end_date, limit=500)
            if obis_data:
                results['biodiversity']['obis_occurrences'] = obis_data
                results['metadata']['data_sources'].append('OBIS')
        except Exception as e:
            logger.error(f"OBIS collection failed: {e}")
        
        # Collect GBIF data
        try:
            gbif_data = self.gbif.get_species_occurrences(region, start_date, end_date, limit=500)
            if gbif_data:
                results['biodiversity']['gbif_occurrences'] = gbif_data
                results['metadata']['data_sources'].append('GBIF')
        except Exception as e:
            logger.error(f"GBIF collection failed: {e}")
        
        # Search ERDDAP datasets
        if include_environmental:
            try:
                sst_datasets = self.erddap.search_datasets("sea surface temperature")
                if sst_datasets:
                    results['environmental']['erddap_sst_datasets'] = sst_datasets[:5]
                    results['metadata']['data_sources'].append('ERDDAP')
            except Exception as e:
                logger.error(f"ERDDAP collection failed: {e}")
        
        # Collect sample buoy data
        if include_environmental:
            try:
                # Sample California buoy stations
                sample_stations = ['46050', '46005', '46013']
                buoy_data = {}
                
                for station in sample_stations[:2]:  # Limit for demo
                    data = self.buoy.get_buoy_data(station)
                    if data is not None:
                        buoy_data[station] = f"Data available: {len(data)} records"
                
                if buoy_data:
                    results['physical_oceanography']['noaa_buoys'] = buoy_data
                    results['metadata']['data_sources'].append('NOAA Buoys')
            except Exception as e:
                logger.error(f"Buoy data collection failed: {e}")
        
        # Add summary statistics
        results['metadata']['summary'] = self._generate_summary(results)
        
        return results
    
    def _generate_summary(self, results: Dict) -> Dict:
        """Generate summary statistics for collected data"""
        summary = {
            'total_datasets': 0,
            'total_records': 0,
            'data_types': [],
            'coverage': {}
        }
        
        for category, datasets in results.items():
            if category == 'metadata':
                continue
                
            summary['data_types'].append(category)
            
            for dataset_name, data in datasets.items():
                summary['total_datasets'] += 1
                
                if isinstance(data, list):
                    summary['total_records'] += len(data)
                elif isinstance(data, dict):
                    summary['total_records'] += 1
        
        return summary


def create_data_catalog(ingested_data: Dict) -> Dict:
    """Create a data catalog for all ingested datasets"""
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
        if category == 'metadata':
            continue
            
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
            elif isinstance(data, dict):
                dataset_info['record_count'] = len(data)
                catalog['summary']['total_records'] += len(data)
            
            catalog['datasets'][category][dataset_name] = dataset_info
            catalog['summary']['total_datasets'] += 1
        
        if catalog['datasets'][category]:
            catalog['summary']['data_sources'].append(category)
    
    return catalog
