from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import statistics
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    """Load telemetry data from the JSON file."""
    try:
        # In Vercel, the file should be in the same directory as the code
        file_path = "q-vercel-latency.json"
        if not os.path.exists(file_path):
            # Try the absolute path
            file_path = os.path.join(os.path.dirname(__file__), "q-vercel-latency.json")
        with open(file_path, "r") as f:
            data = json.load(f)
            logger.info(f"Loaded {len(data)} records from {file_path}")
            return data
    except Exception as e:
        logger.error(f"Error loading telemetry data: {e}")
        # Return some sample data for testing if the file is missing
        return [
            {"region": "emea", "latency_ms": 150},
            {"region": "emea", "latency_ms": 160},
            {"region": "emea", "latency_ms": 200},
            {"region": "amer", "latency_ms": 140},
            {"region": "amer", "latency_ms": 170},
            {"region": "amer", "latency_ms": 190},
        ]

@app.post("/api/latency-metrics")
async def calculate_metrics(request: LatencyRequest):
    try:
        data = load_telemetry_data()
        results = {}
        for region in request.regions:
            region_data = [d for d in data if d.get("region") == region]
            if not region_data:
                results[region] = {
                    "avg_latency": 0.0,
                    "p95_latency": 0.0,
                    "avg_uptime": 0.0,
                    "breaches": 0
                }
                continue

            latencies = [d.get("latency_ms", 0) for d in region_data]
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
    except Exception as e:
        logger.error(f"Error in calculate_metrics: {e}")
        return {"error": str(e)}

@app.get("/")
async def root():
    return {"message": "Latency Metrics API"}

# If we are running in Vercel, we don't need to run the app with uvicorn because Vercel will use the `handler` if provided.
# But Vercel expects a WSGI or ASGI app. We can use mangum to wrap FastAPI for AWS Lambda (which Vercel uses) but let's try without first.

# However, Vercel's Python runtime requires a `app` variable for WSGI/ASGI apps.
# We are using FastAPI which is ASGI, so we don't need to change anything.

# If we were using Flask (WSGI) we would have `app = Flask(__name__)` and Vercel would pick that up.

# For FastAPI, we don't need to do anything else.
