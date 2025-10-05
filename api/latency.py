from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os
import math

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Request model
class LatencyRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

# Response models
class RegionMetrics(BaseModel):
    avg_latency: float
    p95_latency: float
    avg_uptime: float
    breaches: int

class LatencyResponse(BaseModel):
    regions: Dict[str, RegionMetrics]

def load_telemetry_data():
    """Load telemetry data from the JSON file"""
    try:
        # Try multiple possible file locations
        possible_paths = [
            'q-vercel-latency.json',
            './q-vercel-latency.json',
            '/var/task/q-vercel-latency.json',
            './api/q-vercel-latency.json'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        
        # If file not found, return empty list
        print("Warning: q-vercel-latency.json not found")
        return []
    except Exception as e:
        print(f"Error loading telemetry data: {e}")
        return []

def calculate_percentile(data: List[float], percentile: float) -> float:
    """Calculate percentile from a list of values"""
    if not data:
        return 0.0
    
    sorted_data = sorted(data)
    n = len(sorted_data)
    
    if n == 1:
        return sorted_data[0]
    
    # Calculate index for percentile
    index = (n - 1) * percentile / 100.0
    lower_index = math.floor(index)
    upper_index = math.ceil(index)
    
    if lower_index == upper_index:
        return sorted_data[int(index)]
    
    # Linear interpolation
    lower_value = sorted_data[lower_index]
    upper_value = sorted_data[upper_index]
    weight = index - lower_index
    
    return lower_value + (upper_value - lower_value) * weight

# Load telemetry data once at startup
telemetry_data = load_telemetry_data()

@app.post("/", response_model=LatencyResponse)
async def analyze_latency(request: LatencyRequest):
    """
    Analyze latency metrics for specified regions
    Accepts: {"regions": ["region1", "region2"], "threshold_ms": 180}
    Returns: Per-region metrics including avg_latency, p95_latency, avg_uptime, breaches
    """
    try:
        results = {}
        
        for region in request.regions:
            # Filter data for current region (case-insensitive)
            region_data = [
                item for item in telemetry_data 
                if item.get('region', '').lower() == region.lower()
            ]
            
            if not region_data:
                # If no data found for region, return zeros
                results[region] = RegionMetrics(
                    avg_latency=0.0,
                    p95_latency=0.0,
                    avg_uptime=0.0,
                    breaches=0
                )
                continue
            
            # Extract latencies
            latencies = []
            for item in region_data:
                latency = item.get('latency')
                if latency is not None:
                    latencies.append(float(latency))
            
            if not latencies:
                results[region] = RegionMetrics(
                    avg_latency=0.0,
                    p95_latency=0.0,
                    avg_uptime=0.0,
                    breaches=0
                )
                continue
            
            # Calculate metrics
            avg_latency = sum(latencies) / len(latencies)
            p95_latency = calculate_percentile(latencies, 95)
            
            # Calculate breaches (records above threshold)
            breaches = sum(1 for latency in latencies if latency > request.threshold_ms)
            
            # Calculate uptime (fraction of records at or below threshold)
            avg_uptime = (len(latencies) - breaches) / len(latencies)
            
            # Round to 2 decimal places for cleaner output
            results[region] = RegionMetrics(
                avg_latency=round(avg_latency, 2),
                p95_latency=round(p95_latency, 2),
                avg_uptime=round(avg_uptime, 4),  # More precision for uptime percentage
                breaches=breaches
            )
        
        return LatencyResponse(regions=results)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "Latency Analysis API",
        "usage": "POST JSON with {'regions': ['region1', ...], 'threshold_ms': 180}",
        "endpoint": "POST /"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    data_points = len(telemetry_data) if telemetry_data else 0
    regions = list(set(item.get('region') for item in telemetry_data)) if telemetry_data else []
    
    return {
        "status": "healthy",
        "data_points": data_points,
        "regions_available": regions
    }

# Handler for Vercel serverless
handler = app
