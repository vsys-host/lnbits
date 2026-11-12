ARG LNBITS_VERSION=v1.7.1
FROM lnbits/lnbits:${LNBITS_VERSION}

# Copy setup script into the image
COPY setup_lnbits.py /app/setup_lnbits.py
