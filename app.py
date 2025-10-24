from flask import Flask, render_template, request, jsonify
import couchdb

app = Flask(__name__)

# ------------------------------
# CouchDB Connection Settings
# ------------------------------
COUCHDB_URL = "http://admin:21951a05g1@127.0.0.1:5984/"
DB_NAME = "user_aliases"

couch = couchdb.Server(COUCHDB_URL)
if DB_NAME in couch:
    db = couch[DB_NAME]
else:
    db = couch.create(DB_NAME)


# ------------------------------
# Routes
# ------------------------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/users', methods=['GET'])
def get_users():
    data = []
    for i, doc_id in enumerate(db):
        doc = db[doc_id]
        data.append({
            "sno": i + 1,
            "id": doc_id,
            "user_name": doc.get("user_name"),
            "salesforce_names": doc.get("salesforce_names", [])
        })
    return jsonify(data)


@app.route('/users', methods=['POST'])
def add_user():
    info = request.json
    user_name = info.get("user_name")
    salesforce_names = info.get("salesforce_names", [])

    if isinstance(salesforce_names, str):
        salesforce_names = [salesforce_names]

    # Check if user already exists
    existing_doc = None
    for doc_id in db:
        doc = db[doc_id]
        if doc.get("user_name", "").strip().lower() == user_name.strip().lower():
            existing_doc = doc
            break

    if existing_doc:
        # Merge Salesforce names (avoid duplicates)
        existing_sf_names = set(existing_doc.get("salesforce_names", []))
        existing_sf_names.update(salesforce_names)
        existing_doc["salesforce_names"] = list(existing_sf_names)
        db.save(existing_doc)
        return jsonify({"msg": "Updated existing user", "id": existing_doc.id})
    else:
        doc_id, _ = db.save({
            "user_name": user_name,
            "salesforce_names": salesforce_names
        })
        return jsonify({"msg": "Added new user", "id": doc_id})


@app.route('/users/<id>', methods=['PUT'])
def update_user(id):
    if id in db:
        doc = db[id]
        info = request.json
        doc["user_name"] = info.get("user_name", doc["user_name"])
        doc["salesforce_names"] = info.get("salesforce_names", doc["salesforce_names"])
        db.save(doc)
        return jsonify({"msg": "Updated"})
    return jsonify({"error": "Not found"}), 404


@app.route('/users/<id>', methods=['DELETE'])
def delete_user(id):
    if id in db:
        doc = db[id]
        db.delete(doc)
        return jsonify({"msg": "Deleted"})
    return jsonify({"error": "Not found"}), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
