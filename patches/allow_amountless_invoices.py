#!/usr/bin/env python3
"""Let LNbits pay a zero-amount BOLT11 when the request includes amount in sats.

Upstream rejects those invoices before looking at the amount field. SHKeeper
sends the payout amount there so a fee split can pay admin and merchant
invoices that were created with lncli addinvoice --amt 0.
"""

from pathlib import Path

APP = Path("/app")


def replace_once(path: Path, old: str, new: str) -> None:
    file = APP / path
    text = file.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{file}: expected 1 match, found {count}")
    file.write_text(text.replace(old, new, 1))


def main() -> None:
    replace_once(
        Path("lnbits/core/services/payments.py"),
        """    force_resend: bool | None = False,
    conn: Connection | None = None,
) -> Payment:
    if settings.lnbits_only_allow_incoming_payments:
        raise PaymentError("Only incoming payments allowed.", status="failed")

    invoice = _validate_payment_request(payment_request, max_sat)
""",
        """    force_resend: bool | None = False,
    conn: Connection | None = None,
    amount_sat: int | None = None,
) -> Payment:
    if settings.lnbits_only_allow_incoming_payments:
        raise PaymentError("Only incoming payments allowed.", status="failed")

    invoice = _validate_payment_request(
        payment_request, max_sat, amount_sat=amount_sat
    )
""",
    )
    replace_once(
        Path("lnbits/core/services/payments.py"),
        """            _fundingsource_pay_invoice(checking_id, payment.bolt11, fee_reserve_msat),
""",
        """            _fundingsource_pay_invoice(
                checking_id,
                payment.bolt11,
                fee_reserve_msat,
                abs(int(amount_msat)),
            ),
""",
    )
    replace_once(
        Path("lnbits/core/services/payments.py"),
        """async def _fundingsource_pay_invoice(
    checking_id: str, bolt11: str, fee_reserve_msat: int
) -> PaymentResponse:
    logger.debug(f"fundingsource: sending payment {checking_id}")
    funding_source = get_funding_source()
    payment_response: PaymentResponse = await funding_source.pay_invoice(
        bolt11, fee_reserve_msat
    )
""",
        """async def _fundingsource_pay_invoice(
    checking_id: str,
    bolt11: str,
    fee_reserve_msat: int,
    amount_msat: int = 0,
) -> PaymentResponse:
    logger.debug(f"fundingsource: sending payment {checking_id}")
    funding_source = get_funding_source()
    pay_kwargs = {}
    try:
        import inspect

        if "amount_msat" in inspect.signature(funding_source.pay_invoice).parameters:
            pay_kwargs["amount_msat"] = amount_msat
    except (TypeError, ValueError):
        pay_kwargs = {}
    payment_response: PaymentResponse = await funding_source.pay_invoice(
        bolt11, fee_reserve_msat, **pay_kwargs
    )
""",
    )
    replace_once(
        Path("lnbits/core/services/payments.py"),
        """def _validate_payment_request(
    payment_request: str, max_sat: int | None = None
) -> ValidatedPaymentRequest:
    try:
        invoice = bolt11_decode(payment_request)
    except Exception as exc:
        raise PaymentError("Bolt11 decoding failed.", status="failed") from exc

    if not invoice.amount_msat or not invoice.amount_msat > 0:
        raise PaymentError("Amountless invoices not supported.", status="failed")

    max_sat = max_sat or settings.lnbits_max_outgoing_payment_amount_sats
    max_sat = min(max_sat, settings.lnbits_max_outgoing_payment_amount_sats)
    if invoice.amount_msat > max_sat * 1000:
        raise PaymentError(
            f"Invoice amount {invoice.amount_msat // 1000} sats is too high. "
            f"Max allowed: {max_sat} sats.",
            status="failed",
        )

    return ValidatedPaymentRequest(
        payment_request=payment_request,
        amount_msat=invoice.amount_msat,
        payment_hash=invoice.payment_hash,
        expiry_date=invoice.expiry_date,
        description=invoice.description or "",
        is_offer=False,
    )
""",
        """def _validate_payment_request(
    payment_request: str,
    max_sat: int | None = None,
    amount_sat: int | None = None,
) -> ValidatedPaymentRequest:
    try:
        invoice = bolt11_decode(payment_request)
    except Exception as exc:
        raise PaymentError("Bolt11 decoding failed.", status="failed") from exc

    # A zero-amount bolt11 is payable when the caller supplies the sats.
    amount_msat = int(invoice.amount_msat or 0)
    if amount_msat <= 0:
        if amount_sat is None or int(amount_sat) <= 0:
            raise PaymentError("Amountless invoices not supported.", status="failed")
        amount_msat = int(amount_sat) * 1000

    max_sat = max_sat or settings.lnbits_max_outgoing_payment_amount_sats
    max_sat = min(max_sat, settings.lnbits_max_outgoing_payment_amount_sats)
    if amount_msat > max_sat * 1000:
        raise PaymentError(
            f"Invoice amount {amount_msat // 1000} sats is too high. "
            f"Max allowed: {max_sat} sats.",
            status="failed",
        )

    return ValidatedPaymentRequest(
        payment_request=payment_request,
        amount_msat=amount_msat,
        payment_hash=invoice.payment_hash,
        expiry_date=invoice.expiry_date,
        description=invoice.description or "",
        is_offer=False,
    )
""",
    )
    replace_once(
        Path("lnbits/core/views/payment_api.py"),
        """        payment = await pay_invoice(
            wallet_id=wallet_id,
            payment_request=invoice_data.payment_request,
            extra=invoice_data.extra,
            description=invoice_data.memo or "",
            labels=invoice_data.labels,
            external_id=invoice_data.external_id,
            webhook=invoice_data.webhook,
        )
""",
        """        amount_sat = None
        if invoice_data.amount is not None and invoice_data.unit == "sat":
            amount_sat = int(invoice_data.amount)
        payment = await pay_invoice(
            wallet_id=wallet_id,
            payment_request=invoice_data.payment_request,
            extra=invoice_data.extra,
            description=invoice_data.memo or "",
            labels=invoice_data.labels,
            external_id=invoice_data.external_id,
            webhook=invoice_data.webhook,
            amount_sat=amount_sat,
        )
""",
    )
    replace_once(
        Path("lnbits/core/views/payment_api.py"),
        """    return await pay_invoice(
        wallet_id=payment.wallet_id,
        payment_request=payment.bolt11,
        force_resend=True,
    )
""",
        """    return await pay_invoice(
        wallet_id=payment.wallet_id,
        payment_request=payment.bolt11,
        force_resend=True,
        amount_sat=abs(payment.amount) // 1000,
    )
""",
    )
    replace_once(
        Path("lnbits/wallets/lndrest.py"),
        """    async def pay_invoice(self, bolt11: str, fee_limit_msat: int) -> PaymentResponse:
        req = {
            "payment_request": bolt11,
            "fee_limit_msat": fee_limit_msat,
            "timeout_seconds": 30,
            "no_inflight_updates": True,
        }
        if settings.lnd_rest_allow_self_payment:
            req["allow_self_payment"] = True
""",
        """    async def pay_invoice(
        self, bolt11: str, fee_limit_msat: int, amount_msat: int | None = None
    ) -> PaymentResponse:
        req = {
            "payment_request": bolt11,
            "fee_limit_msat": fee_limit_msat,
            "timeout_seconds": 30,
            "no_inflight_updates": True,
        }
        if amount_msat:
            from bolt11 import decode as bolt11_decode

            decoded = bolt11_decode(bolt11)
            if not decoded.amount_msat:
                # LND REST encodes int64 as a string.
                req["amt_msat"] = str(int(amount_msat))
        if settings.lnd_rest_allow_self_payment:
            req["allow_self_payment"] = True
""",
    )
    print("amountless invoice patch applied")


if __name__ == "__main__":
    main()
