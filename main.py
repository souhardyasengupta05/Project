from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import statistics
import json
import os
from mangum import Mangum

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LatencyRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

def load_telemetry_data():
    """Safely load telemetry data with error handling"""
    try:
        # Try to find the JSON file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "q-vercel-latency.json")
        
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)
                print(f"Successfully loaded {len(data)} records")
                return data
        else:
            print(f"File not found at: {json_path}")
            # Return sample data for testing
            return [
                {"region": "emea", "latency_ms": 150},
                {"region": "emea", "latency_ms": 160},
                {"region": "emea", "latency_ms": 200},
                {"region": "amer", "latency_ms": 140},
                {"region": "amer", "latency_ms": 170},
                {"region": "amer", "latency_ms": 190},
            ]
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return []

@app.post("/api/latency-metrics")
async def calculate_metrics(request: LatencyRequest):
    """Calculate latency metrics"""
    try:
        print(f"Received request: {request}")
        
        data = load_telemetry_data()
        results = {}
        
        for region in request.regions:
            # Filter data for current region
            region_data = [d for d in data if d.get("region") == region]
            
            if not region_data:
                results[region] = {
                    "avg_latency": 0.0,
                    "p95_latency": 0.0,
                    "avg_uptime": 0.0,
                    "breaches": 0
                }
                continue
            
            # Extract latency values safely
            latencies = []
            for record in region_data:
                latency = record.get("latency_ms") or record.get("latency") or 0
                if isinstance(latency, (int, float)):
                    latencies.append(latency)
                else:
                    # Default value if latency is invalid
                    latencies.append(0)
            
            if not latencies:
                results[region] = {
                    "avg_latency": 0.0,
                    "p95_latency": 0.0,
                    "avg_uptime": 0.0,
                    "breaches": 0
                }
                continue
            
            # Calculate metrics
            try:
                avg_latency = statistics.mean(latencies)
            except:
                avg_latency = 0.0
            
            # Calculate 95th percentile
            try:
                sorted_latencies = sorted(latencies)
                p95_index = int(0.95 * len(sorted_latencies))
                p95_latency = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]
            except:
                p95_latency = 0.0
            
            # Calculate uptime and breaches
            uptime_count = len([l for l in latencies if l <= request.threshold_ms])
            avg_uptime = (uptime_count / len(latencies)) * 100 if latencies else 0.0
            breaches = len([l for l in latencies if l > request.threshold_ms])
            
            results[region] = {
                "avg_latency": round(avg_latency, 2),
                "p95_latency": round(p95_latency, 2),
                "avg_uptime": round(avg_uptime, 2),
                "breaches": breaches
            }
        
        print(f"Returning results: {results}")
        return results
        
    except Exception as e:
        print(f"Error in calculate_metrics: {str(e)}")
        return {"error": f"Internal server error: {str(e)}"}

@app.get("/")
async def root():
    return {
        "message": "Latency Metrics API is running",
        "usage": "POST /api/latency-metrics with JSON body",
        "example_body": {
            "regions": ["emea", "amer"],
            "threshold_ms": 180
        }
    }

@app.get("/test")
async def test():
    """Test endpoint to verify API is working"""
    return {"status": "OK", "message": "API is running"}

# Vercel handler
handler = Mangum(app)
