from enum import StrEnum


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"


class LedgerType(StrEnum):
    TOPUP = "TOPUP"       # пополнение (через Stars)
    DEBIT = "DEBIT"       # списание (твоя логика биллинга/тарификации)
    REFUND = "REFUND"      # возврат средств пользователю
    ADJUSTMENT = "ADJUSTMENT"  # ручная корректировка (админ)
    BONUS = "BONUS"


class RefundStatus(StrEnum):
    REQUESTED = "REQUESTED"
    OK = "OK"
    FAILED = "FAILED"
