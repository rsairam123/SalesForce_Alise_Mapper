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

    # First, check if a document already exists with the exact pair (case-insensitive)
    exact_match_id = None
    for doc_id in db:
        doc = db[doc_id]
        if doc.get("user_name", "").strip().lower() == user_name.lower() and \
           (doc.get("salesforce_name") or "").strip().lower() == salesforce_name.lower():
            exact_match_id = doc_id
            break

    if exact_match_id:
        return jsonify({"msg": "Mapping already exists", "id": exact_match_id})

    # Enforce uniqueness of salesforce_name across all documents (case-insensitive)
    for doc_id in db:
        doc = db[doc_id]
        if (doc.get("salesforce_name") or "").strip().lower() == salesforce_name.lower():
            return jsonify({
                "error": "salesforce_name must be unique",
                "details": f"The salesforce_name '{salesforce_name}' is already mapped to user '{doc.get('user_name')}'."
            }), 409

    # Create a new mapping document. Allow duplicate user_name values.
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

        # Prepare potential new values
        new_user_name = doc.get("user_name")
        new_sf_name = doc.get("salesforce_name")

        if "user_name" in info and isinstance(info["user_name"], str) and info["user_name"].strip():
            new_user_name = info["user_name"].strip()
        if "salesforce_name" in info and isinstance(info["salesforce_name"], str) and info["salesforce_name"].strip():
            candidate_sf = info["salesforce_name"].strip()
            # If changing to a different salesforce_name, enforce global uniqueness
            if candidate_sf.lower() != (new_sf_name or "").lower():
                for other_id in db:
                    if other_id == id:
                        continue
                    other = db[other_id]
                    if (other.get("salesforce_name") or "").strip().lower() == candidate_sf.lower():
                        return jsonify({
                            "error": "salesforce_name must be unique",
                            "details": f"The salesforce_name '{candidate_sf}' is already mapped to user '{other.get('user_name')}'."
                        }), 409
            new_sf_name = candidate_sf

        # Apply updates
        doc["user_name"] = new_user_name
        doc["salesforce_name"] = new_sf_name
        # Remove resolved conflicts (keep field for backward compatibility)
        conflicts = doc.get("conflicts", [])
        doc["conflicts"] = [c for c in conflicts if c.lower() != (new_sf_name or "").lower()]
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
