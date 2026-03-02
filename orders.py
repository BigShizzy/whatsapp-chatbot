import random
import string
from datetime import datetime

# Store all orders in memory
orders = {}
customer_last_order = {}

def generate_order_number():
    """Generate unique order number like #MLK-001"""
    number = ''.join(random.choices(string.digits, k=3))
    return f"#MLK-{number}"

def create_order(customer_number, items, total):
    """Create a new order"""
    order_number = generate_order_number()
    orders[order_number] = {
        "order_number": order_number,
        "customer": customer_number,
        "items": items,
        "total": total,
        "status": "received",
        "time": datetime.now().strftime("%I:%M %p"),
        "date": datetime.now().strftime("%d/%m/%Y")
    }
    # Save as customer's last order
    customer_last_order[customer_number] = {
        "items": items,
        "total": total
    }
    return order_number

def get_order_status(order_number):
    """Get current status of an order"""
    if order_number in orders:
        order = orders[order_number]
        status = order["status"]

        status_messages = {
            "received": " Order received and confirmed",
            "preparing": " Your food is being prepared",
            "ready": " Your food is ready and waiting for rider",
            "on_the_way": " Your rider is on the way",
            "delivered": " Your order has been delivered"
        }

        return f"Order {order_number}\n{status_messages.get(status, 'Status unknown')}"
    return None

def get_last_order(customer_number):
    """Get customer's last order"""
    return customer_last_order.get(customer_number)

def update_order_status(order_number, new_status):
    """Update order status"""
    if order_number in orders:
        orders[order_number]["status"] = new_status
        return True
    return False