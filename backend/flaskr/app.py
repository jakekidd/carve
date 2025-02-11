import os
import time
from flask import Flask, render_template, request, jsonify, redirect
from flask_apscheduler import APScheduler
from hexbytes import HexBytes
from markupsafe import escape
from email_validator import validate_email, EmailNotValidError
from hashlib import sha256
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, validates
from flask_migrate import Migrate
#from flask_Captchaify import Captchaify
from dataclasses import dataclass
from random import randint
from urllib.parse import quote as url_quote
import logging

from parameter_handler import ParameterHandler

parameters = ParameterHandler()

app = Flask(__name__)

import stripe

stripe.api_key = parameters.stripe_api_key

# basedir = os.path.abspath(os.path.dirname(__file__))
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


@dataclass(kw_only=True)
class CarvingOrder(db.Model):
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    object_id: Mapped[str] = mapped_column(db.String(70), unique=True, index=True)
    payment_id: Mapped[str] = mapped_column(db.String(70), unique=True, index=True)
    carving_to: Mapped[str] = mapped_column(db.String(parameters.carving_from_to_limit))
    carving_from: Mapped[str] = mapped_column(db.String(parameters.carving_from_to_limit))
    carving_message: Mapped[str] = mapped_column(db.String(parameters.carving_length_limit))
    carving_properties: Mapped[str] = mapped_column(db.String(70))
    provided_email: Mapped[str] = mapped_column(db.String(320))
    receipt_email: Mapped[str] = mapped_column(db.String(320))
    created_at: Mapped[float] = mapped_column(db.Double)
    received_at: Mapped[float] = mapped_column(db.Double, default=time.time)
    blockchain_executed: Mapped[bool] = mapped_column(db.Boolean, default=False)
    carving_id: Mapped[str] = mapped_column(db.String(70), nullable=True, default="")
    carving_txn: Mapped[str] = mapped_column(db.String(70), nullable=True, default="")
    email_sent: Mapped[bool] = mapped_column(db.Boolean, default=False)
    carving_link: Mapped[str] = mapped_column(db.String(320), nullable=True, default="")
    
    @validates("carving_id", "carving_txn")
    def format_hex(self, key, value):
        return HexBytes(value).to_0x_hex()
    
    @validates("carving_properties")
    def format_properties(self, key, value):
        return HexBytes(HexBytes("00" * 31) + HexBytes(value))[-31:].to_0x_hex()


@dataclass(kw_only=True)
class SentReminderEmail(db.Model):
    __tablename__ = "reminders"
    
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    email_address: Mapped[str] = mapped_column(db.String(320), index=True)
    time_sent: Mapped[float] = mapped_column(db.Double, default=time.time, index=True)


@dataclass(kw_only=True)
class ExistingCarving(db.Model):
    __tablename__ = "carvings"
    
    carving_id: Mapped[str] = mapped_column(db.String(70), primary_key=True, unique=True, index=True)
    carving_txn: Mapped[str] = mapped_column(db.String(70), unique=True, index=True)
    carving_to: Mapped[str] = mapped_column(db.String(parameters.carving_from_to_limit), nullable=True, default=None)
    carving_from: Mapped[str] = mapped_column(db.String(parameters.carving_from_to_limit), nullable=True, default=None)
    carving_message: Mapped[str] = mapped_column(db.String(parameters.carving_length_limit), nullable=True, default=None)
    carving_properties: Mapped[str] = mapped_column(db.String(70), default=HexBytes("00" * 31).to_0x_hex())
    
    @validates("carving_id", "carving_txn")
    def format_hex(self, key, value):
        return HexBytes(value).to_0x_hex()
    
    @validates("carving_properties")
    def format_properties(self, key, value):
        return HexBytes(HexBytes("00" * 31) + HexBytes(value))[-31:].to_0x_hex()


with app.app_context():
    db.create_all()
    db.session.commit()

import email_handler
from carve_api import CarveAPI
api = CarveAPI()

task_scheduler = APScheduler()
task_scheduler.init_app(app)
task_scheduler.start()


@task_scheduler.task('interval', id='update_parameters', minutes=15, misfire_grace_time=900)
def parameter_task():
    # app.logger.debug("Updating parameters from SSM.")
    parameters.update_from_ssm()


# @task_scheduler.task('interval', id='update_carvings', seconds=60, misfire_grace_time=900)
# def carving_task():
#    #app.logger.debug("Updating existing carvings.")
#    contract.update_existing_carvings()


@app.get("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.get("/tasks")
def get_tasks():
    return str(task_scheduler._scheduler.print_jobs())


@app.get('/db_debug_remove_this_before_publishing')  # FIXME DEBUG
def db_debug():
    return jsonify({"orders": CarvingOrder.query.all(), "reminders": SentReminderEmail.query.all(), "carvings": ExistingCarving.query.all()})


# @app.get('/carvings/<carving_id>')
# def retrieve_carving_message(carving_id):
#     # This could be Regex, but should it?
#     if len(carving_id) != 64:
#         return render_template('error/generic.html', message=f"Invalid carving ID length!"), 400
#     try:
#         int(carving_id, 16)
#     except ValueError:
#         return render_template('error/generic.html', message=f"Carving ID is not valid."), 400
#     return {"carving_id:": carving_id, "message": blockchain_handler.read(carving_id)}


# @app.post('/carvings')
# def email_all_carvings():
#     request_json = request.get_json()
#     if "email" not in request_json:
#         return render_template('error/generic.html', message=f"You need to provide an e-mail"), 400
#     submitted_email = request_json.get("email")
#     try:
#         email = validate_email(submitted_email, check_deliverability=False).normalized
#     except EmailNotValidError as e:
#         return render_template('error/generic.html', message=f"Email invalid."), 400
#     user_id = sha256(f"{email}:{parameters.user_id_salt}".encode('utf-8')).hexdigest()
#     failed_carving_indices = 0
#     carving_index = 0
#     valid_carving_ids = []
#     while failed_carving_indices < parameters.max_index_failures:
#         carving_id = sha256(f"{user_id}:{carving_index}:{parameters.carving_id_salt}".encode('utf-8')).hexdigest()
#         carving_index += 1
#         carving_text = blockchain_handler.read(carving_id)
#         if not carving_text:
#             failed_carving_indices += 1
#         else:
#             valid_carving_ids.append(carving_id)
#     carving_id_text = "\n".join(f"https://carve.xyz/inscription?id={carving_id}" for carving_id in valid_carving_ids)
#     # send email
#     email_handler.send_template_email(email, "Your carvings", "carvings_email.html", carving_text=carving_id_text)


# @app.post('/carvings')
# def publicize_carving():
#     request_json = request.get_json()
#     if "carving_id" not in request_json:
#         return render_template('error/generic.html', message=f"You need to provide an e-mail"), 400
#     carving_id = request_json.get("carving_id")
#     if len(carving_id) != 64:
#         return render_template('error/generic.html', message=f"Invalid carving ID length!"), 400
#     try:
#         int(carving_id, 16)
#     except ValueError:
#         return render_template('error/generic.html', message=f"Carving ID is not valid."), 400
#     if blockchain_handler.publicize(carving_id):
#         return {"carving_id:": carving_id, "message": "Carving publicized (stub)."}
#     else:
#         return {"carving_id:": carving_id, "message": "Publicizing failed."}, 400


# @app.get('/peruse')
# def peruse_carvings():
#     public_carving_ids = blockchain_handler.peruse()
#     found_carvings = []
#     for carving_id in public_carving_ids:
#         carving_content = blockchain_handler.read(carving_id)
#         if carving_content:
#             found_carvings.append(carving_content)
#     return found_carvings


# @app.post('/delete/<carving_id>')
# def delete_carving(carving_id):
#     request_json = request.get_json()
#     # todo: rework with secrets
#     if "api_key" not in request_json or request_json.get("api_key") != parameters.admin_key:
#         return render_template('error/generic.html', message=f"nope"), 403
#     if blockchain_handler.scratch(carving_id):
#         return {"carving_id:": carving_id, "message": "Deletion successful."}, 200
#     else:
#         return {"carving_id:": carving_id, "message": "Deletion failed."}, 404

@app.post("/stripe_webhook")
def stripe_webhook():
    payload = request.get_data(as_text=True)
    # print(payload)
    # print(str(request.headers))
    sig_header = request.headers.get("Stripe-Signature")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, parameters.stripe_webhook_key)
    except ValueError as e:
        # Invalid payload
        app.logger.error("Invalid payload received.", e)
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        app.logger.error("Signature verification failed", e)
        return "Invalid signature", 400
    
    # Handle the checkout.session.completed event
    if event["type"] == "payment_intent.succeeded":
        object_id = event['id']
        payment_object = event["data"]["object"]
        payment_id = payment_object['id']
        app.logger.info(f"Received payment event, object_id: {object_id}, payment ID: {payment_id}")
        if CarvingOrder.query.filter_by(object_id=object_id).first():
            app.logger.info("Payment already processed (object_id matches).")
        elif CarvingOrder.query.filter_by(payment_id=payment_id).first():
            app.logger.info("Payment already processed (payment_id matches).")
        else:
            payment_metadata = payment_object["metadata"]
            order = CarvingOrder(object_id=object_id,
                                 payment_id=payment_id,
                                 carving_to=payment_metadata.get("carving_to", ""),
                                 carving_from=payment_metadata.get("carving_from", ""),
                                 carving_message=payment_metadata.get("carving_message", ""),
                                 carving_properties=HexBytes(payment_metadata.get("carving_properties", "")).to_0x_hex(),
                                 provided_email=payment_metadata.get("provided_email", ""),
                                 receipt_email=payment_object.get("receipt_email", ""),
                                 created_at=event.get("created", 0))
            carving_id = None
            if order.provided_email and order.carving_message:
                carving_id = api.get_next_id_for_email(email=order.provided_email)
                order.carving_id = carving_id.to_0x_hex()
                app.logger.debug(f"Generated carving ID: {carving_id.to_0x_hex()} for email: {order.provided_email} - id={api.next_index[api.generate_user_id(order.provided_email)]}")
                carving_txn = api.make_carving(carving_id=carving_id,
                                                    carving_to=order.carving_to,
                                                    carving_from=order.carving_from,
                                                    carving_message=order.carving_message,
                                                    carving_properties=HexBytes(order.carving_properties))
                order.carving_txn = carving_txn.to_0x_hex()
                order.carving_link = f"https://sepolia-optimism.etherscan.io/tx/{carving_txn.to_0x_hex()}#eventlog"
                #app.logger.debug(f"Carving transaction: {carving_txn}, link: {carving_link}")  # email_handler.send_template_email(recipient=order.provided_email,  #                                  subject="You carving has been made!",  #                                  template="carving_confirmation.html",  #                                  message=carving_link)
            else:
                app.logger.error(f"Order {order.payment_id} missing email or carving text.")
            db.session.add(order)
            db.session.commit()
            email_handler.db_to_sheets()
    else:
        app.logger.error(f"Unknown event type: {event['type']}")
    return "Success", 200


@app.route("/get_link/")
def get_link():
    logging.debug(request.args)
    #if request.args.get("carving_from") != "cultist":
    #    return render_template('error/generic.html', message=f"Invalid request!"), 400
    if not request.args.get("provided_email") or not request.args.get("carving_message"):
        return render_template('error/generic.html', message=f"Missing required parameter!"), 400
    carving_data = {x: request.args.get(x, "") for x in ["provided_email", "carving_to", "carving_from", "carving_message", "carving_properties", "carving_display"]}
    carving_data["carving_to"] = carving_data["carving_to"][:parameters.carving_from_to_limit]
    carving_data["carving_from"] = carving_data["carving_from"][:parameters.carving_from_to_limit]
    carving_data["carving_message"] = carving_data["carving_message"][:parameters.carving_length_limit]
    carving_data["carving_properties"] = HexBytes(request.args.get("carving_display", "00")).to_0x_hex()  # TODO make scalable
    carving_data["carving_properties"] = carving_data["carving_properties"][-33:]
    logging.info(f"Received request for carving: {carving_data['carving_message']} to be sent to {carving_data['provided_email']}")
    checkout_session = stripe.checkout.Session.create(success_url=parameters.payment_success_url,
                                                      cancel_url=parameters.payment_cancel_url + "?" + "&".join(
                                                              f"{k}={url_quote(v)}" for k, v in carving_data.items() if v),
                                                      line_items=[{"price": parameters.stripe_price_id, "quantity": 1}],
                                                      mode="payment",
                                                      customer_email=carving_data["provided_email"],
                                                      custom_text={
                                                              "submit": {
                                                                      "message": (f"𝗖𝗮𝗿𝘃𝗶𝗻𝗴 𝘁𝗼:\r\n{carving_data['carving_to']}\r\n" if carving_data[
                                                                          "carving_to"] else "") + (
                                                                                         f"𝗖𝗮𝗿𝘃𝗶𝗻𝗴 𝗳𝗿𝗼𝗺:\r\n{carving_data['carving_from']}\r\n" if
                                                                                         carving_data["carving_from"] else "") + (
                                                                                         f"𝗖𝗮𝗿𝘃𝗶𝗻𝗴 𝗺𝗲𝘀𝘀𝗮𝗴𝗲:\r\n{carving_data['carving_message']}")}},
                                                      payment_intent_data={"metadata": carving_data})
    # print(checkout_session)
    return redirect(checkout_session.url, code=302)


if __name__ == '__main__':
    app.run(debug=True)

if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
