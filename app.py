from flask import Flask, url_for, redirect, render_template, request, jsonify
import requests
from dotenv import load_dotenv, dotenv_values
import os
from urllib.parse import quote, urlparse
import json


config = dotenv_values(".env")

load_dotenv()
app = Flask(__name__, template_folder="template")
client_Id = os.getenv("CLIENT_ID")
client_Secret = os.getenv("CLIENT_SECRET")
tokenURL = os.getenv("TOKEN_URL")
authURL = os.getenv("AUTH_URL")
redirectURI = os.getenv("REDIRECT_URI")
orgId = os.getenv("ORG_ID")

encodedRedirectURI = quote(redirectURI, safe="")

app.config["OAUTH2_PROVIDERS"] = {
    "johnDeere": {
        "client_id": client_Id,
        "client_secret": client_Secret,
        "authorize_url": authURL,
        "token_url": tokenURL,
        "scopes": ["ag1", "ag2", "ag3", "files"],
        "redirect_uri": redirectURI,
    },
}


def get_access_token(code):
    try:
        response = requests.post(
            tokenURL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_Id,
                "client_secret": client_Secret,
                "redirect_uri": redirectURI,
            },
        )
        response_data = response.json()

        if "access_token" in response_data:
            access_token = response_data["access_token"]
            return access_token
        else:
            print(
                f"Error: Access token not found in response. Response content: {json.dumps(response_data)}"
            )
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error during token retrieval: {e}")
        return None
    except ValueError as e:
        print(
            f"Error: Unable to parse JSON response. Response content: {response.content}"
        )
        return None


@app.route("/token-refresh", methods=["POST"])
def token_refresh():
    refresh_token = request.json.get("refresh_token")

    if not refresh_token:
        return jsonify({"error": "Refresh token is missing"}), 400

    try:
        response = requests.post(
            tokenURL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_Id,
                "client_secret": client_Secret,
            },
        )
        response_data = response.json()

        if "access_token" in response_data:
            access_token = response_data["access_token"]
            return jsonify({"access_token": access_token}), 200
        else:
            return jsonify({"error": "Access token not found in response"}), 500

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error during token refresh: {e}"}), 500
    except ValueError as e:
        return (
            jsonify(
                {
                    "error": f"Error: Unable to parse JSON response. Response content: {response.content}"
                }
            ),
            500,
        )


if __name__ == "__main__":
    app.run(debug=True)


def oauth2_authorize(provider):
    authorization_url = f"{authURL}?response_type=code&client_id={client_Id}&state=DSA&scope=ag1%20ag2%20ag3&redirect_uri={encodedRedirectURI}"
    return redirect(authorization_url)


app.add_url_rule("/oauth2_authorize/<provider>", "oauth2_authorize", oauth2_authorize)


def make_client_api_call(access_token, client_id):
    url = f"https://sandboxapi.deere.com/platform/organizations/{orgId}/clients/{client_id}"
    headers = {
        "Accept": "application/vnd.deere.axiom.v3+json",
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code} - {response.text}"


def make_farm_api_call(access_token, farm_id):
    url = f"https://sandboxapi.deere.com/platform/organizations/{orgId}/farms/{farm_id}"
    headers = {
        "Accept": "application/vnd.deere.axiom.v3+json",
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code} - {response.text}"


def make_field_api_call(access_token, field_id):
    url = (
        f"https://sandboxapi.deere.com/platform/organizations/{orgId}/fields/{field_id}"
    )
    headers = {
        "Accept": "application/vnd.deere.axiom.v3+json",
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code} - {response.text}"


def internal_make_map_summary_api_call(access_token, field_id, title):
    print("title:", title)
    url = f"https://sandboxapi.deere.com/platform/organizations/{orgId}/fields/{field_id}/mapLayerSummaries"
    payload = json.dumps(
        {
            "links": [
                {
                    "rel": "owningOrganization",
                    "uri": f"https://sandboxapi.deere.com/platform/organizations/{orgId}",
                },
                {
                    "rel": "contributionDefinition",
                    "uri": "https://sandboxapi.deere.com/platform/contributionDefinitions/a185014b-a0b6-46e8-8b7e-903cc4eda125",
                },
            ],
            "title": title,
        }
    )
    headers = {
        "Accept": "application/vnd.deere.axiom.v3+json",
        "Content-Type": "application/vnd.deere.axiom.v3+json",
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 201:
        return (response.headers["Location"],)


def internal_make_map_layer_api_call(access_token, map_layer_summary_id, title):
    url = f"https://sandboxapi.deere.com/platform/mapLayerSummaries/{map_layer_summary_id}/mapLayers"
    payload = json.dumps(
        {
            "title": title,
            "legends": {
                "unitId": "seeds1ha-1",
                "ranges": [
                    {
                        "label": "Other - Upper Bound",
                        "minimum": 87500,
                        "maximum": 262500,
                        "hexColor": "#a6cee3",
                        "percent": 2.11,
                    },
                    {
                        "label": "High",
                        "minimum": 87300,
                        "maximum": 87500,
                        "hexColor": "#1f78b4",
                        "percent": 18.02,
                    },
                    {
                        "label": "Medium",
                        "minimum": 87100,
                        "maximum": 87300,
                        "hexColor": "#b2df8a",
                        "percent": 49.74,
                    },
                    {
                        "label": "Low",
                        "minimum": 87100,
                        "maximum": 87300,
                        "hexColor": "#b2df8a",
                        "percent": 49.74,
                    },
                    {
                        "label": "Other - Lower Bound",
                        "minimum": 0,
                        "maximum": 87000,
                        "hexColor": "#fb9a99",
                        "percent": 3.13,
                    },
                ],
            },
        }
    )
    headers = {
        "Accept": "application/vnd.deere.axiom.v3+json",
        "Content-Type": "application/vnd.deere.axiom.v3+json",
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.post(url, headers=headers, data=payload)
    print("response", response.text)
    if response.status_code == 201:
        return (response.headers["Location"],)


def make_file_upload_call(access_token, fileId):
    url = f"https://sandboxapi.deere.com/platform/files/{fileId}"
    headers = {
        "Accept": "application/vnd.deere.axiom.v3+json",
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code} - {response.text}"


def make_fileId(access_token, name):
    url = f"https://sandboxapi.deere.com/platform/organizations/{orgId}/files"
    payload = json.dumps({"name": name})
    headers = {
        "Accept": "application/vnd.deere.axiom.v3+json",
        "Content-Type": "application/vnd.deere.axiom.v3+json",
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.post(url, headers=headers, data=payload)

    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code} - {response.text}"


@app.route("/home")
def hello_world():
    return render_template("index.html")


@app.route("/")
def authorize_john_deere():
    login_url = url_for("oauth2_authorize", provider="johnDeere", _external=True)
    is_home_page = True
    return render_template("index.html", login_url=login_url, is_home_page=is_home_page)


@app.route("/callback", methods=["GET"])
def oauth2_callback():
    access_token = get_access_token(request.args.get("code"))
    print(f"Access token: {access_token}")

    return render_template("index.html", access_token=access_token)


@app.route("/api_call", methods=["GET"])
def api_call():
    access_token = request.args.get("access_token")
    client_id = request.args.get("client_id")
    farm_id = request.args.get("farm_id")
    field_id = request.args.get("field_id")
    date = request.args.get("date")

    if not access_token:
        return "Error: Missing access_token parameter in the request", 400
    responses = {}

    if client_id:
        responses["client"] = make_client_api_call(access_token, client_id)

    if farm_id:
        responses["farm"] = make_farm_api_call(access_token, farm_id)

    if field_id:
        responses["field"] = make_field_api_call(access_token, field_id)

    print("Response", responses)
    return json.dumps(responses)


@app.route("/fileId", methods=["POST"])
def make_fileId():
    data = request.json
    name = data.get("file_name")
    access_token = request.json.get("access_token")
    location = internal_make_fileId(access_token, name)
    print("location", location)
    return location

@app.route("/make_map_summary_api_call", methods=["POST"])
def make_map_summary_api_call():
    access_token = request.json.get("access_token")
    data = request.json
    field_id = data.get("field_id")
    title = data.get("title")
    location = internal_make_map_summary_api_call(access_token, field_id, title)
    location2 = None
    if location is not None:
        a = location[0]
        parsed_url = urlparse(a)
        map_layer_summary_id = parsed_url.path.split("/")[-1]
        location2 = internal_make_map_layer_api_call(
            access_token, map_layer_summary_id, title
        )
        print("location2", location2)
    if location2 is not None:
        b = location2[0]
        parsed_url2 = urlparse(b)
        map_layer_id = parsed_url2.path.split("/")[-1]
        print("map_layer_id", map_layer_id)
        return render_template("index.html", map_layer_id=map_layer_id)
    else:
        return jsonify({"error": "Failed to create map summary"}), 500


# @app.route("/upload_file", methods=['POST'])
# def make_file_upload_api_call():
#     data = request.json
#     access_token = data.get('access_token')
#     fileId = request.args.get('fileId')
#     if 'file' not in request.files:
#         return jsonify({"error": "No file part in the request"}), 400
#     file = request.files['file']

#     if file.filename == '':
#         return jsonify({"error": "No selected file"}), 400

#     location = make_file_upload_call(access_token, fileId)
#     response = jsonify({"result": "success"})
#     response.headers["Location"] = location
#     print(f"API response Location: {location}")

#     return response


@app.route("/success", methods=["GET", "POST"])
def success():
    if request.method == "POST":
        return "Form submitted successfully!"

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
