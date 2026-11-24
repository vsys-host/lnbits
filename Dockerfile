ARG LNBITS_VERSION=v1.7.1
FROM lnbits/lnbits:${LNBITS_VERSION}

# Copy setup script into the image
COPY setup_lnbits.py /app/setup_lnbits.py

# Pay zero-amount BOLT11 invoices when the API request includes amount (sats).
COPY patches/allow_amountless_invoices.py /tmp/allow_amountless_invoices.py
RUN /app/.venv/bin/python /tmp/allow_amountless_invoices.py \
    && rm /tmp/allow_amountless_invoices.py
