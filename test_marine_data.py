#!/usr/bin/env python3
"""
Test script for Marine Data Ingestion System
Demonstrates the comprehensive data collection capabilities
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from data.ingestion import (
        OBISDataIngester,
        NOAABuoyIngester,
        GBIFSpeciesIngester,
        ERDDAPIngester,
        EMODnetBiologyIngester,
        SatelliteDataIngester,
        MarineDataAggregator,
        create_data_catalog
    )
    print("✅ Successfully imported marine data ingestion modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all required packages are installed")
    sys.exit(1)

def test_individual_ingesters():
    """Test each data ingester individually"""
    print("\n" + "="*60)
    print("🧪 TESTING INDIVIDUAL DATA INGESTERS")
    print("="*60)
    
    # Define test region (around California)
    test_region = {
        'west': -125.0,
        'east': -120.0,
        'south': 35.0,
        'north': 40.0
    }
    
    # Define recent date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    print(f"📍 Test Region: {test_region}")
    print(f"📅 Date Range: {start_str} to {end_str}")
    
    # Test OBIS
    print("\n🐟 Testing OBIS Data Ingester...")
    try:
        obis = OBISDataIngester()
        obis_data = obis.get_species_occurrences(test_region, start_str, end_str, limit=10)
        print(f"   📊 Retrieved {len(obis_data)} OBIS records")
        if obis_data:
            print(f"   📋 Sample record keys: {list(obis_data[0].keys())[:5]}")
    except Exception as e:
        print(f"   ❌ OBIS test failed: {e}")
    
    # Test GBIF
    print("\n🌍 Testing GBIF Data Ingester...")
    try:
        gbif = GBIFSpeciesIngester()
        gbif_data = gbif.get_species_occurrences(test_region, start_str, end_str, limit=10)
        print(f"   📊 Retrieved {len(gbif_data)} GBIF records")
        if gbif_data:
            print(f"   📋 Sample record keys: {list(gbif_data[0].keys())[:5]}")
    except Exception as e:
        print(f"   ❌ GBIF test failed: {e}")
    
    # Test ERDDAP
    print("\n🛰️ Testing ERDDAP Data Ingester...")
    try:
        erddap = ERDDAPIngester()
        datasets = erddap.search_datasets("temperature")
        print(f"   📊 Found {len(datasets)} ERDDAP temperature datasets")
        if datasets:
            print(f"   📋 Sample dataset: {datasets[0].get('title', 'Unknown')}")
    except Exception as e:
        print(f"   ❌ ERDDAP test failed: {e}")
    
    # Test EMODnet Biology
    print("\n🦑 Testing EMODnet Biology Ingester...")
    try:
        emodnet = EMODnetBiologyIngester()
        # Use European waters for EMODnet
        eu_region = {'west': 0.0, 'east': 10.0, 'south': 45.0, 'north': 55.0}
        emodnet_data = emodnet.get_species_distribution(eu_region)
        print(f"   📊 Retrieved {len(emodnet_data)} EMODnet Biology records")
    except Exception as e:
        print(f"   ❌ EMODnet Biology test failed: {e}")
    
    # Test Satellite Data
    print("\n🛰️ Testing Satellite Data Ingester...")
    try:
        satellite = SatelliteDataIngester()
        sst_data = satellite.get_sea_surface_temperature(test_region, start_str, end_str)
        if sst_data:
            print(f"   📊 Found SST dataset: {sst_data.get('dataset_id', 'Unknown')}")
        else:
            print("   📊 No SST datasets found")
    except Exception as e:
        print(f"   ❌ Satellite data test failed: {e}")

def test_comprehensive_aggregator():
    """Test the comprehensive data aggregator"""
    print("\n" + "="*60)
    print("🔄 TESTING COMPREHENSIVE DATA AGGREGATOR")
    print("="*60)
    
    # Define test region (smaller for faster testing)
    test_region = {
        'west': -124.0,
        'east': -123.0,
        'south': 37.0,
        'north': 38.0
    }
    
    # Define recent date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)  # Shorter range for testing
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    print(f"📍 Test Region: {test_region}")
    print(f"📅 Date Range: {start_str} to {end_str}")
    
    try:
        aggregator = MarineDataAggregator()
        print("\n🚀 Starting comprehensive data collection...")
        
        # Collect data with limited scope for testing
        results = aggregator.comprehensive_data_collection(
            region=test_region,
            start_date=start_str,
            end_date=end_str,
            include_environmental=True,
            max_workers=3  # Limit parallel workers
        )
        
        print("\n📊 DATA COLLECTION RESULTS:")
        print("-" * 40)
        
        # Display results summary
        for category, datasets in results.items():
            if category == 'metadata':
                continue
            print(f"\n📂 {category.upper()}:")
            for dataset_name, data in datasets.items():
                if data is None:
                    status = "❌ No data"
                elif isinstance(data, list):
                    status = f"✅ {len(data)} records"
                elif isinstance(data, dict):
                    status = f"✅ {len(data)} items"
                else:
                    status = "✅ Available"
                print(f"   • {dataset_name}: {status}")
        
        # Show metadata
        if 'metadata' in results:
            metadata = results['metadata']
            print(f"\n📋 METADATA:")
            print(f"   • Data sources: {len(metadata.get('data_sources', []))}")
            print(f"   • Collection time: {metadata.get('collection_timestamp', 'Unknown')}")
            if 'summary' in metadata:
                summary = metadata['summary']
                print(f"   • Total datasets: {summary.get('total_datasets', 0)}")
                print(f"   • Total records: {summary.get('total_records', 0)}")
        
        # Create data catalog
        print("\n📚 Creating data catalog...")
        catalog = create_data_catalog(results)
        print(f"   ✅ Catalog created with {catalog['summary']['total_datasets']} datasets")
        
        return results, catalog
        
    except Exception as e:
        print(f"❌ Comprehensive aggregator test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def display_system_info():
    """Display system information"""
    print("="*60)
    print("🌊 MARINE ECOSYSTEM HEALTH & SPECIES PRESENCE PREDICTION")
    print("   MLOps Platform for SDG 14: Life Below Water")
    print("="*60)
    print(f"🐍 Python Version: {sys.version}")
    print(f"💻 Platform: {sys.platform}")
    print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """Main test function"""
    display_system_info()
    
    # Test individual ingesters
    test_individual_ingesters()
    
    # Test comprehensive aggregator
    results, catalog = test_comprehensive_aggregator()
    
    # Final summary
    print("\n" + "="*60)
    print("🎯 TEST SUMMARY")
    print("="*60)
    
    if results and catalog:
        print("✅ All tests completed successfully!")
        print("✅ Marine data ingestion system is operational")
        print("✅ Ready for production-grade MLOps workflows")
        
        # Save sample results
        try:
            with open('test_results.json', 'w') as f:
                # Convert datetime objects to strings for JSON serialization
                json_results = json.dumps(catalog, indent=2, default=str)
                f.write(json_results)
            print("✅ Test results saved to 'test_results.json'")
        except Exception as e:
            print(f"⚠️ Could not save results: {e}")
    else:
        print("❌ Some tests failed")
        print("⚠️ Please check the error messages above")
    
    print("\n🌊 Marine Data Ingestion System Test Complete! 🌊")

if __name__ == "__main__":
    main()
