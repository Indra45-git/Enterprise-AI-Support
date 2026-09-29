# Enterprise Order Cancellation Policy

## 1. Instant Pre-Dispatch Cancellation
Customers may cancel an order immediately with zero penalty under the following deterministic conditions:
- The order's `cancellable` flag is set to **true** in the ERP order management system.
- The order status is currently in **"Processing"** or **"Confirmed"**.
- The package has not yet been handed over to the courier hub for transit.

## 2. Dispatch Lock Rule
- Once an order transitions to **"Shipped"** or **"Out for Delivery"**, cancellation is automatically **locked**.
- At this stage, couriers cannot recall parcels in transit.
- Customers wishing to return the item should accept delivery and immediately initiate a return within the standard 10-day return window.

## 3. Cancellation Refund Processing
- For prepaid orders (UPI, Card, Net Banking), cancellation automatically initiates an instant reversal refund.
- Funds are credited back to the original source within **24 to 48 hours** for UPI, and **3 to 5 business days** for card transactions.

## 4. How to Request Cancellation
You can request cancellation directly through:
1. **AI Chat Studio**: Say *"Cancel order ORD00012"* — the agent will verify eligibility and initiate the cancellation.
2. **Order Dashboard**: Click on the order card and submit a cancellation ticket under "Orders & Tracking".
