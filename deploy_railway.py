#!/usr/bin/env python3
"""Deploy ondo-var-hedge to Railway via source deploy (no GitHub integration needed).
Uses RAILWAY_TOKEN from .secrets.env. Builds a tarball and pushes to Railway.
"""
import os, sys, tarfile, io, json, subprocess, time

ROOT = os.path.dirname(os.path.abspath(__file__))
PID = "563143b6-f552-43b7-9822-e40633ad8da9"  # ondo-var-hedge project
ENV_ID = "5ceb366a-62da-4b57-8b47-9ace54c281ce"  # production
API = "https://backboard.railway.app/graphql/v2"

def load_token():
    with open(os.path.join(ROOT, ".secrets.env")) as f:
        for line in f:
            if line.startswith("RAILWAY_TOKEN="):
                return line.strip().split("=", 1)[1]

TOKEN = load_token()
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def gql(query, variables=None):
    body = {"query": query}
    if variables:
        body["variables"] = variables
    import urllib.request
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers=H, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

def main():
    # 1. create service
    print("[1] create service...")
    r = gql("""mutation($pid: String!, $name: String!) {
      serviceCreate(input: { projectId: $pid, name: $name, source: { image: "" } }) {
        id
      }
    }""", {"pid": PID, "name": "monitor"})
    svc = r.get("data", {}).get("serviceCreate", {}).get("id")
    if not svc:
        print("serviceCreate failed:", r); sys.exit(1)
    print("    service id:", svc)

    # 2. set railway config (startCommand) via service update is not exposed;
    #    instead set env + rely on railway.json in repo. For source deploy we
    #    must set the start command via the deployment. Use service settings.
    # 3. build tarball of source (exclude .git, .venv, .secrets.env)
    print("[2] build tarball...")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name in ["ondo_var_hedge", "requirements.txt", "railway.json",
                     "Procfile", "Dockerfile", "README.md"]:
            p = os.path.join(ROOT, name)
            tf.add(p, arcname=name, recursive=True)
    data = buf.getvalue()
    print("    tarball bytes:", len(data))

    # 4. upload + deploy
    print("[3] deploy (sourceDeploy)...")
    r = gql("""mutation($pid: String!, $sid: String!, $data: String!) {
      deploymentCreateSource(input: {
        projectId: $pid, serviceId: $sid, environmentId: $ENV_ID_PLACEHOLDER,
        files: $data
      }) { id }
    }""".replace("$ENV_ID_PLACEHOLDER", ENV_ID),
    {"pid": PID, "sid": svc, "data": data.decode("latin-1")})
    # NOTE: sourceDeploy expects base64; adjust if API differs
    print("    raw response:", json.dumps(r)[:800])

if __name__ == "__main__":
    main()
