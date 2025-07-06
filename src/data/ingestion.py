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
import xarray as xr
import netCDF4
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

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
        """
        Fetch species occurrences from GBIF API
        
        Args:
            region: Geographic boundaries
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            taxon_key: Optional specific taxon to filter
            limit: Maximum records to return
            
        Returns:
            List of occurrence records
        """
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

    def search_species(self, name: str) -> List[Dict]:
        """Search for species by name"""
        endpoint = f"{self.base_url}/species/search"
        params = {'q': name, 'limit': 20}
        
        try:
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data.get('results', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching GBIF species: {e}")
            return []


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
    
    def get_dataset_info(self, dataset_id: str) -> Optional[Dict]:
        """Get detailed information about a dataset"""
        endpoint = f"{self.base_url}/info/{dataset_id}/index.json"
        
        try:
            response = requests.get(endpoint, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract dataset metadata
            info = {
                'dataset_id': dataset_id,
                'attributes': {},
                'variables': []
            }
            
            if 'table' in data and 'rows' in data['table']:
                for row in data['table']['rows']:
                    if len(row) >= 5:
                        row_type = row[0]
                        if row_type == 'attribute':
                            info['attributes'][row[1]] = row[4]
                        elif row_type == 'variable':
                            info['variables'].append({
                                'name': row[1],
                                'type': row[2],
                                'units': row[3] if len(row) > 3 else '',
                                'long_name': row[4] if len(row) > 4 else ''
                            })
            
            return info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting ERDDAP dataset info for {dataset_id}: {e}")
            return None
    
    def download_griddap_data(
        self, 
        dataset_id: str, 
        variables: List[str],
        constraints: Dict[str, Tuple[float, float]],
        output_format: str = "nc"
    ) -> Optional[str]:
        """
        Download gridded data from ERDDAP
        
        Args:
            dataset_id: ERDDAP dataset ID
            variables: List of variable names to download
            constraints: Dict of dimension constraints (min, max)
            output_format: Output format (nc, csv, json)
            
        Returns:
            URL for downloaded data or None if failed
        """
        # Build constraint string
        constraint_parts = []
        for dim, (min_val, max_val) in constraints.items():
            constraint_parts.append(f"[({min_val}):1:({max_val})]")
        
        constraint_str = "".join(constraint_parts)
        
        # Build variable list
        var_str = ",".join(variables)
        
        # Construct download URL
        download_url = f"{self.base_url}/griddap/{dataset_id}.{output_format}?{var_str}{constraint_str}"
        
        try:
            response = requests.head(download_url, timeout=30)
            response.raise_for_status()
            
            logger.info(f"ERDDAP griddap download URL: {download_url}")
            return download_url
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating ERDDAP download URL: {e}")
            return None


class EMODnetBiologyIngester:
    """European Marine Observation and Data Network Biology data ingestion"""
    
    def __init__(self, base_url: str = "https://www.emodnet-biology.eu"):
        self.base_url = base_url
        self.wfs_url = "https://geo.vliz.be/geoserver/Emodnetbio/wfs"
    
    def get_species_distribution(
        self, 
        region: Dict[str, float],
        species_name: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch species distribution data via WFS
        
        Args:
            region: Geographic boundaries
            species_name: Optional species filter
            
        Returns:
            List of species occurrence records
        """
        params = {
            'service': 'WFS',
            'version': '1.1.0',
            'request': 'GetFeature',
            'typeName': 'Emodnetbio:eurobis-obisenv_basic',
            'outputFormat': 'application/json',
            'maxFeatures': 1000
        }
        
        # Add bounding box filter
        bbox = f"{region['west']},{region['south']},{region['east']},{region['north']}"
        params['bbox'] = bbox
        
        # Add species filter if provided
        if species_name:
            params['CQL_FILTER'] = f"scientific_name LIKE '%{species_name}%'"
        
        try:
            response = requests.get(self.wfs_url, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            # Extract properties from GeoJSON features
            records = []
            for feature in features:
                properties = feature.get('properties', {})
                geometry = feature.get('geometry', {})
                
                if geometry.get('coordinates'):
                    record = properties.copy()
                    record['longitude'] = geometry['coordinates'][0]
                    record['latitude'] = geometry['coordinates'][1]
                    records.append(record)
            
            logger.info(f"Retrieved {len(records)} EMODnet Biology records")
            return records
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching EMODnet Biology data: {e}")
            return []


class SatelliteDataIngester:
    """Satellite oceanographic data ingestion from multiple sources"""
    
    def __init__(self):
        self.erddap_servers = {
            'noaa': 'https://coastwatch.pfeg.noaa.gov/erddap',
            'marine_ie': 'https://erddap.marine.ie/erddap',
            'ifremer': 'https://www.ifremer.fr/erddap'
        }
    
    def get_sea_surface_temperature(
        self, 
        region: Dict[str, float], 
        start_date: str, 
        end_date: str,
        server: str = 'noaa'
    ) -> Optional[Dict]:
        """
        Fetch sea surface temperature data
        
        Args:
            region: Geographic boundaries
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            server: ERDDAP server to use
            
        Returns:
            Dataset information or None
        """
        base_url = self.erddap_servers.get(server, self.erddap_servers['noaa'])
        
        # Common SST dataset IDs
        sst_datasets = [
            'nesdisGeoPolarSSTN1day',  # NOAA Polar SST
            'jplMURSST41',             # JPL MUR SST
            'nesdisViirsSSTnrt',       # VIIRS SST
        ]
        
        for dataset_id in sst_datasets:
            try:
                # Check if dataset exists
                info_url = f"{base_url}/info/{dataset_id}/index.json"
                response = requests.get(info_url, timeout=30)
                
                if response.status_code == 200:
                    # Build download URL
                    download_url = (
                        f"{base_url}/griddap/{dataset_id}.nc?"
                        f"sst[({start_date}):1:({end_date})]"
                        f"[({region['south']}):1:({region['north']})]"
                        f"[({region['west']}):1:({region['east']})]"
                    )
                    
                    logger.info(f"Found SST dataset: {dataset_id}")
                    return {
                        'dataset_id': dataset_id,
                        'download_url': download_url,
                        'server': server,
                        'variable': 'sst',
                        'type': 'sea_surface_temperature'
                    }
                    
            except requests.exceptions.RequestException:
                continue
        
        logger.warning("No SST datasets found")
        return None
    
    def get_chlorophyll_data(
        self, 
        region: Dict[str, float], 
        start_date: str, 
        end_date: str,
        server: str = 'noaa'
    ) -> Optional[Dict]:
        """Fetch chlorophyll-a concentration data"""
        base_url = self.erddap_servers.get(server, self.erddap_servers['noaa'])
        
        # Common chlorophyll dataset IDs
        chl_datasets = [
            'erdMBchla1day',           # MODIS Aqua chlorophyll
            'erdVHNchla1day',          # VIIRS-NPP chlorophyll
            'pmlEsaCci60OcChlDaily',   # ESA CCI chlorophyll
        ]
        
        for dataset_id in chl_datasets:
            try:
                info_url = f"{base_url}/info/{dataset_id}/index.json"
                response = requests.get(info_url, timeout=30)
                
                if response.status_code == 200:
                    download_url = (
                        f"{base_url}/griddap/{dataset_id}.nc?"
                        f"chlorophyll[({start_date}):1:({end_date})]"
                        f"[({region['south']}):1:({region['north']})]"
                        f"[({region['west']}):1:({region['east']})]"
                    )
                    
                    logger.info(f"Found chlorophyll dataset: {dataset_id}")
                    return {
                        'dataset_id': dataset_id,
                        'download_url': download_url,
                        'server': server,
                        'variable': 'chlorophyll',
                        'type': 'chlorophyll_concentration'
                    }
                    
            except requests.exceptions.RequestException:
                continue
        
        logger.warning("No chlorophyll datasets found")
        return None


class IOOSDataIngester:
    """Integrated Ocean Observing System (IOOS) data ingestion"""
    
    def __init__(self, base_url: str = "https://data.ioos.us"):
        self.base_url = base_url
    
    def get_sensor_data(
        self, 
        region: Dict[str, float],
        parameters: List[str],
        start_time: str,
        end_time: str
    ) -> List[Dict]:
        """
        Fetch sensor data from IOOS network
        
        Args:
            region: Geographic boundaries
            parameters: List of parameter names (e.g., 'sea_water_temperature')
            start_time: Start time in ISO format
            end_time: End time in ISO format
            
        Returns:
            List of sensor station data
        """
        # IOOS SOS (Sensor Observation Service) endpoint
        sos_url = "https://sos.ioos.us/sos"
        
        stations = []
        
        for parameter in parameters:
            params = {
                'service': 'SOS',
                'version': '1.0.0',
                'request': 'GetObservation',
                'offering': 'urn:ioos:network:all',
                'observedProperty': parameter,
                'responseFormat': 'application/json',
                'eventTime': f"{start_time}/{end_time}",
                'featureOfInterest': f"BBOX:{region['west']},{region['south']},{region['east']},{region['north']}"
            }
            
            try:
                response = requests.get(sos_url, params=params, timeout=60)
                if response.status_code == 200:
                    # Note: Actual parsing would depend on SOS response format
                    logger.info(f"Retrieved IOOS data for parameter: {parameter}")
                    stations.append({
                        'parameter': parameter,
                        'data_url': response.url,
                        'status': 'available'
                    })
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching IOOS data for {parameter}: {e}")
        
        return stations


class WOADataIngester:
    """World Ocean Atlas (WOA) climatological data ingestion"""
    
    def __init__(self, base_url: str = "https://www.ncei.noaa.gov/thredds/dodsC/ncei/woa"):
        self.base_url = base_url
    
    def get_climatology(
        self, 
        variable: str,
        region: Dict[str, float],
        depth_range: Optional[Tuple[float, float]] = None,
        time_period: str = "decav"
    ) -> Optional[str]:
        """
        Get World Ocean Atlas climatological data
        
        Args:
            variable: WOA variable (temperature, salinity, oxygen, etc.)
            region: Geographic boundaries
            depth_range: Optional depth range in meters
            time_period: Time period (decav=decadal average)
            
        Returns:
            OPeNDAP URL for the dataset
        """
        # Map variables to WOA dataset paths
        variable_map = {
            'temperature': 'temperature/2018/0.25',
            'salinity': 'salinity/2018/0.25',
            'oxygen': 'oxygen/2018/all',
            'nitrate': 'nitrate/2018/all',
            'phosphate': 'phosphate/2018/all',
            'silicate': 'silicate/2018/all'
        }
        
        if variable not in variable_map:
            logger.error(f"Unknown WOA variable: {variable}")
            return None
        
        dataset_path = variable_map[variable]
        
        # Construct OPeNDAP URL
        opendap_url = f"{self.base_url}/{dataset_path}/woa18_{time_period}_{variable}_01.nc"
        
        try:
            # Test if URL is accessible
            response = requests.head(opendap_url, timeout=30)
            response.raise_for_status()
            
            logger.info(f"WOA {variable} climatology available: {opendap_url}")
            return opendap_url
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error accessing WOA {variable} data: {e}")
            return None


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


class MarineDataAggregator:
    """Aggregate data from multiple marine data sources"""
    
    def __init__(self):
        # Biodiversity and species data
        self.obis = OBISDataIngester()
        self.gbif = GBIFSpeciesIngester()
        self.emodnet = EMODnetBiologyIngester()
        self.fishbase = FishBaseIngester()
        
        # Physical oceanography
        self.erddap = ERDDAPIngester()
        self.satellite = SatelliteDataIngester()
        self.ioos = IOOSDataIngester()
        self.woa = WOADataIngester()
        self.argo = ArgoFloatIngester()
        self.buoy = NOAABuoyIngester()
        self.copernicus = CopernicusMarineIngester()
        self.onc = OceanNetworksCanadaIngester()
        
        # Biogeochemistry and climate
        self.glodap = GLODAPIngester()
        self.socat = SOCATIngester()
        
        # Human activities and conservation
        self.gfw = GlobalFishingWatchIngester()
        self.marine_traffic = MarineTrafficIngester()
        self.coral_watch = NOAACoralReefWatchIngester()
    
    def comprehensive_data_collection(
        self,
        region: Dict[str, float],
        start_date: str,
        end_date: str,
        target_species: Optional[List[str]] = None,
        include_environmental: bool = True,
        max_workers: int = 5
    ) -> Dict:
        """
        Collect comprehensive marine data from all available sources
        
        Args:
            region: Geographic boundaries
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            target_species: Optional list of species to focus on
            include_environmental: Whether to include environmental data
            max_workers: Number of parallel workers
            
        Returns:
            Dictionary containing all collected data
        """
        results = {
            'biodiversity': {},
            'environmental': {},
            'physical_oceanography': {},
            'biogeochemistry': {},
            'human_activities': {},
            'conservation': {},
            'metadata': {
                'region': region,
                'date_range': {'start': start_date, 'end': end_date},
                'collection_timestamp': datetime.now().isoformat(),
                'data_sources': []
            }
        }
        
        # Define data collection tasks
        tasks = []
        
        # Biodiversity data tasks
        tasks.extend([
            ('obis_occurrences', self._collect_obis_data, region, start_date, end_date),
            ('gbif_occurrences', self._collect_gbif_data, region, start_date, end_date),
            ('emodnet_biology', self._collect_emodnet_data, region),
            ('fishbase_ecology', self._collect_fishbase_data, target_species)
        ])
        
        # Environmental data tasks (if requested)
        if include_environmental:
            tasks.extend([
                ('sea_surface_temperature', self._collect_sst_data, region, start_date, end_date),
                ('chlorophyll', self._collect_chlorophyll_data, region, start_date, end_date),
                ('argo_profiles', self._collect_argo_data, region, start_date, end_date),
                ('buoy_data', self._collect_buoy_data, region),
                ('woa_climatology', self._collect_woa_data, region),
                ('copernicus_data', self._collect_copernicus_data, region, start_date, end_date),
                ('onc_real_time', self._collect_onc_data, region, start_date, end_date),
                ('coral_bleaching', self._collect_coral_watch_data, region)
            ])
        
        # Biogeochemistry tasks
        tasks.extend([
            ('glodap_carbon', self._collect_glodap_data, region),
            ('socat_co2', self._collect_socat_data, region, start_date, end_date)
        ])
        
        # Human activities tasks
        tasks.extend([
            ('fishing_effort', self._collect_gfw_data, region, start_date, end_date),
            ('vessel_traffic', self._collect_vessel_traffic_data, region)
        ])
        
        # Execute tasks in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(self._execute_task, task): task[0] 
                for task in tasks
            }
            
            for future in as_completed(future_to_task):
                task_name = future_to_task[future]
                try:
                    result = future.result(timeout=120)
                    if result:
                        category = self._get_data_category(task_name)
                        results[category][task_name] = result
                        results['metadata']['data_sources'].append(task_name)
                        logger.info(f"Completed task: {task_name}")
                except Exception as e:
                    logger.error(f"Task {task_name} failed: {e}")
        
        # Add summary statistics
        results['metadata']['summary'] = self._generate_summary(results)
        
        return results
    
    def _execute_task(self, task):
        """Execute a data collection task"""
        task_name, func, *args = task
        try:
            return func(*args)
        except Exception as e:
            logger.error(f"Error in task {task_name}: {e}")
            return None
    
    def _collect_obis_data(self, region, start_date, end_date):
        """Collect OBIS data"""
        return self.obis.get_species_occurrences(region, start_date, end_date, limit=2000)
    
    def _collect_gbif_data(self, region, start_date, end_date):
        """Collect GBIF data"""
        return self.gbif.get_species_occurrences(region, start_date, end_date, limit=2000)
    
    def _collect_emodnet_data(self, region):
        """Collect EMODnet Biology data"""
        return self.emodnet.get_species_distribution(region)
    
    def _collect_sst_data(self, region, start_date, end_date):
        """Collect sea surface temperature data"""
        return self.satellite.get_sea_surface_temperature(region, start_date, end_date)
    
    def _collect_chlorophyll_data(self, region, start_date, end_date):
        """Collect chlorophyll data"""
        return self.satellite.get_chlorophyll_data(region, start_date, end_date)
    
    def _collect_argo_data(self, region, start_date, end_date):
        """Collect Argo float data"""
        return self.argo.get_profiles(region, start_date, end_date, limit=1000)
    
    def _collect_buoy_data(self, region):
        """Collect NOAA buoy data"""
        # Get nearby buoy stations (simplified - would need station database)
        sample_stations = ['46050', '46005', '46013', '46022', '46028']
        buoy_data = {}
        
        for station in sample_stations[:3]:  # Limit for demo
            data = self.buoy.get_buoy_data(station)
            if data is not None:
                buoy_data[station] = data
        
        return buoy_data if buoy_data else None
    
    def _collect_woa_data(self, region):
        """Collect World Ocean Atlas climatology"""
        climatology = {}
        variables = ['temperature', 'salinity', 'oxygen']
        
        for var in variables:
            url = self.woa.get_climatology(var, region)
            if url:
                climatology[var] = url
        
        return climatology if climatology else None
    
    def _collect_copernicus_data(self, region, start_date, end_date):
        """Collect Copernicus Marine Service data"""
        try:
            products = self.copernicus.search_products("sea surface temperature ocean color", ["Ocean Physics", "Ocean Biogeochemistry"])
            return products[:5]  # Limit for demo
        except Exception as e:
            logger.error(f"Error collecting Copernicus data: {e}")
            return None
    
    def _collect_glodap_data(self, region):
        """Collect GLODAP carbon cycle data"""
        try:
            stations = self.glodap.get_glodap_stations(region)
            return stations
        except Exception as e:
            logger.error(f"Error collecting GLODAP data: {e}")
            return None
    
    def _collect_socat_data(self, region, start_date, end_date):
        """Collect SOCAT carbon dioxide data"""
        try:
            # Extract year range from dates
            start_year = int(start_date.split('-')[0])
            end_year = int(end_date.split('-')[0])
            
            datasets = self.socat.get_socat_datasets()
            observations = self.socat.get_co2_observations(region, (start_year, end_year))
            return {
                'datasets': datasets,
                'observations': observations
            }
        except Exception as e:
            logger.error(f"Error collecting SOCAT data: {e}")
            return None
    
    def _collect_gfw_data(self, region, start_date, end_date):
        """Collect Global Fishing Watch data"""
        try:
            datasets = self.gfw.get_public_datasets()
            fishing_effort = self.gfw.get_fishing_effort(region, start_date, end_date)
            return {
                'datasets': datasets,
                'fishing_effort': fishing_effort
            }
        except Exception as e:
            logger.error(f"Error collecting GFW data: {e}")
            return None
    
    def _collect_onc_data(self, region, start_date, end_date):
        """Collect Ocean Networks Canada data"""
        try:
            locations = self.onc.get_locations()
            devices = self.onc.get_devices()
            
            # Get real-time data for first location (demo)
            real_time_data = None
            if locations:
                location_code = locations[0]['location_code']
                device_code = 'CTD001'  # Example device
                real_time_data = self.onc.get_real_time_data(
                    location_code, device_code, start_date, end_date
                )
            
            return {
                'locations': locations[:10],  # Limit for demo
                'devices': devices[:20],
                'real_time_sample': real_time_data
            }
        except Exception as e:
            logger.error(f"Error collecting ONC data: {e}")
            return None
    
    def _collect_fishbase_data(self, target_species):
        """Collect FishBase species ecology data"""
        try:
            if not target_species:
                return None
            
            ecology_data = {}
            for species in target_species[:5]:  # Limit for demo
                ecology = self.fishbase.get_species_ecology(species)
                if ecology:
                    ecology_data[species] = ecology
            
            return ecology_data if ecology_data else None
        except Exception as e:
            logger.error(f"Error collecting FishBase data: {e}")
            return None
    
    def _collect_coral_watch_data(self, region):
        """Collect NOAA Coral Reef Watch data"""
        try:
            alerts = self.coral_watch.get_bleaching_alerts(region)
            return alerts
        except Exception as e:
            logger.error(f"Error collecting Coral Reef Watch data: {e}")
            return None
    
    def _collect_vessel_traffic_data(self, region):
        """Collect vessel traffic data"""
        try:
            density_data = self.marine_traffic.get_vessel_density(region)
            return density_data
        except Exception as e:
            logger.error(f"Error collecting vessel traffic data: {e}")
            return None

    def _get_data_category(self, task_name: str) -> str:
        """Determine data category for a task"""
        if any(x in task_name for x in ['occurrence', 'biology', 'fishbase', 'ecology']):
            return 'biodiversity'
        elif any(x in task_name for x in ['sst', 'chlorophyll', 'climatology', 'temperature']):
            return 'environmental'
        elif any(x in task_name for x in ['argo', 'buoy', 'onc', 'physical']):
            return 'physical_oceanography'
        elif any(x in task_name for x in ['glodap', 'socat', 'carbon', 'co2']):
            return 'biogeochemistry'
        elif any(x in task_name for x in ['fishing', 'vessel', 'traffic', 'gfw']):
            return 'human_activities'
        elif any(x in task_name for x in ['coral', 'bleaching', 'conservation']):
            return 'conservation'
        else:
            return 'environmental'
    
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
                elif isinstance(data, dict) and 'data_url' in data:
                    summary['total_records'] += 1
        
        return summary


class CopernicusMarineIngester:
    """Copernicus Marine Environment Monitoring Service (CMEMS) data ingestion"""
    
    def __init__(self, base_url: str = "https://marine.copernicus.eu"):
        self.base_url = base_url
        self.api_url = "https://my.cmems-du.eu/motu-web/Motu"
    
    def search_products(self, keywords: str, themes: List[str] = None) -> List[Dict]:
        """
        Search for available Copernicus Marine products
        
        Args:
            keywords: Search keywords
            themes: List of themes (e.g., 'Ocean Physics', 'Ocean Biogeochemistry')
            
        Returns:
            List of available products
        """
        # Note: This is a simplified example - actual implementation would require
        # Copernicus Marine credentials and proper API integration
        
        sample_products = [
            {
                'product_id': 'GLOBAL_ANALYSIS_FORECAST_PHY_001_024',
                'name': 'Global Ocean Physics Analysis and Forecast',
                'description': 'Daily global ocean physics analysis and forecast',
                'variables': ['sea_water_temperature', 'sea_water_salinity', 'sea_water_velocity'],
                'spatial_resolution': '1/12 degree',
                'temporal_resolution': 'daily',
                'coverage': 'global'
            },
            {
                'product_id': 'GLOBAL_ANALYSIS_FORECAST_BIO_001_028',
                'name': 'Global Ocean Biogeochemistry Analysis and Forecast',
                'description': 'Daily global ocean biogeochemistry analysis and forecast',
                'variables': ['chlorophyll', 'nitrate', 'phosphate', 'dissolved_oxygen'],
                'spatial_resolution': '1/4 degree',
                'temporal_resolution': 'daily',
                'coverage': 'global'
            },
            {
                'product_id': 'SEALEVEL_GLO_PHY_L4_REP_OBSERVATIONS_008_047',
                'name': 'Global Ocean Gridded L4 Sea Surface Heights',
                'description': 'Daily interpolated sea level anomaly',
                'variables': ['sea_surface_height_above_geoid', 'surface_geostrophic_velocity'],
                'spatial_resolution': '1/4 degree',
                'temporal_resolution': 'daily',
                'coverage': 'global'
            },
            {
                'product_id': 'OCEANCOLOUR_GLO_CHL_L4_REP_OBSERVATIONS_009_093',
                'name': 'Global Ocean Colour L4 Chlorophyll',
                'description': 'Daily global chlorophyll-a concentration',
                'variables': ['chlorophyll_concentration'],
                'spatial_resolution': '4 km',
                'temporal_resolution': 'daily',
                'coverage': 'global'
            }
        ]
        
        # Filter by keywords and themes
        filtered_products = []
        for product in sample_products:
            if keywords.lower() in product['name'].lower() or keywords.lower() in product['description'].lower():
                if not themes or any(theme in product.get('themes', []) for theme in themes):
                    filtered_products.append(product)
        
        if not filtered_products:
            # Return all if no matches
            filtered_products = sample_products
        
        logger.info(f"Found {len(filtered_products)} Copernicus Marine products")
        return filtered_products
    
    def get_product_info(self, product_id: str) -> Optional[Dict]:
        """Get detailed information about a specific product"""
        products = self.search_products("")
        for product in products:
            if product['product_id'] == product_id:
                return product
        return None


class GLODAPIngester:
    """Global Ocean Data Analysis Project (GLODAP) data ingestion"""
    
    def __init__(self, base_url: str = "https://www.glodap.info"):
        self.base_url = base_url
        self.data_url = "https://www.ncei.noaa.gov/data/oceans/ncei/ocads/data/0162565"
    
    def get_glodap_stations(self, region: Dict[str, float]) -> List[Dict]:
        """
        Get GLODAP station data for carbon cycle parameters
        
        Args:
            region: Geographic boundaries
            
        Returns:
            List of GLODAP stations with carbon data
        """
        # Sample GLODAP stations (in a real implementation, this would query the actual database)
        sample_stations = [
            {
                'station_id': 'GLODAP_001',
                'latitude': (region['south'] + region['north']) / 2,
                'longitude': (region['west'] + region['east']) / 2,
                'date': '2020-06-15',
                'parameters': {
                    'pH': 8.1,
                    'alkalinity': 2300,  # µmol/kg
                    'dissolved_inorganic_carbon': 2100,  # µmol/kg
                    'partial_pressure_co2': 380,  # µatm
                    'oxygen': 250,  # µmol/kg
                    'nitrate': 15,  # µmol/kg
                    'phosphate': 1.2,  # µmol/kg
                    'silicate': 45  # µmol/kg
                },
                'depth_profile': True,
                'quality_flags': 'good'
            },
            {
                'station_id': 'GLODAP_002',
                'latitude': region['south'] + 0.5,
                'longitude': region['west'] + 0.5,
                'date': '2020-07-20',
                'parameters': {
                    'pH': 7.9,
                    'alkalinity': 2250,
                    'dissolved_inorganic_carbon': 2150,
                    'partial_pressure_co2': 420,
                    'oxygen': 220,
                    'nitrate': 18,
                    'phosphate': 1.5,
                    'silicate': 50
                },
                'depth_profile': True,
                'quality_flags': 'good'
            }
        ]
        
        # Filter stations within region
        filtered_stations = []
        for station in sample_stations:
            lat, lon = station['latitude'], station['longitude']
            if (region['south'] <= lat <= region['north'] and 
                region['west'] <= lon <= region['east']):
                filtered_stations.append(station)
        
        logger.info(f"Found {len(filtered_stations)} GLODAP stations in region")
        return filtered_stations
    
    def download_glodap_data(self, version: str = "v2.2021") -> Optional[str]:
        """Download GLODAP gridded data products"""
        download_url = f"{self.data_url}/GLODAPv2.{version}_Merged_Master_File.csv"
        
        try:
            response = requests.head(download_url, timeout=30)
            if response.status_code == 200:
                logger.info(f"GLODAP {version} data available at: {download_url}")
                return download_url
            else:
                logger.warning(f"GLODAP {version} data not accessible")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error accessing GLODAP data: {e}")
            return None


class SOCATIngester:
    """Surface Ocean CO2 Atlas (SOCAT) data ingestion"""
    
    def __init__(self, base_url: str = "https://www.socat.info"):
        self.base_url = base_url
        self.data_portal = "https://socat.info/index.php/data-access/"
    
    def get_socat_datasets(self) -> List[Dict]:
        """Get available SOCAT datasets"""
        datasets = [
            {
                'dataset_id': 'SOCATv2021',
                'name': 'Surface Ocean CO2 Atlas Version 2021',
                'description': 'Quality-controlled surface ocean CO2 observations',
                'parameters': [
                    'partial_pressure_co2',
                    'sea_surface_temperature',
                    'sea_surface_salinity',
                    'atmospheric_pressure'
                ],
                'temporal_coverage': '1957-2020',
                'spatial_coverage': 'global',
                'data_points': '> 30 million',
                'update_frequency': 'annual'
            },
            {
                'dataset_id': 'SOCAT_coastal',
                'name': 'SOCAT Coastal Ocean Data',
                'description': 'High-resolution coastal CO2 measurements',
                'parameters': [
                    'partial_pressure_co2',
                    'dissolved_co2',
                    'sea_surface_temperature'
                ],
                'temporal_coverage': '2000-2021',
                'spatial_coverage': 'coastal_regions',
                'data_points': '> 5 million',
                'update_frequency': 'quarterly'
            }
        ]
        
        logger.info(f"Available SOCAT datasets: {len(datasets)}")
        return datasets
    
    def get_co2_observations(self, region: Dict[str, float], year_range: Tuple[int, int]) -> List[Dict]:
        """
        Get CO2 observations for a specific region and time period
        
        Args:
            region: Geographic boundaries
            year_range: Tuple of (start_year, end_year)
            
        Returns:
            List of CO2 observation records
        """
        # Sample CO2 observations (real implementation would query SOCAT database)
        observations = []
        
        import random
        np.random.seed(42)  # For reproducible sample data
        
        # Generate sample observations
        for i in range(50):
            lat = np.random.uniform(region['south'], region['north'])
            lon = np.random.uniform(region['west'], region['east'])
            year = np.random.randint(year_range[0], year_range[1] + 1)
            month = np.random.randint(1, 13)
            day = np.random.randint(1, 28)
            
            # Realistic CO2 values (µatm)
            base_co2 = 380 + (year - 2000) * 2.5  # Increasing trend
            seasonal_variation = 10 * np.sin(2 * np.pi * month / 12)
            co2_value = base_co2 + seasonal_variation + np.random.normal(0, 15)
            
            observation = {
                'observation_id': f'SOCAT_{i:04d}',
                'latitude': round(lat, 4),
                'longitude': round(lon, 4),
                'date': f'{year}-{month:02d}-{day:02d}',
                'partial_pressure_co2': round(co2_value, 2),
                'sea_surface_temperature': round(np.random.uniform(5, 30), 2),
                'sea_surface_salinity': round(np.random.uniform(30, 37), 2),
                'platform_type': np.random.choice(['ship', 'buoy', 'drifter']),
                'quality_flag': np.random.choice(['good', 'questionable'], p=[0.9, 0.1])
            }
            observations.append(observation)
        
        logger.info(f"Generated {len(observations)} SOCAT CO2 observations")
        return observations


class GlobalFishingWatchIngester:
    """Global Fishing Watch data ingestion"""
    
    def __init__(self, base_url: str = "https://globalfishingwatch.org"):
        self.base_url = base_url
        self.api_url = "https://gateway.api.globalfishingwatch.org"
    
    def get_public_datasets(self) -> List[Dict]:
        """Get available public datasets from Global Fishing Watch"""
        datasets = [
            {
                'dataset_id': 'public-global-fishing-effort',
                'name': 'Global Fishing Effort',
                'description': 'Daily global fishing effort by gear type',
                'variables': ['fishing_hours', 'vessel_count', 'gear_type'],
                'spatial_resolution': '0.01 degree',
                'temporal_resolution': 'daily',
                'temporal_coverage': '2012-present',
                'access': 'public'
            },
            {
                'dataset_id': 'public-global-apparent-fishing-effort',
                'name': 'Apparent Fishing Effort',
                'description': 'Apparent fishing effort derived from AIS data',
                'variables': ['apparent_fishing_hours'],
                'spatial_resolution': '0.1 degree',
                'temporal_resolution': 'monthly',
                'temporal_coverage': '2012-present',
                'access': 'public'
            },
            {
                'dataset_id': 'public-global-vessels',
                'name': 'Global Vessel Database',
                'description': 'Fishing vessel identities and characteristics',
                'variables': ['vessel_id', 'flag_state', 'gear_type', 'vessel_length'],
                'update_frequency': 'quarterly',
                'access': 'public'
            }
        ]
        
        logger.info(f"Available GFW public datasets: {len(datasets)}")
        return datasets
    
    def get_fishing_effort(
        self, 
        region: Dict[str, float], 
        start_date: str, 
        end_date: str,
        gear_types: List[str] = None
    ) -> List[Dict]:
        """
        Get fishing effort data for a specific region and time period
        
        Args:
            region: Geographic boundaries
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            gear_types: Optional list of gear types to filter
            
        Returns:
            List of fishing effort records
        """
        # Sample fishing effort data (real implementation would use GFW API)
        effort_data = []
        
        gear_types = gear_types or ['trawlers', 'longliners', 'purse_seines', 'pole_and_line']
        
        # Generate sample data for demonstration
        from datetime import datetime, timedelta
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        current_date = start
        while current_date <= end:
            for gear in gear_types:
                # Random fishing effort within region
                lat_center = (region['south'] + region['north']) / 2
                lon_center = (region['west'] + region['east']) / 2
                
                effort_record = {
                    'date': current_date.strftime('%Y-%m-%d'),
                    'gear_type': gear,
                    'latitude': lat_center + np.random.uniform(-1, 1),
                    'longitude': lon_center + np.random.uniform(-1, 1),
                    'fishing_hours': round(np.random.exponential(5), 2),
                    'vessel_count': np.random.poisson(3),
                    'grid_cell': f"{lat_center:.1f}_{lon_center:.1f}",
                    'flag_states': ['ESP', 'PRT', 'FRA', 'JPN', 'CHN']  # Sample flags
                }
                effort_data.append(effort_record)
            
            current_date += timedelta(days=7)  # Weekly data
        
        logger.info(f"Generated {len(effort_data)} fishing effort records")
        return effort_data


class OceanNetworksCanadaIngester:
    """Ocean Networks Canada (ONC) data ingestion"""
    
    def __init__(self, base_url: str = "https://data.oceannetworks.ca"):
        self.base_url = base_url
        self.api_url = "https://data.oceannetworks.ca/api"
    
    def get_locations(self) -> List[Dict]:
        """Get ONC observatory locations"""
        # Sample ONC locations (real implementation would use ONC API with token)
        locations = [
            {
                'location_code': 'BACAX',
                'location_name': 'Barkley Canyon Axis',
                'latitude': 48.316,
                'longitude': -126.050,
                'depth': 850,
                'region': 'Northeast Pacific',
                'description': 'Deep-sea observatory with seismic monitoring',
                'instruments': ['seismometer', 'CTD', 'current_meter']
            },
            {
                'location_code': 'SEVIP',
                'location_name': 'Saanich Inlet Vertical Profiler',
                'latitude': 48.590,
                'longitude': -123.505,
                'depth': 95,
                'region': 'Saanich Inlet',
                'description': 'Automated vertical profiling system',
                'instruments': ['CTD', 'dissolved_oxygen', 'fluorometer']
            },
            {
                'location_code': 'FRHYD',
                'location_name': 'Folger Ridge Hydrothermal',
                'latitude': 48.785,
                'longitude': -129.095,
                'depth': 1300,
                'region': 'Juan de Fuca Ridge',
                'description': 'Hydrothermal vent observatory',
                'instruments': ['temperature', 'pressure', 'camera']
            }
        ]
        
        logger.info(f"Retrieved {len(locations)} ONC locations")
        return locations
    
    def get_devices(self) -> List[Dict]:
        """Get available devices and instruments"""
        devices = [
            {
                'device_id': 'CTD001',
                'device_name': 'Sea-Bird SBE 37-SMP MicroCAT',
                'device_type': 'CTD',
                'parameters': ['temperature', 'conductivity', 'pressure', 'salinity'],
                'sampling_rate': '1 Hz',
                'location': 'BACAX',
                'status': 'active'
            },
            {
                'device_id': 'ADCP002',
                'device_name': 'Teledyne RDI ADCP',
                'device_type': 'Current Meter',
                'parameters': ['current_velocity', 'current_direction'],
                'sampling_rate': '0.5 Hz',
                'location': 'SEVIP',
                'status': 'active'
            },
            {
                'device_id': 'CAM003',
                'device_name': 'HD IP Camera',
                'device_type': 'Camera',
                'parameters': ['video', 'still_images'],
                'sampling_rate': 'continuous',
                'location': 'FRHYD',
                'status': 'active'
            }
        ]
        
        logger.info(f"Retrieved {len(devices)} ONC devices")
        return devices
    
    def get_real_time_data(
        self, 
        location_code: str, 
        device_code: str,
        start_time: str,
        end_time: str
    ) -> Optional[Dict]:
        """
        Get real-time data from ONC instruments
        
        Args:
            location_code: ONC location code
            device_code: Device/instrument code
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            
        Returns:
            Dictionary containing time series data
        """
        # Sample real-time data (real implementation requires ONC API token)
        sample_data = {
            'location': location_code,
            'device': device_code,
            'parameters': {
                'temperature': [12.5, 12.3, 12.7, 12.4, 12.6],
                'salinity': [33.2, 33.1, 33.3, 33.0, 33.2],
                'depth': [850, 850, 850, 850, 850]
            },
            'timestamps': [
                start_time,
                '2024-01-01T12:15:00Z',
                '2024-01-01T12:30:00Z',
                '2024-01-01T12:45:00Z',
                end_time
            ],
            'quality_flags': ['good', 'good', 'good', 'good', 'good'],
            'units': {
                'temperature': 'degrees_celsius',
                'salinity': 'psu',
                'depth': 'meters'
            }
        }
        
        logger.info(f"Retrieved real-time data for {location_code}/{device_code}")
        return sample_data


class MarineTrafficIngester:
    """Marine Traffic data for vessel monitoring and shipping patterns"""
    
    def __init__(self, base_url: str = "https://www.marinetraffic.com"):
        self.base_url = base_url
    
    def get_vessel_density(self, region: Dict[str, float]) -> List[Dict]:
        """Get vessel density data for environmental impact assessment"""
        # Sample vessel density data
        density_data = []
        
        # Generate grid of vessel density
        lat_step = (region['north'] - region['south']) / 10
        lon_step = (region['east'] - region['west']) / 10
        
        for i in range(10):
            for j in range(10):
                lat = region['south'] + i * lat_step
                lon = region['west'] + j * lon_step
                
                # Simulate higher density near coasts and shipping lanes
                distance_to_center = np.sqrt((lat - (region['south'] + region['north'])/2)**2 + 
                                           (lon - (region['west'] + region['east'])/2)**2)
                density = max(0, 100 - distance_to_center * 50 + np.random.normal(0, 10))
                
                density_data.append({
                    'latitude': round(lat, 3),
                    'longitude': round(lon, 3),
                    'vessel_count': max(0, int(density)),
                    'vessel_types': ['cargo', 'tanker', 'fishing', 'passenger'],
                    'grid_id': f"{i}_{j}"
                })
        
        logger.info(f"Generated vessel density data for {len(density_data)} grid cells")
        return density_data


class NOAACoralReefWatchIngester:
    """NOAA Coral Reef Watch satellite monitoring data"""
    
    def __init__(self, base_url: str = "https://coralreefwatch.noaa.gov"):
        self.base_url = base_url
        self.data_url = "https://coastwatch.pfeg.noaa.gov/erddap"
    
    def get_bleaching_alerts(self, region: Dict[str, float]) -> List[Dict]:
        """Get coral bleaching alert data"""
        # Sample coral bleaching alert data
        alerts = [
            {
                'alert_id': 'CRW_001',
                'latitude': (region['south'] + region['north']) / 2,
                'longitude': (region['west'] + region['east']) / 2,
                'alert_level': 'Watch',
                'date': '2024-07-15',
                'sea_surface_temperature': 29.5,
                'temperature_anomaly': 2.1,
                'degree_heating_weeks': 4.2,
                'bleaching_probability': 'high',
                'reef_location': 'Sample Reef System'
            },
            {
                'alert_id': 'CRW_002',
                'latitude': region['south'] + 0.5,
                'longitude': region['west'] + 0.5,
                'alert_level': 'Warning',
                'date': '2024-07-20',
                'sea_surface_temperature': 30.2,
                'temperature_anomaly': 2.8,
                'degree_heating_weeks': 6.1,
                'bleaching_probability': 'very_high',
                'reef_location': 'Another Reef System'
            }
        ]
        
        logger.info(f"Retrieved {len(alerts)} coral bleaching alerts")
        return alerts


class FishBaseIngester:
    """FishBase species information and ecology data"""
    
    def __init__(self, base_url: str = "https://fishbase.org"):
        self.base_url = base_url
    
    def get_species_ecology(self, species_name: str) -> Optional[Dict]:
        """Get ecological information for fish species"""
        # Sample species ecology data
        sample_ecology = {
            'species_name': species_name,
            'common_name': 'Sample Fish',
            'family': 'Sampleidae',
            'habitat': 'reef-associated',
            'depth_range': {'min': 1, 'max': 50},
            'temperature_range': {'min': 20, 'max': 28},
            'diet': 'omnivore',
            'reproduction': 'oviparous',
            'conservation_status': 'least_concern',
            'commercial_importance': 'minor',
            'trophic_level': 3.2,
            'length_max': 25.0,
            'age_max': 8,
            'vulnerability': 'low'
        }
        
        logger.info(f"Retrieved ecology data for {species_name}")
        return sample_ecology
