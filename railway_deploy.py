#!/usr/bin/env python3
"""Probe + deploy ondo-var-hedge to Railway. Read-only probe first, then deploy."""
import os, json, urllib.request, tarfile, io

ROOT = os.path.dirname(os.path.abspath(__file__))
PID = "563143b6-f552-43b7-9822-e40633ad8da9"
ENV_ID = "5ceb366a-62da-4b57-8b47-9ace54c281ce"
API = "https://backboard.railway.app/graphql/v2"

def token():
    with open(os.path.join(ROOT, ".secrets.env")) as f:
        for line in f:
            if line.startswith("RAILWAY_TOKEN="):
                return line.strip().split("=", 1)[1]

H = {"Authorization": f"Bearer {token()}", "Content-Type": "application/json",
     "User-Agent": "ondo-var-deploy/1.0", "Accept": "application/json"}

def gql(query, variables=None):
    body = {"query": query}
    if variables:
        body["variables"] = variables
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers=H, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

def create_service():
    r = gql("""mutation($pid: String!, $name: String!) {
      serviceCreate(input: { projectId: $pid, name: $name, source: { image: "" } }) {
        id
      }
    }""", {"pid": PID, "name": "monitor"})
    return r.get("data", {}).get("serviceCreate", {}).get("id")

def probe_deploy(svc):
    # Try the real deploymentCreate mutation with minimal input to learn shape
    r = gql("""mutation($i: DeploymentCreateInput!) {
      deploymentCreate(input: $i) { id }
    }""", {"i": {"serviceId": svc, "environmentId": ENV_ID}})
    return r

if __name__ == "__main__":
    svc = create_service()
    print("service:", svc)
    print("probe deploymentCreate:", json.dumps(probe_deploy(svc))[:600])
