# Marine Ecosystem Health & Species Presence Prediction Platform

## 🌊 SDG 14: Life Below Water - MLOps Project

A production-grade MLOps platform for predicting marine ecosystem health and species presence using satellite imagery, ocean physics data, and in-situ sensor measurements.

## Project Overview

This platform combines multiple data sources to predict:
- Marine species presence and distribution
- Sea surface temperature forecasts
- Ecosystem health indicators
- Early warning for harmful algal blooms

## Architecture

```
Data Sources → Ingestion → Feature Store → Training → Model Serving → Monitoring
```

### Data Sources
- **Satellite Imagery**: Sentinel-2/3, MODIS chlorophyll & turbidity
- **Ocean Physics**: NOAA OSTIA SST, CMEMS currents/salinity
- **In-situ Sensors**: Argo floats, NOAA Buoy network
- **Species Data**: OBIS API, iNaturalist exports
- **Bathymetry**: SRTM30 + GEBCO elevation data

### Technology Stack
- **Data Processing**: Python, Pandas, Google Earth Engine SDK
- **Feature Store**: Feast on Kubernetes
- **Training**: Kubeflow Pipelines, MLflow
- **Model Serving**: Seldon Core
- **Monitoring**: Prometheus, Grafana, Evidently
- **Infrastructure**: Terraform, Kubernetes
- **CI/CD**: GitHub Actions, Argo CD

## Getting Started

1. **Environment Setup**
   ```bash
   cd notebooks
   pip install -r requirements.txt
   ```

2. **Data Exploration**
   - Start with `01_data_exploration.ipynb`
   - Explore satellite imagery in `02_satellite_data.ipynb`
   - Analyze ocean physics in `03_ocean_physics.ipynb`

3. **Feature Engineering**
   ```bash
   cd src/features
   python feature_definitions.py
   ```

4. **Model Training**
   ```bash
   cd pipelines
   kfp run --pipeline training_pipeline.yaml
   ```

## Project Structure

```
mlops-sdg14/
├── data/                      # Raw and processed data
├── notebooks/                 # Jupyter notebooks for exploration
├── src/                       # Source code
│   ├── data/                 # Data ingestion modules
│   ├── features/             # Feature engineering
│   ├── models/               # Model definitions
│   └── api/                  # API endpoints
├── pipelines/                # Kubeflow pipeline definitions
├── infrastructure/           # Terraform and K8s manifests
├── monitoring/               # Grafana dashboards and alerts
└── docker/                   # Docker configurations
```

## License

MIT License - See LICENSE file for details.

## Contributing

Please see CONTRIBUTING.md for guidelines.
