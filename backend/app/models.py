from sqlalchemy import Column, String, Integer, Float, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String)
    city = Column(String)
    state = Column(String)
    pincode = Column(String)
    customer_tier = Column(String)
    created_at = Column(Date)
    password_hash = Column(String)  # seeded with a demo password; never sent to the LLM

    orders = relationship("Order", back_populates="customer")
    tickets = relationship("SupportTicket", back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    product_id = Column(String, primary_key=True)
    product_name = Column(String, nullable=False)
    category = Column(String)
    price = Column(Float)
    stock_quantity = Column(Integer)
    warranty_months = Column(Integer)
    returnable = Column(Boolean)


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False, index=True)
    status = Column(String)
    total_amount = Column(Float)
    payment_status = Column(String)
    payment_method = Column(String)
    order_date = Column(Date)
    expected_delivery = Column(Date)
    cancellable = Column(Boolean)
    tracking_number = Column(String)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    tickets = relationship("SupportTicket", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id = Column(String, primary_key=True)
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.product_id"), nullable=False, index=True)
    quantity = Column(Integer)
    unit_price = Column(Float)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    ticket_id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False, index=True)
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=True)
    issue_type = Column(String)
    description = Column(String)
    priority = Column(String)
    status = Column(String)
    assigned_to = Column(String)
    created_at = Column(Date)
    escalation_reason = Column(String, nullable=True)  # set by escalate_ticket tool

    customer = relationship("Customer", back_populates="tickets")
    order = relationship("Order", back_populates="tickets")


class ChatbotSetting(Base):
    """Chatbot customization settings (matching tutorial features for embeddable SaaS)."""
    __tablename__ = "chatbot_settings"

    bot_id = Column(String, primary_key=True, default="default")
    bot_name = Column(String, default="Apex AI Support")
    welcome_message = Column(String, default="Hello! 👋 I'm your AI customer support assistant. How can I help you today?")
    primary_color = Column(String, default="#6366f1")
    secondary_color = Column(String, default="#4f46e5")
    avatar_icon = Column(String, default="🤖")
    placeholder_text = Column(String, default="Ask about orders, returns, tracking, policies…")
    suggested_questions = Column(String, default="Where is my order ORD00012?|What is your return policy?|Can I return an item?|Open a support ticket")
    system_instructions = Column(String, default="You are an enterprise AI support assistant. Answer accurately based on verified company policy and database results.")
    is_public = Column(Boolean, default=True)


class ChatSession(Base):
    """Session tracking for customer and public widget conversations."""
    __tablename__ = "chat_sessions"

    session_id = Column(String, primary_key=True)
    customer_id = Column(String, nullable=True, index=True)
    bot_id = Column(String, default="default")
    created_at = Column(Date)
    last_active = Column(Date)


class ChatMessage(Base):
    """Message history for sessions."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"), index=True)
    sender = Column(String)  # "user" | "bot" | "guardrail"
    content = Column(String)
    created_at = Column(Date)

