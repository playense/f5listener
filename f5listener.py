from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
import sseclient
import uvicorn
import json

app = FastAPI()

@app.get("/wait-for-result")
def wait_for_gradio_result(
    event_id: str = Query(...),
    session_hash: str = Query(...)
):
    url = f"http://localhost:7861/gradio_api/queue/data?event_id={event_id}&session_hash={session_hash}"
    headers = {"Accept": "text/event-stream"}

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=120)
        client = sseclient.SSEClient(response)

        for event in client.events():
            if not event.data.strip():
                continue

            # Remove "data: " prefix if needed and parse JSON
            try:
                raw_json = json.loads(event.data)
            except json.JSONDecodeError:
                continue

            if raw_json.get("msg") == "process_completed" and raw_json.get("success"):
                output = raw_json.get("output", {})
                output_data = output.get("data", [])

                # extract all file URLs in output
                file_urls = [entry["url"] for entry in output_data if isinstance(entry, dict) and "url" in entry]

                return JSONResponse(content={
                    "status": "complete",
                    "event_id": raw_json["event_id"],
                    "file_urls": file_urls,
                    "raw": raw_json  # optional: include full response
                })

        return JSONResponse(content={"status": "incomplete", "message": "No 'process_completed' received."})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
