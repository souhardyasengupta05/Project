from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import statistics
import json
import os
from mangum import Mangum

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class LatencyRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

def load_telemetry_data():
    try:
        with open("q-vercel-latency.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: {e}")
        return []

@app.post("/api/latency-metrics")
async def calculate_metrics(request: LatencyRequest):
    data = load_telemetry_data()
    results = {}
    
    for region in request.regions:
        region_data = [d for d in data if d.get("region") == region]
        
        if not region_data:
            results[region] = {"avg_latency": 0.0, "p95_latency": 0.0, "avg_uptime": 0.0, "breaches": 0}
            continue
            
        latencies = [d.get("latency_ms", 0) for d in region_data]
        
        # Calculate metrics
        avg_latency = statistics.mean(latencies)
        
        sorted_latencies = sorted(latencies)
        p95_index = int(0.95 * len(sorted_latencies))
        p95_latency = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]
        
        uptime_count = len([l for l in latencies if l <= request.threshold_ms])
        avg_uptime = (uptime_count / len(latencies)) * 100
        
        breaches = len([l for l in latencies if l > request.threshold_ms])
        
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches
        }
    
    return results

@app.get("/")
async def root():
    return {"message": "Latency Metrics API - Use POST /api/latency-metrics"}

# Add this endpoint to check if API is working
@app.get("/api/test")
async def test():
    return {"status": "API is working"}

# Vercel handler
handler = Mangum(app)
