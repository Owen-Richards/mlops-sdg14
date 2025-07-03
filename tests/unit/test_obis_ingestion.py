"""
Unit tests for OBIS data ingestion
"""

import pytest
import requests_mock
from unittest.mock import Mock, patch
from src.data.ingestion import OBISDataIngester, DataValidator


class TestOBISDataIngester:
    """Test suite for OBIS data ingestion"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.ingester = OBISDataIngester()
        self.test_region = {
            'west': -150.0,
            'east': -120.0,
            'south': 20.0,
            'north': 50.0
        }
        self.start_date = '2023-01-01'
        self.end_date = '2023-12-31'
    
    def test_init(self):
        """Test ingester initialization"""
        assert self.ingester.base_url == "https://api.obis.org/v3"
        
        # Test custom base URL
        custom_ingester = OBISDataIngester("https://custom.api.url")
        assert custom_ingester.base_url == "https://custom.api.url"
    
    @requests_mock.Mocker()
    def test_get_species_occurrences_success(self, m):
        """Test successful species occurrence retrieval"""
        # Mock response data
        mock_response = {
            'results': [
                {
                    'species': 'Thunnus albacares',
                    'decimalLatitude': 30.5,
                    'decimalLongitude': -140.2,
                    'eventDate': '2023-06-15'
                },
                {
                    'species': 'Delphinus delphis',
                    'decimalLatitude': 35.8,
                    'decimalLongitude': -125.3,
                    'eventDate': '2023-07-20'
                }
            ]
        }
        
        # Mock the API endpoint
        m.get(requests_mock.ANY, json=mock_response)
        
        # Call the method
        result = self.ingester.get_species_occurrences(
            self.test_region, 
            self.start_date, 
            self.end_date,
            limit=1000
        )
        
        # Assertions
        assert len(result) == 2
        assert result[0]['species'] == 'Thunnus albacares'
        assert result[1]['species'] == 'Delphinus delphis'
        
        # Verify the request was made correctly
        assert m.call_count == 1
        request = m.request_history[0]
        assert 'geometry' in request.qs
        assert 'startdate' in request.qs
        assert 'enddate' in request.qs
        assert 'size' in request.qs
    
    @requests_mock.Mocker()
    def test_get_species_occurrences_api_error(self, m):
        """Test API error handling"""
        # Mock API error
        m.get(requests_mock.ANY, status_code=500)
        
        # Call the method
        result = self.ingester.get_species_occurrences(
            self.test_region, 
            self.start_date, 
            self.end_date
        )
        
        # Should return empty list on error
        assert result == []
    
    @requests_mock.Mocker()
    def test_get_species_occurrences_timeout(self, m):
        """Test timeout handling"""
        # Mock timeout
        m.get(requests_mock.ANY, exc=requests.exceptions.Timeout)
        
        # Call the method
        result = self.ingester.get_species_occurrences(
            self.test_region, 
            self.start_date, 
            self.end_date
        )
        
        # Should return empty list on timeout
        assert result == []
    
    def test_polygon_geometry_construction(self):
        """Test that polygon geometry is constructed correctly"""
        with requests_mock.Mocker() as m:
            m.get(requests_mock.ANY, json={'results': []})
            
            self.ingester.get_species_occurrences(
                self.test_region, 
                self.start_date, 
                self.end_date
            )
            
            request = m.request_history[0]
            geometry = request.qs['geometry'][0]
            
            # Check that polygon includes all corners
            assert str(self.test_region['west']) in geometry
            assert str(self.test_region['east']) in geometry
            assert str(self.test_region['south']) in geometry
            assert str(self.test_region['north']) in geometry
            assert 'POLYGON' in geometry


class TestDataValidator:
    """Test suite for data validation utilities"""
    
    def test_validate_coordinates_valid(self):
        """Test valid coordinate validation"""
        assert DataValidator.validate_coordinates(45.0, -120.0) == True
        assert DataValidator.validate_coordinates(0.0, 0.0) == True
        assert DataValidator.validate_coordinates(-90.0, -180.0) == True
        assert DataValidator.validate_coordinates(90.0, 180.0) == True
    
    def test_validate_coordinates_invalid(self):
        """Test invalid coordinate validation"""
        # Invalid latitude
        assert DataValidator.validate_coordinates(91.0, 0.0) == False
        assert DataValidator.validate_coordinates(-91.0, 0.0) == False
        
        # Invalid longitude
        assert DataValidator.validate_coordinates(0.0, 181.0) == False
        assert DataValidator.validate_coordinates(0.0, -181.0) == False
        
        # Both invalid
        assert DataValidator.validate_coordinates(100.0, 200.0) == False
    
    def test_validate_date_range_valid(self):
        """Test valid date range validation"""
        assert DataValidator.validate_date_range('2023-01-01', '2023-12-31') == True
        assert DataValidator.validate_date_range('2023-06-15', '2023-06-15') == True
    
    def test_validate_date_range_invalid(self):
        """Test invalid date range validation"""
        # End date before start date
        assert DataValidator.validate_date_range('2023-12-31', '2023-01-01') == False
        
        # Invalid date format
        assert DataValidator.validate_date_range('invalid-date', '2023-12-31') == False
        assert DataValidator.validate_date_range('2023-01-01', 'invalid-date') == False
    
    def test_validate_species_record_valid(self):
        """Test valid species record validation"""
        valid_record = {
            'species': 'Thunnus albacares',
            'decimalLatitude': 30.5,
            'decimalLongitude': -140.2,
            'eventDate': '2023-06-15'
        }
        assert DataValidator.validate_species_record(valid_record) == True
    
    def test_validate_species_record_invalid(self):
        """Test invalid species record validation"""
        # Missing required fields
        invalid_record1 = {
            'species': 'Thunnus albacares',
            'decimalLatitude': 30.5
            # Missing decimalLongitude
        }
        assert DataValidator.validate_species_record(invalid_record1) == False
        
        # Empty record
        assert DataValidator.validate_species_record({}) == False


@pytest.fixture
def sample_species_data():
    """Fixture providing sample species occurrence data"""
    return [
        {
            'species': 'Thunnus albacares',
            'decimalLatitude': 30.5,
            'decimalLongitude': -140.2,
            'eventDate': '2023-06-15',
            'basisOfRecord': 'OBSERVATION'
        },
        {
            'species': 'Delphinus delphis',
            'decimalLatitude': 35.8,
            'decimalLongitude': -125.3,
            'eventDate': '2023-07-20',
            'basisOfRecord': 'OBSERVATION'
        }
    ]


def test_obis_integration(sample_species_data):
    """Integration test for OBIS data processing"""
    # Test that we can process the sample data
    for record in sample_species_data:
        assert DataValidator.validate_species_record(record)
        assert DataValidator.validate_coordinates(
            record['decimalLatitude'], 
            record['decimalLongitude']
        )
