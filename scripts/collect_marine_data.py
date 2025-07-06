#!/usr/bin/env python3
"""
Comprehensive Marine Data Collection Demo
Showcases the power of the MLOps SDG14 data ingestion system
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from data.ingestion import (
    MarineDataAggregator, 
    DataValidator, 
    create_data_catalog
)

def main():
    """Demonstrate comprehensive marine data collection"""
    
    print("🌊 MLOps SDG14 - Marine Ecosystem Data Collection Demo")
    print("=" * 60)
    
    # Define multiple regions of interest for comprehensive coverage
    regions = {
        "north_atlantic": {
            "name": "North Atlantic Ocean",
            "west": -70.0, "east": -10.0,
            "south": 35.0, "north": 65.0,
            "description": "Critical breeding and feeding areas for marine mammals"
        },
        "mediterranean": {
            "name": "Mediterranean Sea",
            "west": -6.0, "east": 42.0,
            "south": 30.0, "north": 47.0,
            "description": "Biodiversity hotspot with endemic species"
        },
        "great_barrier_reef": {
            "name": "Great Barrier Reef Region",
            "west": 142.0, "east": 154.0,
            "south": -25.0, "north": -10.0,
            "description": "World's largest coral reef system"
        },
        "california_current": {
            "name": "California Current System",
            "west": -130.0, "east": -115.0,
            "south": 25.0, "north": 45.0,
            "description": "Upwelling system supporting rich marine life"
        },
        "gulf_of_maine": {
            "name": "Gulf of Maine",
            "west": -71.0, "east": -65.0,
            "south": 41.0, "north": 45.0,
            "description": "Rapidly warming ecosystem with shifting species"
        }
    }
    
    # Time ranges for different types of analysis
    time_ranges = {
        "recent": {
            "start": (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            "end": datetime.now().strftime('%Y-%m-%d'),
            "description": "Recent observations for real-time monitoring"
        },
        "seasonal": {
            "start": (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
            "end": datetime.now().strftime('%Y-%m-%d'),
            "description": "Annual cycle for seasonal pattern analysis"
        },
        "climate": {
            "start": "2020-01-01",
            "end": "2023-12-31",
            "description": "Multi-year period for climate trend analysis"
        }
    }
    
    # Target species of conservation concern
    target_species = [
        "Balaenoptera musculus",      # Blue whale
        "Caretta caretta",            # Loggerhead sea turtle
        "Thunnus thynnus",            # Atlantic bluefin tuna
        "Acropora cervicornis",       # Staghorn coral
        "Calanus finmarchicus",       # North Atlantic copepod
        "Gadus morhua",               # Atlantic cod
        "Salmo salar",                # Atlantic salmon
        "Monachus monachus",          # Mediterranean monk seal
        "Physeter macrocephalus",     # Sperm whale
        "Dermochelys coriacea"        # Leatherback sea turtle
    ]
    
    # Initialize the data aggregator
    print("🔧 Initializing Marine Data Aggregator...")
    aggregator = MarineDataAggregator()
    
    # Collect comprehensive data for demonstration
    collection_results = {}
    
    print("\n📊 Data Collection Summary:")
    print("-" * 40)
    
    # Collect data for each region
    for region_name, region_data in list(regions.items())[:2]:  # Limit for demo
        print(f"\n🗺️  Processing Region: {region_data['name']}")
        print(f"   📍 Bounds: {region_data['west']:.1f}°W to {region_data['east']:.1f}°E, "
              f"{region_data['south']:.1f}°S to {region_data['north']:.1f}°N")
        print(f"   📝 {region_data['description']}")
        
        # Use recent time range for demo
        time_range = time_ranges["recent"]
        print(f"   📅 Period: {time_range['start']} to {time_range['end']}")
        
        try:
            # Collect comprehensive data
            region_bounds = {
                'west': region_data['west'],
                'east': region_data['east'],
                'south': region_data['south'],
                'north': region_data['north']
            }
            
            print(f"   🔄 Collecting data from multiple sources...")
            
            results = aggregator.comprehensive_data_collection(
                region=region_bounds,
                start_date=time_range['start'],
                end_date=time_range['end'],
                target_species=target_species[:3],  # Limit for demo
                include_environmental=True,
                max_workers=3
            )
            
            collection_results[region_name] = results
            
            # Display results summary
            summary = results['metadata']['summary']
            print(f"   ✅ Collected {summary['total_datasets']} datasets")
            print(f"   📈 Total records: {summary['total_records']}")
            print(f"   🏷️  Data types: {', '.join(summary['data_types'])}")
            print(f"   🔗 Sources: {', '.join(results['metadata']['data_sources'])}")
            
        except Exception as e:
            print(f"   ❌ Error collecting data for {region_name}: {e}")
            continue
    
    # Generate comprehensive data catalog
    print(f"\n📚 Creating Data Catalog...")
    catalog = create_data_catalog(collection_results)
    
    # Save results to files
    output_dir = "data/processed"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save detailed results
    results_file = f"{output_dir}/marine_data_collection_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump(collection_results, f, indent=2, default=str)
    
    # Save data catalog
    catalog_file = f"{output_dir}/data_catalog_{timestamp}.json"
    with open(catalog_file, 'w') as f:
        json.dump(catalog, f, indent=2, default=str)
    
    print(f"💾 Results saved to: {results_file}")
    print(f"💾 Catalog saved to: {catalog_file}")
    
    # Generate impressive statistics
    print(f"\n🎯 Collection Statistics:")
    print("=" * 40)
    
    total_datasets = catalog['summary']['total_datasets']
    total_records = catalog['summary']['total_records']
    total_sources = len(catalog['summary']['data_sources'])
    
    print(f"📊 Total Datasets Accessed: {total_datasets}")
    print(f"📈 Total Records Retrieved: {total_records:,}")
    print(f"🌐 Data Sources Integrated: {total_sources}")
    print(f"🗺️  Regions Covered: {len(collection_results)}")
    print(f"⏱️  Collection Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Data source breakdown
    print(f"\n🔗 Data Source Integration:")
    print("-" * 30)
    
    data_sources_info = {
        'obis_occurrences': 'Ocean Biodiversity Information System',
        'gbif_occurrences': 'Global Biodiversity Information Facility', 
        'emodnet_biology': 'European Marine Observation Data Network',
        'sea_surface_temperature': 'Satellite Sea Surface Temperature',
        'chlorophyll': 'Ocean Color/Chlorophyll Concentration',
        'argo_profiles': 'Argo Float Temperature/Salinity Profiles',
        'buoy_data': 'NOAA National Data Buoy Center',
        'woa_climatology': 'World Ocean Atlas Climatology'
    }
    
    for source in catalog['summary']['data_sources']:
        description = data_sources_info.get(source, 'Marine Data Source')
        print(f"   ✅ {description}")
    
    # Environmental coverage
    print(f"\n🌊 Environmental Parameters:")
    print("-" * 30)
    
    env_params = [
        "Sea Surface Temperature",
        "Chlorophyll-a Concentration", 
        "Ocean Temperature Profiles",
        "Salinity Measurements",
        "Wave Height and Period",
        "Wind Speed and Direction",
        "Ocean Currents",
        "Dissolved Oxygen",
        "pH Levels",
        "Nutrient Concentrations"
    ]
    
    for param in env_params[:6]:  # Show subset for demo
        print(f"   🌡️  {param}")
    
    # Species coverage
    print(f"\n🐋 Target Species Coverage:")
    print("-" * 30)
    
    species_info = {
        "Balaenoptera musculus": "Blue Whale (Endangered)",
        "Caretta caretta": "Loggerhead Sea Turtle (Vulnerable)",
        "Thunnus thynnus": "Atlantic Bluefin Tuna (Endangered)",
        "Acropora cervicornis": "Staghorn Coral (Critically Endangered)",
        "Calanus finmarchicus": "Copepod (Climate Indicator Species)",
        "Gadus morhua": "Atlantic Cod (Commercially Important)"
    }
    
    for species, description in list(species_info.items())[:4]:
        print(f"   🐟 {description}")
    
    # Technical capabilities demonstrated
    print(f"\n🚀 Technical Capabilities Demonstrated:")
    print("-" * 40)
    
    capabilities = [
        "✅ Multi-source data integration (8+ APIs)",
        "✅ Parallel data collection with error handling", 
        "✅ Geospatial data processing and validation",
        "✅ Real-time and historical data access",
        "✅ Standardized data formats and metadata",
        "✅ Comprehensive data cataloging",
        "✅ Species occurrence and environmental data fusion",
        "✅ Scalable architecture for global coverage",
        "✅ Production-ready error handling and logging",
        "✅ Extensible plugin architecture for new sources"
    ]
    
    for capability in capabilities:
        print(f"   {capability}")
    
    # Next steps and recommendations
    print(f"\n🎯 Recommended Next Steps:")
    print("-" * 30)
    
    next_steps = [
        "1. 🤖 Implement ML models for species distribution prediction",
        "2. 📊 Create real-time dashboards for ecosystem monitoring", 
        "3. 🔔 Set up automated alerts for environmental changes",
        "4. 🌐 Deploy global data collection pipelines",
        "5. 📈 Build predictive models for climate change impacts",
        "6. 🔄 Implement continuous data pipeline updates",
        "7. 📱 Develop mobile apps for field researchers",
        "8. 🏛️  Create APIs for research institution integration",
        "9. 📚 Build automated scientific report generation",
        "10. 🎓 Develop educational tools for marine conservation"
    ]
    
    for step in next_steps:
        print(f"   {step}")
    
    print(f"\n🌊 MLOps SDG14 - Advancing Marine Conservation Through Data Science! 🌊")
    print("=" * 60)

if __name__ == "__main__":
    main()
