from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import statistics
import json
import os

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

class LatencyRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

# Load the telemetry data
def load_telemetry_data():
    # In Vercel, files are relative to the deployment
    try:
        with open('q-vercel-latency.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Try alternative path for Vercel deployment
        with open('./api/q-vercel-latency.json', 'r') as f:
            return json.load(f)

@app.post("/")
async def calculate_metrics(request: LatencyRequest):
    data = load_telemetry_data()
    results = {}
    
    for region in request.regions:
        # Filter data for the current region
        region_data = [item for item in data if item.get('region') == region]
        
        if not region_data:
            results[region] = {
                "avg_latency": 0,
                "p95_latency": 0,
                "avg_uptime": 0,
                "breaches": 0
            }
            continue
        
        # Extract latencies and uptimes
        latencies = [item.get('latency', 0) for item in region_data]
        uptimes = [item.get('uptime', 0) for item in region_data]
        
        # Calculate metrics
        avg_latency = statistics.mean(latencies) if latencies else 0
        avg_uptime = statistics.mean(uptimes) if uptimes else 0
        
        # Calculate 95th percentile
        if latencies:
            sorted_latencies = sorted(latencies)
            index = int(0.95 * len(sorted_latencies))
            p95_latency = sorted_latencies[index] if index < len(sorted_latencies) else sorted_latencies[-1]
        else:
            p95_latency = 0
        
        # Count breaches
        breaches = sum(1 for latency in latencies if latency > request.threshold_ms)
        
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 4),
            "breaches": breaches
        }
    
    return results

# For local testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
