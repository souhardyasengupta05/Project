from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import statistics
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class LatencyRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

def load_data():
    try:
        with open('q-vercel-latency.json', 'r') as f:
            return json.load(f)
    except:
        return []

@app.post("/")  # This creates /api/latency endpoint
async def main(request: LatencyRequest):
    data = load_data()
    results = {}
    
    for region in request.regions:
        region_data = [item for item in data if item.get('region') == region]
        
        if not region_data:
            results[region] = {"avg_latency": 0, "p95_latency": 0, "avg_uptime": 0, "breaches": 0}
            continue
        
        latencies = [item.get('latency', 0) for item in region_data]
        uptimes = [item.get('uptime', 0) for item in region_data]
        
        avg_latency = statistics.mean(latencies)
        avg_uptime = statistics.mean(uptimes)
        
        sorted_latencies = sorted(latencies)
        index = int(0.95 * len(sorted_latencies))
        p95_latency = sorted_latencies[min(index, len(sorted_latencies)-1)]
        
        breaches = sum(1 for latency in latencies if latency > request.threshold_ms)
        
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 4),
            "breaches": breaches
        }
    
    return results
