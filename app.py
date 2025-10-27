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
    for doc_id in db:
        doc = db[doc_id]
        # Support both legacy (array) and new (single) schema on read
        sf_name = doc.get("salesforce_name")
        if not sf_name:
            names = doc.get("salesforce_names", [])
            sf_name = names[0] if isinstance(names, list) and names else None
        data.append({
            "id": doc_id,
            "user_name": doc.get("user_name"),
            "salesforce_name": sf_name,
            "conflicts": doc.get("conflicts", [])
        })
    return jsonify(data)


@app.route('/users', methods=['POST'])
def add_user():
    info = request.json
    user_name = (info.get("user_name") or "").strip()
    salesforce_name = (info.get("salesforce_name") or "").strip()

    if not user_name or not salesforce_name:
        return jsonify({"error": "user_name and salesforce_name are required"}), 400

    # Find existing doc by user_name (case-insensitive)
    existing_doc = None
    for doc_id in db:
        doc = db[doc_id]
        if (doc.get("user_name", "").strip().lower() == user_name.lower()):
            existing_doc = doc
            break

    if existing_doc:
        current_sf = existing_doc.get("salesforce_name")
        if current_sf and current_sf.lower() != salesforce_name.lower():
            # Track conflicts separately
            conflicts = existing_doc.get("conflicts", [])
            if salesforce_name not in conflicts:
                conflicts.append(salesforce_name)
            existing_doc["conflicts"] = conflicts
        # Always set main mapping to the latest provided name
        existing_doc["salesforce_name"] = salesforce_name
        # Clean legacy field if present
        if "salesforce_names" in existing_doc:
            existing_doc.pop("salesforce_names", None)
        db.save(existing_doc)
        return jsonify({"msg": "Updated existing mapping", "id": existing_doc.id})
    else:
        doc_id, _ = db.save({
            "user_name": user_name,
            "salesforce_name": salesforce_name,
            "conflicts": []
        })
        return jsonify({"msg": "Added new mapping", "id": doc_id})


@app.route('/users/<id>', methods=['PUT'])
def update_user(id):
    if id in db:
        doc = db[id]
        info = request.json
        if "user_name" in info and info["user_name"].strip():
            doc["user_name"] = info["user_name"].strip()
        if "salesforce_name" in info and info["salesforce_name"].strip():
            doc["salesforce_name"] = info["salesforce_name"].strip()
            # Remove from conflicts if resolved
            conflicts = doc.get("conflicts", [])
            doc["conflicts"] = [c for c in conflicts if c.lower() != doc["salesforce_name"].lower()]
        # Clean legacy field if present
        if "salesforce_names" in doc:
            doc.pop("salesforce_names", None)
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
