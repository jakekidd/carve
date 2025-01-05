from flask import Flask, render_template, request
from markupsafe import escape
from email_validator import validate_email, EmailNotValidError
from hashlib import sha256
import tree
import local_constants
import local_secrets

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.get('/carvings/<carving_id>')
def retrieve_carving_message(carving_id):
    # This could be Regex, but should it?
    if len(carving_id) != 64:
        return render_template('error/generic.html', message=f"Invalid carving ID length!"), 400
    try:
        int(carving_id, 16)
    except ValueError:
        return render_template('error/generic.html', message=f"Carving ID is not valid."), 400
    return {"carving_id:": carving_id, "message": tree.read(carving_id)}


@app.post('/carvings')
def email_all_carvings():
    request_json = request.get_json()
    if "email" not in request_json:
        return render_template('error/generic.html', message=f"You need to provide an e-mail"), 400
    submitted_email = request_json.get("email")
    try:
        email = validate_email(submitted_email, check_deliverability=False).normalized
    except EmailNotValidError as e:
        return render_template('error/generic.html', message=f"Email invalid."), 400
    user_id = sha256(f"email:{local_secrets.user_id_salt}".encode('utf-8')).hexdigest()
    failed_carving_indices = 0
    carving_index = 0
    valid_carving_ids = []
    while failed_carving_indices < local_constants.max_index_failures:
        carving_id = sha256(f"user_id:{carving_index}:{local_secrets.carving_id_salt}".encode('utf-8')).hexdigest()
        carving_index += 1
        carving_text = tree.read(carving_id)
        if not carving_text:
            failed_carving_indices += 1
        else:
            valid_carving_ids.append(carving_id)
    carving_id_text = "\n".join(f"https://carve.xyz/inscription?id={carving_id}" for carving_id in valid_carving_ids)
    # todo: send e-mail

@app.post('/carvings')
def publicize_carving():
    request_json = request.get_json()
    if "carving_id" not in request_json:
        return render_template('error/generic.html', message=f"You need to provide an e-mail"), 400
    carving_id = request_json.get("carving_id")
    if len(carving_id) != 64:
        return render_template('error/generic.html', message=f"Invalid carving ID length!"), 400
    try:
        int(carving_id, 16)
    except ValueError:
        return render_template('error/generic.html', message=f"Carving ID is not valid."), 400
    if tree.publicize(carving_id):
        return {"carving_id:": carving_id, "message": "Carving publicized (stub)."}
    else:
        return {"carving_id:": carving_id, "message": "Publicizing failed."}, 400


@app.get('/peruse')
def peruse_carvings():
    public_carving_ids = tree.peruse()
    found_carvings = []
    for carving_id in public_carving_ids:
        carving_content = tree.read(carving_id)
        if carving_content:
            found_carvings.append(carving_content)
    return found_carvings


@app.post('/delete/<carving_id>')
def delete_carving(carving_id):
    request_json = request.get_json()
    # todo: rework with secrets
    if "api_key" not in request_json or request_json.get("api_key") != local_secrets.admin_api_key:
        return render_template('error/generic.html', message=f"nope"), 403
    if tree.scratch(carving_id):
        return {"carving_id:": carving_id, "message": "Deletion successful."}, 200
    else:
        return {"carving_id:": carving_id, "message": "Deletion failed."}, 404


if __name__ == '__main__':
    app.run(debug=True)