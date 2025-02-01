import os
from flask import Flask, render_template, request, jsonify
from markupsafe import escape
from email_validator import validate_email, EmailNotValidError
from hashlib import sha256
import stripe
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column
import time
from dataclasses import dataclass

import blockchain_handler
from parameter_handler import ParameterHandler
import email_handler
import scheduled_tasks

parameters = ParameterHandler()

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


scheduled_tasks.start_tasks()


@app.get('/db_debug_remove_this_before_publishing') # FIXME DEBUG
def db_debug():
    return {"orders": jsonify(CarvingOrder.query.all()),
            "reminders": jsonify(SentReminderEmail.query.all())}


@dataclass(kw_only=True)
class CarvingOrder(db.Model):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    object_id: Mapped[str] = mapped_column(db.String(30), unique=True, index=True)
    payment_id: Mapped[str] = mapped_column(db.String(30), unique=True, index=True)
    carving_text: Mapped[str] = mapped_column(db.String(parameters.carving_length_limit))
    provided_email: Mapped[str] = mapped_column(db.String(320))
    receipt_email: Mapped[str] = mapped_column(db.String(320))
    created_at: Mapped[float] = mapped_column(db.Double)
    received_at: Mapped[float] = mapped_column(db.Double, default=time.time)
    blockchain_executed: Mapped[bool] = mapped_column(db.Boolean, default=False)
    email_sent: Mapped[bool] = mapped_column(db.Boolean, default=False)


@dataclass(kw_only=True)
class SentReminderEmail(db.Model):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    email_address: Mapped[str] = mapped_column(db.String(320), index=True)
    time_sent: Mapped[float] = mapped_column(db.Double, default=time.time, index=True)


@app.get("/")
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
    return {"carving_id:": carving_id, "message": blockchain_handler.read(carving_id)}


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
    user_id = sha256(f"{email}:{parameters.user_id_salt}".encode('utf-8')).hexdigest()
    failed_carving_indices = 0
    carving_index = 0
    valid_carving_ids = []
    while failed_carving_indices < parameters.max_index_failures:
        carving_id = sha256(f"{user_id}:{carving_index}:{parameters.carving_id_salt}".encode('utf-8')).hexdigest()
        carving_index += 1
        carving_text = blockchain_handler.read(carving_id)
        if not carving_text:
            failed_carving_indices += 1
        else:
            valid_carving_ids.append(carving_id)
    carving_id_text = "\n".join(f"https://carve.xyz/inscription?id={carving_id}" for carving_id in valid_carving_ids)
    # send email
    email_handler.send_template_email(email, "Your carvings", "carvings_email.html", carving_text=carving_id_text)


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
    if blockchain_handler.publicize(carving_id):
        return {"carving_id:": carving_id, "message": "Carving publicized (stub)."}
    else:
        return {"carving_id:": carving_id, "message": "Publicizing failed."}, 400


@app.get('/peruse')
def peruse_carvings():
    public_carving_ids = blockchain_handler.peruse()
    found_carvings = []
    for carving_id in public_carving_ids:
        carving_content = blockchain_handler.read(carving_id)
        if carving_content:
            found_carvings.append(carving_content)
    return found_carvings


@app.post('/delete/<carving_id>')
def delete_carving(carving_id):
    request_json = request.get_json()
    # todo: rework with secrets
    if "api_key" not in request_json or request_json.get("api_key") != parameters.admin_key:
        return render_template('error/generic.html', message=f"nope"), 403
    if blockchain_handler.scratch(carving_id):
        return {"carving_id:": carving_id, "message": "Deletion successful."}, 200
    else:
        return {"carving_id:": carving_id, "message": "Deletion failed."}, 404

@app.post("/stripe_webhook")
def stripe_webhook():
    payload = request.get_data(as_text=True)
    #print(payload)
    #print(str(request.headers))
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, parameters.stripe_api_key
        )

    except ValueError as e:
        # Invalid payload
        print("Invalid payload received.", e)
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print("Signature verification failed", e)
        return "Invalid signature", 400

    # Handle the checkout.session.completed event
    if event["type"] == "payment_intent.succeeded":
        object_id = event['id']
        payment_object = event["data"]["object"]
        payment_id = payment_object['id']
        print(f"Received payment event, object_id: {object_id}, payment ID: {payment_id}")
        if CarvingOrder.query.filter_by(object_id=object_id).first():
            print("Payment already processed (object_id matches).")
        elif CarvingOrder.query.filter_by(payment_id=payment_id).first():
            print("Payment already processed (payment_id matches).")
        else:
            payment_metadata = payment_object["metadata"]
            order = CarvingOrder(
                object_id=object_id,
                payment_id=payment_id,
                carving_text=payment_metadata.get("carving_text", ""),
                provided_email=payment_metadata.get("provided_email", ""),
                receipt_email=payment_object.get("receipt_email", ""),
                created_at=event.get("created", 0))
            db.session.add(order)
            db.session.commit()
            # TODO: async crypto function call
    else:
        print(f"Unknown event type: {event['type']}")
    return "Success", 200


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)