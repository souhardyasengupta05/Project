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

class RegionMetrics(BaseModel):
    avg_latency: float
    p95_latency: float
    avg_uptime: float
    breaches: int

def load_telemetry_data():
    """
    Load telemetry data from q-vercel-latency.json
    """
    try:
        # For Vercel deployment, the file should be in the same directory
        file_path = "q-vercel-latency.json"
        
        # Alternative path for Vercel serverless environment
        if not os.path.exists(file_path):
            file_path = os.path.join(os.path.dirname(__file__), "q-vercel-latency.json")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        print(f"Loaded {len(data)} telemetry records")
        return data
        
    except FileNotFoundError:
        print("Telemetry file not found. Using empty dataset.")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return []
    except Exception as e:
        print(f"Error loading telemetry data: {e}")
        return []

@app.post("/api/latency-metrics")
async def get_latency_metrics(request: LatencyRequest) -> Dict[str, RegionMetrics]:
    # Load the actual telemetry data
    data = load_telemetry_data()
    results = {}
    
    # Filter data only for requested regions
    filtered_data = [d for d in data if d.get("region") in request.regions]
    
    for region in request.regions:
        region_data = [d for d in filtered_data if d.get("region") == region]
        
        if not region_data:
            # Return zeros if no data found for region
            results[region] = RegionMetrics(
                avg_latency=0.0,
                p95_latency=0.0,
                avg_uptime=0.0,
                breaches=0
            )
            continue
            
        # Extract latencies, handling different possible field names
        latencies = []
        for record in region_data:
            # Try different possible field names for latency
            if "latency_ms" in record:
                latencies.append(record["latency_ms"])
            elif "latency" in record:
                latencies.append(record["latency"])
            elif "response_time" in record:
                latencies.append(record["response_time"])
        
        if not latencies:
            results[region] = RegionMetrics(
                avg_latency=0.0,
                p95_latency=0.0,
                avg_uptime=0.0,
                breaches=0
            )
            continue
            
        # Calculate metrics
        avg_latency = statistics.mean(latencies)
        
        # Calculate 95th percentile
        sorted_latencies = sorted(latencies)
        p95_index = int(0.95 * len(sorted_latencies))
        p95_latency = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]
        
        # Calculate uptime (percentage of records below or equal to threshold)
        uptime_records = [latency for latency in latencies if latency <= request.threshold_ms]
        avg_uptime = (len(uptime_records) / len(latencies)) * 100
        
        # Count breaches (records above threshold)
        breaches = len([latency for latency in latencies if latency > request.threshold_ms])
        
        results[region] = RegionMetrics(
            avg_latency=round(avg_latency, 2),
            p95_latency=round(p95_latency, 2),
            avg_uptime=round(avg_uptime, 2),
            breaches=breaches
        )
    
    return results

@app.get("/")
async def root():
    return {"message": "Latency Metrics API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
