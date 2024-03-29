from flask import Flask, request, abort
from fastapi import HTTPException, WebSocketException
import hmac
import hashlib
import base64
import subprocess


webhook = Flask(__name__)

# Get rand_var from environment variable
rand_cmd = subprocess.check_output(["echo $RAND_VAR"], shell=True, encoding="utf-8")
rand_var=str(rand_cmd).strip()
#print("rand_var")
#print(rand_var)

# Run 'echo' and pipe the output to 'openssl'
secret_cmd = subprocess.Popen(["echo $CRYPT_SECRET"], shell=True, stdout=subprocess.PIPE)
#print(secret_cmd.stdout)
# Run 'openssl' and pipe the output of 'echo' to it
openssl_cmd = subprocess.check_output(["openssl", "enc", "-aes-256-ctr", "-pbkdf2", "-d", "-a", "-k", rand_var], stdin=secret_cmd.stdout, encoding="utf-8")
secret_token=str(openssl_cmd).strip()
#print("..")
#print(secret_token)
#print("...")

def verify_signature(payload_body, secret_token, signature_header):

    """Verify that the payload was sent from GitHub by validating SHA256.
    Raise and return 403 if not authorized.
    Args:
        payload_body: original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
        https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
    """
    if not signature_header:
        raise HTTPException(status_code=403, detail="x-hub-signature-256 header is missing!")
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)

@webhook.route('/hooked', methods=['POST'])
def handle_webhook():
    # Get raw body
    payload_body = request.get_data()
    #print("body")
    #print(payload_body)
    # Get signature header
    signature_header = request.headers.get('X-Hub-Signature-256')
    #print("signature_header")
    #print(signature_header)
    verified = verify_signature(payload_body, secret_token, signature_header)

    if not verified:
        print("not verified")
        abort(401)

    # git pull
    git_pull_output = subprocess.check_output(['git', 'pull'], cwd="/opt/mkdocs")
    print("git pull output")
    print(git_pull_output)
    # mkdocs build
    mkdocs_build_output = subprocess.check_output(['mkdocs', 'build'], cwd="/opt/mkdocs")
    print("mkdocs build output")
    print(mkdocs_build_output)

    print("verified")
    return ('', 200)

# use waitress to serve the webhook on all interfaces port 8080
if __name__ == "__main__":
    from waitress import serve
    serve(webhook, host="0.0.0.0", port=8080)