import hashlib
import hmac
import json
import os
import subprocess
import threading
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


DEPLOY_SECRET = os.environ.get("DEPLOY_SECRET", "").strip()
DEPLOY_PATH = os.environ.get("DEPLOY_PATH", "/opt/aspectcoffee").strip()


def _run_deploy():
    deploy_script = os.path.join(DEPLOY_PATH, "deploy.sh")
    subprocess.Popen(
        [deploy_script],
        cwd=DEPLOY_PATH,
        stdout=open("/var/log/deploy.log", "a"),
        stderr=subprocess.STDOUT,
    )


@csrf_exempt
@require_POST
def webhook_deploy(request):
    if not DEPLOY_SECRET:
        return JsonResponse({"error": "deploy webhook is disabled"}, status=503)

    signature = request.headers.get("X-Hub-Signature-256", "")
    body = request.body

    expected = "sha256=" + hmac.new(
        DEPLOY_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return JsonResponse({"error": "invalid signature"}, status=403)

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    ref = data.get("ref", "")
    if ref != "refs/heads/main":
        return JsonResponse({"status": "skipped", "reason": "not main branch"})

    threading.Thread(target=_run_deploy, daemon=True).start()
    return JsonResponse({"status": "deploy started"})
