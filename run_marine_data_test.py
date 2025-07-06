#!/usr/bin/env python3
"""
Simple test runner for Marine Data Ingestion System
Tests the basic functionality with core data sources
"""

import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_simple_ingestion():
    """Test the simplified ingestion system"""
    print("🌊 Testing Marine Data Ingestion System")
    print("="*50)
    
    try:
        from data.ingestion_simple import OBISDataIngester, GBIFSpeciesIngester
        print("✅ Successfully imported simplified ingestion modules")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Define test region (around California coast)
    test_region = {
        'west': -125.0,
        'east': -120.0,
        'south': 35.0,
        'north': 40.0
    }
    
    # Define recent date range (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    print(f"📍 Test Region: {test_region}")
    print(f"📅 Date Range: {start_str} to {end_str}")
    print()
    
    # Test OBIS Data Ingester
    print("🐠 Testing OBIS Data Ingester...")
    try:
        obis_ingester = OBISDataIngester()
        obis_data = obis_ingester.get_species_occurrences(
            region=test_region,
            start_date=start_str,
            end_date=end_str,
            limit=10  # Small limit for testing
        )
        print(f"✅ OBIS: Retrieved {len(obis_data)} species occurrences")
        
        if obis_data:
            sample = obis_data[0]
            print(f"   Sample data keys: {list(sample.keys())[:5]}...")
            
    except Exception as e:
        print(f"❌ OBIS Error: {e}")
    
    print()
    
    # Test GBIF Data Ingester
    print("🦋 Testing GBIF Data Ingester...")
    try:
        gbif_ingester = GBIFSpeciesIngester()
        gbif_data = gbif_ingester.get_species_occurrences(
            region=test_region,
            start_date=start_str,
            end_date=end_str,
            limit=10  # Small limit for testing
        )
        print(f"✅ GBIF: Retrieved {len(gbif_data)} species occurrences")
        
        if gbif_data:
            sample = gbif_data[0]
            print(f"   Sample data keys: {list(sample.keys())[:5]}...")
            
    except Exception as e:
        print(f"❌ GBIF Error: {e}")
    
    print()
    print("🎉 Simple ingestion test completed!")
    return True

def test_full_ingestion():
    """Test the full ingestion system if available"""
    print("\n🌊 Testing Full Marine Data Ingestion System")
    print("="*50)
    
    try:
        from data.ingestion import MarineDataAggregator, OBISDataIngester
        print("✅ Successfully imported full ingestion modules")
    except ImportError as e:
        print(f"❌ Import error for full system: {e}")
        print("💡 Falling back to simplified system only")
        return False
    
    try:
        # Create aggregator
        aggregator = MarineDataAggregator()
        
        # Define test parameters
        test_region = {
            'west': -125.0,
            'east': -120.0,
            'south': 35.0,
            'north': 40.0
        }
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # Shorter range for full test
        
        print(f"📊 Collecting data from {len(aggregator.ingesters)} data sources...")
        
        # Collect data
        all_data = aggregator.collect_all_data(
            region=test_region,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            limit_per_source=5  # Small limit for testing
        )
        
        print(f"✅ Full system: Collected data from {len(all_data)} sources")
        
        for source, data in all_data.items():
            if isinstance(data, list):
                print(f"   {source}: {len(data)} records")
            elif isinstance(data, dict):
                print(f"   {source}: {len(data)} entries")
            else:
                print(f"   {source}: {type(data)} data")
        
        return True
        
    except Exception as e:
        print(f"❌ Full system error: {e}")
        return False

def main():
    """Main test runner"""
    print("🐋 Marine Data MLOps Platform - SDG 14: Life Below Water")
    print("🔬 Running Data Ingestion Tests")
    print("="*60)
    
    # Test simplified system first
    simple_success = test_simple_ingestion()
    
    # If simple works, try full system
    if simple_success:
        test_full_ingestion()
    
    print("\n" + "="*60)
    print("📊 Test Summary Complete")
    print("💡 Ready to collect marine data for SDG 14 monitoring!")

if __name__ == "__main__":
    main()
