import os, json, time, requests

GRAPH_VERSION = os.environ.get("GRAPH_API_VERSION", "v25.0")
BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"

def post(path, data):
    r = requests.post(f"{BASE}{path}", data=data, timeout=60)
    j = r.json()
    if "error" in j:
        raise RuntimeError(j["error"])
    return j

def get(path, params):
    r = requests.get(f"{BASE}{path}", params=params, timeout=60)
    j = r.json()
    if "error" in j:
        raise RuntimeError(j["error"])
    return j

def wait_container(container_id, token, timeout_sec=180):
    start = time.time()
    while time.time() - start < timeout_sec:
        st = get(f"/{container_id}", {"fields": "status_code", "access_token": token})
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container status: {code}")
        time.sleep(3)
    raise RuntimeError("Timeout esperando el contenedor")

def main():
    token = os.environ["IG_ACCESS_TOKEN"]
    ig_user_id = os.environ["IG_USER_ID"]
    image_url = os.environ["PUBLIC_IMAGE_URL"]

    with open("public/latest.json", "r", encoding="utf-8") as f:
        payload = json.load(f)

    caption = payload["caption"]
    extra = os.environ.get("IG_CAPTION_EXTRA", "").strip()
    if extra:
        caption = caption + "\n\n" + extra

    # 1) create container
    creation = post(f"/{ig_user_id}/media", {
        "image_url": image_url,
        "caption": caption,
        "access_token": token
    })
    creation_id = creation["id"]

    wait_container(creation_id, token)

    # 2) publish
    published = post(f"/{ig_user_id}/media_publish", {
        "creation_id": creation_id,
        "access_token": token
    })

    print("Publicado:", published)

if __name__ == "__main__":
    main()
