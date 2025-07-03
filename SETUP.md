# Marine Ecosystem Health & Species Presence Prediction Platform - Setup Guide

## 🚀 Getting Started

This guide will help you set up the complete MLOps pipeline for marine ecosystem predictions.

## Prerequisites

- Python 3.8 or higher
- Git
- Docker (for containerization)
- Access to Google Earth Engine (free registration)
- AWS or GCP account (for cloud storage)

## Quick Start

### 1. Environment Setup

```bash
# Clone the repository (if not already done)
git clone <your-repo-url>
cd mlops-sdg14

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure APIs and Credentials

Create a `.env` file in the root directory:

```bash
# Google Earth Engine
# Run: earthengine authenticate (first time only)

# NOAA API
NOAA_API_KEY=your_noaa_api_key_here

# AWS (if using S3)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-west-2

# Google Cloud (if using GCS)
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json

# Optional: Slack/Discord for alerts
SLACK_WEBHOOK_URL=your_slack_webhook_url
```

### 3. API Registration

#### Google Earth Engine (Required)
1. Visit https://earthengine.google.com/
2. Sign up for access (free for research and education)
3. Install the Earth Engine API: `pip install earthengine-api`
4. Authenticate: `earthengine authenticate`

#### NOAA API (Recommended)
1. Visit https://www.ncdc.noaa.gov/cdo-web/webservices/v2
2. Request a free API key
3. Add to your `.env` file

### 4. Run the Data Ingestion Pipeline

```bash
# Start Jupyter Lab
jupyter lab

# Open and run the notebook:
notebooks/01_data_ingestion.ipynb
```

## Project Architecture

```
MLOps Pipeline Flow:
Data Sources → Ingestion → Feature Store → Training → Model Serving → Monitoring
```

### Data Sources Integration

| Source | Purpose | Authentication | Status |
|--------|---------|----------------|---------|
| Google Earth Engine | Satellite imagery (Sentinel, MODIS) | Google account | ✅ Integrated |
| OBIS API | Marine species occurrences | Public API | ✅ Integrated |
| NOAA NDBC | Buoy sensor data | Public API | ✅ Integrated |
| Argovis | Argo float profiles | Public API | ✅ Integrated |
| GEBCO | Bathymetry data | Manual download | 📋 Manual step |

### Next Development Phases

1. **Data Ingestion** (Current) ✅
   - Multi-source data collection
   - Data validation and quality checks
   - Local and cloud storage

2. **Feature Engineering** (Next) 🔄
   - Spatio-temporal feature computation
   - Feature store setup (Feast)
   - Data preprocessing pipelines

3. **Model Training** 📋
   - Kubeflow pipeline setup
   - ML model development (XGBoost, LSTM)
   - Experiment tracking (MLflow)

4. **Model Serving** 📋
   - Seldon Core deployment
   - API endpoint creation
   - Auto-scaling configuration

5. **Monitoring & Ops** 📋
   - Prometheus + Grafana dashboards
   - Data drift detection (Evidently)
   - CI/CD with GitHub Actions

## Development Workflow

### Daily Development
```bash
# Activate environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Start development server
jupyter lab

# Run tests
pytest tests/

# Code formatting
black src/
flake8 src/
```

### Adding New Data Sources

1. Create ingester class in `src/data/ingestion.py`
2. Add validation logic in `DataValidator`
3. Update the ingestion notebook
4. Test with sample data
5. Document in README

### Model Development

1. Create model definitions in `src/models/`
2. Add training scripts in `src/models/training.py`
3. Configure Kubeflow pipelines in `pipelines/`
4. Set up experiment tracking

## Troubleshooting

### Common Issues

**Earth Engine Authentication**
```bash
# If authentication fails:
earthengine authenticate --force
```

**Memory Issues with Large Datasets**
- Use data chunking in xarray
- Implement streaming data processing
- Consider Dask for parallel processing

**API Rate Limits**
- Implement exponential backoff
- Use caching for repeated requests
- Consider data pagination

### Performance Optimization

1. **Data Processing**
   - Use vectorized operations (NumPy/Pandas)
   - Implement lazy loading for large datasets
   - Cache frequently accessed data

2. **Model Training**
   - Use GPU acceleration when available
   - Implement distributed training for large models
   - Optimize hyperparameter search

3. **Serving**
   - Implement model caching
   - Use async/await for API calls
   - Configure proper resource limits

## Monitoring and Alerts

### Health Checks

```bash
# Check data ingestion status
python -m src.data.ingestion --health-check

# Validate model endpoints
curl http://localhost:8080/health

# Monitor system resources
docker stats
```

### Setting Up Alerts

1. Configure Prometheus to scrape metrics
2. Set up Grafana dashboards
3. Configure alert rules in Alertmanager
4. Test notification channels

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request
5. Ensure CI/CD passes

## License

MIT License - See LICENSE file for details.

## Support

- 📧 Email: support@mlops-sdg14.org
- 💬 Slack: #mlops-sdg14
- 📖 Documentation: https://docs.mlops-sdg14.org
- 🐛 Issues: GitHub Issues
