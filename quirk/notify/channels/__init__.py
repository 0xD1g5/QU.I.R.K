"""quirk.notify.channels — Delivery channel senders (Phase 101 NOTIFY-03/04/05).

Each channel is isolated in its own module.  Import only the sender you need:

    from quirk.notify.channels.slack import send_slack
    from quirk.notify.channels.email import send_email
    from quirk.notify.channels.webhook import send_webhook
"""
