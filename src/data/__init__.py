"""
Marine Ecosystem Data Processing Module

This module provides utilities for ingesting, processing, and validating
marine ecosystem data for the SDG 14 MLOps platform.
"""

from .ingestion import (
    OBISDataIngester,
    NOAABuoyIngester, 
    ArgoFloatIngester,
    DataValidator,
    create_data_catalog
)

__all__ = [
    'OBISDataIngester',
    'NOAABuoyIngester', 
    'ArgoFloatIngester',
    'DataValidator',
    'create_data_catalog'
]
