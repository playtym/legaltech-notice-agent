import json
import subprocess
import os

DIST_ID = "E2LDFKZ9T7UJ4A"
FUNC_NAME = "AppendHTML"

# 1. Create JS file
js_code = """function handler(event) {
    var request = event.request;
    var uri = request.uri;
    if (uri.endsWith('/')) {
        request.uri += 'index.html';
    } else if (!uri.includes('.')) {
        request.uri += '.html';
    }
    return request;
}"""
with open("cf_function.js", "w") as f:
    f.write(js_code)

# 2. Create or Update Function
try:
    print("Checking if function exists...")
    func_info = json.loads(subprocess.check_output(["aws", "cloudfront", "describe-function", "--name", FUNC_NAME]).decode())
    etag = func_info["ETag"]
    print("Function exists. Updating...")
    update_out = subprocess.check_output([
        "aws", "cloudfront", "update-function",
        "--name", FUNC_NAME,
        "--if-match", etag,
        "--function-config", '{"Comment":"Append HTML to clean URLs","Runtime":"cloudfront-js-1.0"}',
        "--function-code", "fileb://cf_function.js"
    ]).decode()
    func_info = json.loads(update_out)
    etag = func_info["ETag"]
except subprocess.CalledProcessError:
    print("Creating function...")
    create_out = subprocess.check_output([
        "aws", "cloudfront", "create-function",
        "--name", FUNC_NAME,
        "--function-config", '{"Comment":"Append HTML to clean URLs","Runtime":"cloudfront-js-1.0"}',
        "--function-code", "fileb://cf_function.js"
    ]).decode()
    func_info = json.loads(create_out)
    etag = func_info["ETag"]

# 3. Publish Function
print("Publishing function...")
publish_out = subprocess.check_output([
    "aws", "cloudfront", "publish-function",
    "--name", FUNC_NAME,
    "--if-match", etag
]).decode()
func_arn = json.loads(publish_out)["FunctionSummary"]["FunctionMetadata"]["FunctionARN"]

# 4. Associate with Distribution
print("Fetching distribution config...")
out = subprocess.check_output(["aws", "cloudfront", "get-distribution-config", "--id", DIST_ID]).decode()
data = json.loads(out)
dist_etag = data["ETag"]
config = data["DistributionConfig"]

# Initialize FunctionAssociations if not exist
if "FunctionAssociations" not in config["DefaultCacheBehavior"]:
    config["DefaultCacheBehavior"]["FunctionAssociations"] = {"Quantity": 0, "Items": []}
elif not config["DefaultCacheBehavior"]["FunctionAssociations"].get("Items"):
    config["DefaultCacheBehavior"]["FunctionAssociations"]["Items"] = []

assocs = config["DefaultCacheBehavior"]["FunctionAssociations"]

# Check if already associated
existing = [a for a in assocs.get("Items", []) if a["EventType"] == "viewer-request" and a["FunctionARN"] == func_arn]
if not existing:
    assocs["Items"] = [a for a in assocs.get("Items", []) if a["EventType"] != "viewer-request"]
    
    assocs["Items"].append({
        "EventType": "viewer-request",
        "FunctionARN": func_arn
    })
    assocs["Quantity"] = len(assocs["Items"])
    
    with open("cf_config_deploy.json", "w") as f:
        json.dump(config, f)
        
    print("Updating distribution...")
    try:
        subprocess.check_output([
            "aws", "cloudfront", "update-distribution",
            "--id", DIST_ID,
            "--if-match", dist_etag,
            "--distribution-config", "file://cf_config_deploy.json"
        ])
        print("Success! Distribution is updating. It may take a few minutes to fully deploy AWS-side.")
    except subprocess.CalledProcessError as e:
        print(f"Error updating distribution.")
else:
    print("Function already associated with distribution.")
