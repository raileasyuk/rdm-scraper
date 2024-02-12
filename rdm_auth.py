"""
This module provides a get_bearer_token function to authenticate with the Rail Data Market API.
"""
import base64
from hashlib import md5
from urllib.parse import urlparse, parse_qs
import sys
from Crypto.Cipher import AES
import requests
import ua_generator


def __unpad(data):
    return data[: -(data[-1] if isinstance(data[-1], int) else ord(data[-1]))]


def __bytes_to_key(data, salt, output=48):
    # extended from https://gist.github.com/gsakkis/4546068
    assert len(salt) == 8, len(salt)
    data += salt
    key = md5(data).digest()
    final_key = key
    while len(final_key) < output:
        key = md5(key + data).digest()
        final_key += key
    return final_key[:output]


def __decrypt(encrypted, passphrase):
    encrypted = base64.b64decode(encrypted)
    assert encrypted[0:8] == b"Salted__"
    salt = encrypted[8:16]
    key_iv = __bytes_to_key(passphrase, salt, 32 + 16)
    key = key_iv[:32]
    iv = key_iv[32:]
    aes = AES.new(key, AES.MODE_CBC, iv)
    return __unpad(aes.decrypt(encrypted[16:]))


# I'm not even joking. The key is "Secret".
__AES_SECRET = "Secret".encode()

# RDM 403's if you don't give a nice looking user agent
__BROWSER_HEADERS = ua_generator.generate(
    browser=("chrome", "edge", "firefox"), platform=("windows")
).headers.get()


def get_bearer_token(username: str, password: str, otp_uri: str | None) -> str:
    """
    Authenticates with the Rail Data Market API and return a bearer token.
    :param username: The username to authenticate with
    :param password: The password to authenticate with
    :param otp_uri: otpauth:// scheme URI for generating TOTP codes (optional)
    :return: The bearer token to authenticate with the RDM API
    """
    print(f"Authenticating as {username}")

    sess = requests.Session()

    auth_config = sess.get(
        "https://api1.raildata.org.uk/prod-env-cache-endpoints/configuration",
        headers=__BROWSER_HEADERS,
    )

    # sometimes this fails, so make sure the status code is 200 else bail
    assert auth_config.status_code == 200, auth_config.text
    auth_config = auth_config.json()

    client_key = __decrypt(auth_config["clientKey"], __AES_SECRET).decode()
    client_secret = __decrypt(auth_config["clientSecret"], __AES_SECRET).decode()

    login_query = do_authorize_call(auth_config, client_key, sess)
    session_data_key = login_query["sessionDataKey"][0]

    auth_resp = sess.post(
        "https://login.raildata.org.uk/commonauth",
        data={
            "usernameUserInput": username,
            "username": username,
            "password": password,
            "sessionDataKey": session_data_key,
        },
        allow_redirects=False,
        headers=__BROWSER_HEADERS,
        timeout=30,
    )
    auth_url = urlparse(auth_resp.headers["Location"])
    auth_query = parse_qs(auth_url.query)

    if "authenticators" in auth_query:
        if otp_uri is None or otp_uri == "":
            print("MFA enforced, but no OTP URI was provided")
            sys.exit(1)

        # Conditional import to avoid loading pyotp unless needed
        import pyotp  # pylint: disable=import-outside-toplevel

        totp = pyotp.parse_uri(otp_uri)

        if not isinstance(totp, pyotp.TOTP):
            print("Invalid OTP URI provided: type is not TOTP")
            sys.exit(1)

        print("Using TOTP for MFA")

        auth_resp = sess.post(
            "https://login.raildata.org.uk/commonauth",
            data={
                "token": totp.now(),
                "sessionDataKey": session_data_key,
            },
            allow_redirects=False,
            headers=__BROWSER_HEADERS,
            timeout=30,
        )
        auth_url = urlparse(auth_resp.headers["Location"])
        auth_query = parse_qs(auth_url.query)

    if "authFailure" in auth_query:
        print(f"Login failed: {auth_query['authFailureMsg']}")
        sys.exit(1)

    authorize_query = do_authorize_call(auth_config, client_key, sess)
    authorize_code = authorize_query["code"][0]

    bearer_token = sess.post(
        f"{auth_config['identityServerUrl']}oauth2/token",
        data={
            "client_id": client_key,
            "client_secret": client_secret,
            "code": authorize_code,
            "grant_type": "authorization_code",
            "redirect_uri": auth_config["redirectURI"],
        },
        headers=__BROWSER_HEADERS,
        timeout=30,
    ).json()["access_token"]

    return bearer_token


def do_authorize_call(auth_config, client_key, sess) -> dict:
    """
    Makes a call to the /oauth2/authorize endpoint and returns the query parameters from the redirect.
    :param auth_config: The auth config object
    :param client_key: The client_id to send across, decrypted from the auth config
    :param sess: The requests session to use
    :return: The query parameters from the redirect
    """
    authorize_resp = sess.get(
        "https://login.raildata.org.uk/oauth2/authorize",
        params={
            "response_type": "code",
            "scope": "openid",
            "redirect_uri": auth_config["redirectURI"],
            "client_id": client_key,
        },
        allow_redirects=False,
        headers=__BROWSER_HEADERS,
        timeout=30,
    )
    redirect_target = urlparse(authorize_resp.headers["Location"])
    redirect_target_query = parse_qs(redirect_target.query)
    return redirect_target_query
