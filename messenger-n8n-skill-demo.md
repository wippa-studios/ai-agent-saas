# Messenger + n8n AI Agent: Demo Gallery

This gallery demonstrates a safe deployment pattern for a Facebook Messenger sales and customer-service agent backed by n8n. All values are fictional samples. The demonstrations are offline simulations: they do not publish a workflow, send Messenger messages, or write orders, payments, or stock.

## The common pipeline

```text
Meta Messenger webhook
  → immediate HTTP 200 acknowledgement
  → normalize event
  → ignore Page echoes / receipts
  → deduplicate by message ID
  → load customer and conversation state
  → look up catalog and delivery data
  → calculate stock, price tier, subtotal, and delivery fee deterministically
  → ask AI for language, intent, missing fields, and concise wording
  → approval router
  → draft Messenger response or staff handoff
```

The AI is a language and judgment layer. It does not invent stock, prices, discounts, payment confirmation, delivery fees, or order status.

## Safety requirements

- Keep workflows inactive during simulation.
- Deduplicate Messenger event IDs before AI processing and before any Send API call.
- Treat payment screenshots as unverified evidence requiring staff review.
- Never promise quantities above available stock.
- Require human approval for refunds, disputes, discounts, shortages, stale data, large orders, and payment evidence.
- Add the live Send API only after credentials, durable deduplication, catalog storage, approval routing, and test coverage are ready.

## Structured AI response contract

```json
{
  "language": "my|en|mixed",
  "intent": "product_question|price_request|stock_question|retail_order|wholesale_inquiry|payment_question|human_handoff|other",
  "customer_type": "retail|wholesale|unknown",
  "confidence": 0.0,
  "reply_text": "",
  "needs_human": false,
  "handoff_reason": "",
  "order_draft": {"status": "not_started|missing_information|awaiting_customer_confirmation|awaiting_staff_approval|confirmed"},
  "missing_information": [],
  "warnings": []
}
```

Arrays should declare string items explicitly, absent values should use empty strings rather than nullable unions, and approval-relevant fields should be required.

## Recommended rollout

Start with 7–14 days of draft and human-approval mode. Test valid questions, shortages, invalid products, incomplete addresses, discounts, payment screenshots, refunds, duplicate events, Page echoes, and attachment-only messages. Then enable autonomous replies only for low-risk catalog and availability questions.
