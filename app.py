import os
from flask import jsonify
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError
from flask import (Flask, redirect, render_template, request,
                   send_from_directory, url_for)

app = Flask(__name__)


@app.route('/')
def index():
   print('Request for index page received')
   return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/hello', methods=['POST'])
def hello():
   name = request.form.get('name')

   if name:
       print('Request for hello page received with name=%s' % name)
       return render_template('hello.html', name = name)
   else:
       print('Request for hello page received with no name or blank name -- redirecting')
       return redirect(url_for('index'))


# Azure Blob Storage configuration
storage_account = os.environ["AZURE_STORAGE_ACCOUNT_NAME"]
container_name = os.environ["AZURE_STORAGE_CONTAINER_NAME_01"]

credential = DefaultAzureCredential()

blob_service = BlobServiceClient(
    account_url=f"https://{storage_account}.blob.core.windows.net",
    credential=credential
)


@app.route("/storage/health")
def storage_health():
    try:
        container = blob_service.get_container_client(container_name)

        # Check whether the application can read container properties.
        container.get_container_properties()

        return jsonify({
            "status": "connected",
            "storage_account": storage_account,
            "container": container_name,
            "authentication": "Microsoft Entra ID"
        })

    except AzureError:
        app.logger.exception("Storage connectivity check failed")
        return jsonify({
            "status": "error",
            "message": "Storage connectivity or authorization failed"
        }), 503

@app.route("/identity/health")
def identity_health():
    try:
        credential.get_token(
            "https://storage.azure.com/.default"
        )

        return jsonify({
            "status": "success",
            "message": "Azure identity token acquired"
        })

    except Exception:
        app.logger.exception("Managed identity test failed")
        return jsonify({
            "status": "error",
            "message": "Token acquisition failed"
        }), 503

@app.route("/storage/files")
def list_files():
    try:
        container = blob_service.get_container_client(container_name)

        files = [
            blob.name
            for blob in container.list_blobs()
        ]

        return jsonify({
            "container": container_name,
            "files": files
        })

    except AzureError:
        app.logger.exception("Storage listing failed")
        return jsonify({
            "status": "error",
            "message": "Unable to list blobs"
        }), 503

if __name__ == '__main__':
   app.run()
