from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from groq import Groq
import os
from dotenv import load_dotenv
from datetime import datetime
from menu import RESTAURANT_INFO
from delivery import get_delivery_time
from orders import (
    create_order,
    get_order_status,
    get_last_order,
    update_order_status
)

load_dotenv()

app = Flask(__name__)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Store conversation history per user
conversations = {}

# Store user states
waiting_for_address = {}
pending_orders = {}

def is_open():
    """Check if restaurant is within operating hours"""
    now = datetime.now()
    return 8 <= now.hour < 22

def get_ai_response(user_number, user_message):
    """Get AI response from Groq"""
    if user_number not in conversations:
        conversations[user_number] = [
            {
                "role": "system",
                "content": RESTAURANT_INFO
            }
        ]

    conversations[user_number].append({
        "role": "user",
        "content": user_message
    })

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=conversations[user_number],
        max_tokens=500
    )

    assistant_message = response.choices[0].message.content

    conversations[user_number].append({
        "role": "assistant",
        "content": assistant_message
    })

    return assistant_message

def send_whatsapp_update(to_number, message):
    """Send proactive WhatsApp message to customer"""
    from twilio.rest import Client
    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )
    client.messages.create(
        from_=os.getenv("TWILIO_WHATSAPP_NUMBER"),
        to=to_number,
        body=message
    )

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")
    incoming_lower = incoming_msg.lower()

    print(f"Message from {sender}: {incoming_msg}")

    resp = MessagingResponse()

    # Check operating hours
    if not is_open():
        reply = (
            "Sorry, we are currently closed \n\n"
            "Our operating hours are:\n"
            "8:00 AM - 10:00 PM daily\n\n"
            "We look forward to serving you tomorrow! "
        )
        resp.message(reply)
        return str(resp)

    # Handle order tracking
    if "track" in incoming_lower or incoming_msg.startswith("#MLK"):
        order_number = None
        words = incoming_msg.upper().split()
        for word in words:
            if word.startswith("#MLK"):
                order_number = word
                break

        if order_number:
            status = get_order_status(order_number)
            if status:
                resp.message(status)
            else:
                resp.message(
                    f"Order {order_number} not found.\n"
                    "Please check your order number and try again."
                )
        else:
            resp.message(
                "Please provide your order number.\n"
                "Example: Track #MLK-001"
            )
        return str(resp)

    # Handle repeat order
    if "order again" in incoming_lower or "same order" in incoming_lower:
        last_order = get_last_order(sender)
        if last_order:
            reply = (
                f"Here's your last order:\n"
                f"{last_order['items']}\n"
                f"Total = ₦{last_order['total']:,}\n\n"
                f"Should I place this order again? (Yes/No)"
            )
        else:
            reply = "No previous order found. What would you like to order?"
        resp.message(reply)
        return str(resp)

    # Handle complaint
    complaints = [
        "cold", "wrong order", "bad food",
        "not delivered", "missing item",
        "complaint", "problem", "issue"
    ]
    if any(word in incoming_lower for word in complaints):
        reply = (
            "We sincerely apologize for this experience \n\n"
            "Your complaint has been escalated to our manager.\n"
            "You will be contacted within 10 minutes.\n\n"
            "We value your patronage and will make this right!"
        )
        resp.message(reply)
        return str(resp)

    # Handle delivery address
    if waiting_for_address.get(sender):
        waiting_for_address[sender] = False

        # Get pending order details
        order_info = pending_orders.get(sender, {})
        items = order_info.get("items", "Your order")
        total = order_info.get("total", 0)

        # Create order with unique number
        order_number = create_order(sender, items, total)

        # Get real delivery time
        delivery_info = get_delivery_time(incoming_msg)

        reply = (
            f" Order Confirmed!\n\n"
            f" Order Number: {order_number}\n"
            f" Delivering to:\n{incoming_msg}\n\n"
            f" {delivery_info['message']}\n\n"
            f"You can track your order anytime by sending:\n"
            f"'Track {order_number}'\n\n"
            f"Thank you for choosing Mama Lagos Kitchen! "
        )

        # Send initial status update
        update_order_status(order_number, "preparing")
        resp.message(reply)
        return str(resp)

    # Handle payment confirmation
    if incoming_lower in ["sent", "done", "paid", "transferred"]:
        waiting_for_address[sender] = True

        # Extract order details from conversation
        last_ai_message = ""
        if sender in conversations:
            for msg in reversed(conversations[sender]):
                if msg["role"] == "assistant":
                    last_ai_message = msg["content"]
                    break

        # Store pending order
        pending_orders[sender] = {
            "items": "Order items",
            "total": 0
        }

        reply = (
            "Payment confirmed! \n\n"
            "Please send your delivery address:"
        )
        resp.message(reply)
        return str(resp)

    # All other messages handled by AI
    ai_response = get_ai_response(sender, incoming_msg)
    resp.message(ai_response)
    return str(resp)

@app.route("/update_status", methods=["POST"])
def update_status():
    """Endpoint to update order status and notify customer"""
    order_number = request.json.get("order_number")
    new_status = request.json.get("status")

    from orders import orders
    if order_number in orders:
        update_order_status(order_number, new_status)
        customer = orders[order_number]["customer"]

        status_messages = {
            "preparing": f" Update on {order_number}:\nYour food is being prepared!",
            "ready": f" Update on {order_number}:\nYour food is ready! Rider assigned.",
            "on_the_way": f" Update on {order_number}:\nYour rider is on the way!",
            "delivered": f" Update on {order_number}:\nYour order has been delivered!\nEnjoy your meal! 😊"
        }

        if new_status in status_messages:
            send_whatsapp_update(customer, status_messages[new_status])

        return {"success": True, "message": "Status updated"}
    return {"success": False, "message": "Order not found"}

@app.route("/", methods=["GET"])
def home():
    return "Mama Lagos Kitchen Bot is Running! "

if __name__ == "__main__":
    app.run(debug=True, port=5000)