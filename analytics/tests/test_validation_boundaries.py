"""Boundary-value tests for the Pydantic models in analytics/src/schemas/validation.py.

For every constrained field the tests check the values around each limit:
just below, on, and just above it (min-1, min, min+1, max-1, max, max+1).

Every rejection test also checks that the error is reported for the field under
test, so a case cannot pass because some *other* field happened to be invalid.
"""
import math
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
from pydantic import ValidationError

from analytics.src.schemas import validation
from analytics.src.schemas.validation import (
    RawDonationRecord,
    RawStreamMetricRecord,
    validate_donations_batch,
)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _s(length: int) -> str:
    """String of exactly `length` characters."""
    return "a" * length


def make_donation(**overrides) -> dict:
    payload = {
        "transaction_id": "tx_00001",
        "amount": 100.0,
        "currency": "RUB",
        "fund_type": "general",
        "created_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
    }
    payload.update(overrides)
    return payload


def make_stream(**overrides) -> dict:
    payload = {
        "stream_id": "stream_1",
        "service_name": "Sunday liturgy",
        "peak_viewers": 10,
        "avg_watch_time_seconds": 600,
        "chat_messages_count": 5,
        "donations_during_stream": 0.0,
    }
    payload.update(overrides)
    return payload


def assert_rejected_for(model, payload: dict, field: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        model(**payload)
    failed_fields = {err["loc"][0] for err in exc_info.value.errors() if err["loc"]}
    assert field in failed_fields, f"expected error on '{field}', got {failed_fields}"


FROZEN_NOW = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
ONE_MICROSECOND = timedelta(microseconds=1)


class _FrozenDatetime(datetime):
    """datetime whose now() is pinned, so the 'not in the future' edge is exact."""

    @classmethod
    def now(cls, tz=None):
        return FROZEN_NOW if tz is not None else FROZEN_NOW.replace(tzinfo=None)


@contextmanager
def frozen_now():
    with mock.patch.object(validation, "datetime", _FrozenDatetime):
        yield


# --------------------------------------------------------------------------- #
# RawDonationRecord: string length limits
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "length",
    [
        pytest.param(5, id="min"),
        pytest.param(6, id="min+1"),
        pytest.param(99, id="max-1"),
        pytest.param(100, id="max"),
    ],
)
def test_transaction_id_length_accepted(length):
    record = RawDonationRecord(**make_donation(transaction_id=_s(length)))
    assert len(record.transaction_id) == length


@pytest.mark.parametrize(
    "length",
    [
        pytest.param(0, id="empty"),
        pytest.param(4, id="min-1"),
        pytest.param(101, id="max+1"),
    ],
)
def test_transaction_id_length_rejected(length):
    assert_rejected_for(RawDonationRecord, make_donation(transaction_id=_s(length)), "transaction_id")


@pytest.mark.parametrize(
    "user_id",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param(_s(1), id="min+1"),
        pytest.param(_s(99), id="max-1"),
        pytest.param(_s(100), id="max"),
    ],
)
def test_user_id_accepted(user_id):
    assert RawDonationRecord(**make_donation(user_id=user_id)).user_id == user_id


def test_user_id_max_plus_one_rejected():
    assert_rejected_for(RawDonationRecord, make_donation(user_id=_s(101)), "user_id")


@pytest.mark.parametrize(
    "length",
    [
        pytest.param(0, id="empty"),
        pytest.param(1, id="min+1"),
        pytest.param(49, id="max-1"),
        pytest.param(50, id="max"),
    ],
)
def test_payment_method_length_accepted(length):
    record = RawDonationRecord(**make_donation(payment_method=_s(length)))
    assert len(record.payment_method) == length


def test_payment_method_max_plus_one_rejected():
    assert_rejected_for(RawDonationRecord, make_donation(payment_method=_s(51)), "payment_method")


def test_payment_method_defaults_to_card():
    assert RawDonationRecord(**make_donation()).payment_method == "card"


@pytest.mark.parametrize(
    "note_text",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param(_s(1), id="min+1"),
        pytest.param(_s(499), id="max-1"),
        pytest.param(_s(500), id="max"),
    ],
)
def test_note_text_accepted(note_text):
    assert RawDonationRecord(**make_donation(note_text=note_text)).note_text == note_text


def test_note_text_max_plus_one_rejected():
    assert_rejected_for(RawDonationRecord, make_donation(note_text=_s(501)), "note_text")


# --------------------------------------------------------------------------- #
# RawDonationRecord: amount (strictly greater than 0)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "amount",
    [
        pytest.param(0.01, id="just-above-zero"),
        pytest.param(1e-9, id="tiny-positive"),
        pytest.param(5e-324, id="smallest-positive-float"),
        pytest.param(1, id="int-one"),
        pytest.param(1_000_000.0, id="large"),
        pytest.param("0.01", id="numeric-string"),
    ],
)
def test_amount_accepted(amount):
    record = RawDonationRecord(**make_donation(amount=amount))
    assert record.amount > 0


@pytest.mark.parametrize(
    "amount",
    [
        pytest.param(0, id="zero-int"),
        pytest.param(0.0, id="zero"),
        pytest.param(-0.0, id="negative-zero"),
        pytest.param(-0.01, id="just-below-zero"),
        pytest.param(-1, id="minus-one"),
        pytest.param(-math.inf, id="minus-infinity"),
        pytest.param(math.nan, id="nan"),
        pytest.param("0", id="zero-string"),
        pytest.param("abc", id="not-a-number"),
        pytest.param(None, id="none"),
    ],
)
def test_amount_rejected(amount):
    assert_rejected_for(RawDonationRecord, make_donation(amount=amount), "amount")


def test_amount_is_required():
    payload = make_donation()
    del payload["amount"]
    assert_rejected_for(RawDonationRecord, payload, "amount")


@pytest.mark.xfail(
    strict=True,
    reason="DEFECT: float('inf') passes gt=0, so an infinite donation is accepted. "
    "Fix: Field(..., gt=0, allow_inf_nan=False). Remove this xfail after the fix.",
)
def test_amount_positive_infinity_rejected():
    assert_rejected_for(RawDonationRecord, make_donation(amount=math.inf), "amount")


# --------------------------------------------------------------------------- #
# RawDonationRecord: enums
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("currency", ["RUB", "BYN", "USD"])
def test_currency_accepted(currency):
    assert RawDonationRecord(**make_donation(currency=currency)).currency == currency


@pytest.mark.parametrize(
    "currency",
    [
        pytest.param("", id="empty"),
        pytest.param("rub", id="lowercase"),
        pytest.param("USD ", id="trailing-space"),
        pytest.param("EUR", id="unsupported"),
        pytest.param(None, id="none"),
    ],
)
def test_currency_rejected(currency):
    assert_rejected_for(RawDonationRecord, make_donation(currency=currency), "currency")


@pytest.mark.parametrize(
    "fund_type",
    ["general", "temple_restoration", "choir", "charity", "minecraft_church"],
)
def test_fund_type_accepted(fund_type):
    assert RawDonationRecord(**make_donation(fund_type=fund_type)).fund_type == fund_type


@pytest.mark.parametrize(
    "fund_type",
    [
        pytest.param("", id="empty"),
        pytest.param("GENERAL", id="uppercase"),
        pytest.param("general ", id="trailing-space"),
        pytest.param("unknown_fund", id="unsupported"),
        pytest.param(None, id="none"),
    ],
)
def test_fund_type_rejected(fund_type):
    assert_rejected_for(RawDonationRecord, make_donation(fund_type=fund_type), "fund_type")


# --------------------------------------------------------------------------- #
# RawDonationRecord: created_at (must not be in the future)
# The clock is frozen so "now" and "now + 1 microsecond" are exact edges.
# --------------------------------------------------------------------------- #

TZ_PLUS_3 = timezone(timedelta(hours=3))
TZ_MINUS_12 = timezone(timedelta(hours=-12))


@pytest.mark.parametrize(
    "created_at",
    [
        pytest.param(FROZEN_NOW - timedelta(days=365), id="year-ago"),
        pytest.param(FROZEN_NOW - timedelta(seconds=1), id="now-1s"),
        pytest.param(FROZEN_NOW - ONE_MICROSECOND, id="now-1us"),
        pytest.param(FROZEN_NOW, id="exactly-now"),
        pytest.param(FROZEN_NOW.astimezone(TZ_PLUS_3), id="exactly-now-utc+3"),
        pytest.param(FROZEN_NOW.astimezone(TZ_MINUS_12), id="exactly-now-utc-12"),
        pytest.param(FROZEN_NOW.replace(tzinfo=None), id="naive-exactly-now-as-utc"),
        pytest.param(datetime(1970, 1, 1, tzinfo=timezone.utc), id="unix-epoch"),
        pytest.param("2026-09-30T12:00:00Z", id="iso-string-exactly-now"),
    ],
)
def test_created_at_not_in_future_accepted(created_at):
    with frozen_now():
        record = RawDonationRecord(**make_donation(created_at=created_at))
    assert record.created_at.tzinfo is not None
    assert record.created_at <= FROZEN_NOW


@pytest.mark.parametrize(
    "created_at",
    [
        pytest.param(FROZEN_NOW + ONE_MICROSECOND, id="now+1us"),
        pytest.param(FROZEN_NOW + timedelta(seconds=1), id="now+1s"),
        pytest.param(FROZEN_NOW + timedelta(days=1), id="tomorrow"),
        pytest.param((FROZEN_NOW + ONE_MICROSECOND).astimezone(TZ_PLUS_3), id="now+1us-utc+3"),
        pytest.param((FROZEN_NOW + ONE_MICROSECOND).astimezone(TZ_MINUS_12), id="now+1us-utc-12"),
        pytest.param((FROZEN_NOW + ONE_MICROSECOND).replace(tzinfo=None), id="naive-now+1us-as-utc"),
        pytest.param("2999-01-01T00:00:00Z", id="iso-string-far-future"),
    ],
)
def test_created_at_in_future_rejected(created_at):
    with frozen_now():
        with pytest.raises(ValidationError, match="Transaction timestamp cannot be in the future"):
            RawDonationRecord(**make_donation(created_at=created_at))


def test_created_at_naive_datetime_is_treated_as_utc():
    naive = datetime(2020, 5, 17, 8, 30, 0)
    with frozen_now():
        record = RawDonationRecord(**make_donation(created_at=naive))
    assert record.created_at == naive.replace(tzinfo=timezone.utc)
    assert record.created_at.utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    "created_at",
    [
        pytest.param("", id="empty-string"),
        pytest.param("not-a-date", id="garbage-string"),
        pytest.param("2026-13-01T00:00:00Z", id="month-13"),
        pytest.param("2026-02-30T00:00:00Z", id="feb-30"),
        pytest.param(None, id="none"),
    ],
)
def test_created_at_invalid_value_rejected(created_at):
    assert_rejected_for(RawDonationRecord, make_donation(created_at=created_at), "created_at")


# --------------------------------------------------------------------------- #
# RawStreamMetricRecord
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "length",
    [
        pytest.param(3, id="min"),
        pytest.param(4, id="min+1"),
        pytest.param(99, id="max-1"),
        pytest.param(100, id="max"),
    ],
)
def test_stream_id_length_accepted(length):
    record = RawStreamMetricRecord(**make_stream(stream_id=_s(length)))
    assert len(record.stream_id) == length


@pytest.mark.parametrize(
    "length",
    [
        pytest.param(0, id="empty"),
        pytest.param(2, id="min-1"),
        pytest.param(101, id="max+1"),
    ],
)
def test_stream_id_length_rejected(length):
    assert_rejected_for(RawStreamMetricRecord, make_stream(stream_id=_s(length)), "stream_id")


@pytest.mark.parametrize(
    "length",
    [
        pytest.param(0, id="empty"),
        pytest.param(1, id="min+1"),
        pytest.param(149, id="max-1"),
        pytest.param(150, id="max"),
    ],
)
def test_service_name_length_accepted(length):
    record = RawStreamMetricRecord(**make_stream(service_name=_s(length)))
    assert len(record.service_name) == length


def test_service_name_max_plus_one_rejected():
    assert_rejected_for(RawStreamMetricRecord, make_stream(service_name=_s(151)), "service_name")


COUNTER_FIELDS = ["peak_viewers", "avg_watch_time_seconds", "chat_messages_count"]


@pytest.mark.parametrize("field", COUNTER_FIELDS)
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(0, id="min"),
        pytest.param(1, id="min+1"),
        pytest.param(2**31 - 1, id="int32-max"),
        pytest.param("0", id="zero-string"),
    ],
)
def test_counter_fields_accepted(field, value):
    record = RawStreamMetricRecord(**make_stream(**{field: value}))
    assert getattr(record, field) >= 0


@pytest.mark.parametrize("field", COUNTER_FIELDS)
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(-1, id="min-1"),
        pytest.param(-(2**31), id="int32-min"),
        pytest.param("-1", id="minus-one-string"),
        pytest.param(1.5, id="fractional"),
        pytest.param("1.5", id="fractional-string"),
        pytest.param(None, id="none"),
    ],
)
def test_counter_fields_rejected(field, value):
    assert_rejected_for(RawStreamMetricRecord, make_stream(**{field: value}), field)


@pytest.mark.parametrize("field", COUNTER_FIELDS)
def test_counter_fields_are_required(field):
    payload = make_stream()
    del payload[field]
    assert_rejected_for(RawStreamMetricRecord, payload, field)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(0.0, id="min"),
        pytest.param(-0.0, id="negative-zero"),
        pytest.param(0, id="int-zero"),
        pytest.param(0.01, id="min+0.01"),
        pytest.param(1_000_000.5, id="large"),
    ],
)
def test_donations_during_stream_accepted(value):
    record = RawStreamMetricRecord(**make_stream(donations_during_stream=value))
    assert record.donations_during_stream >= 0


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(-0.01, id="min-0.01"),
        pytest.param(-1, id="minus-one"),
        pytest.param(-math.inf, id="minus-infinity"),
        pytest.param(math.nan, id="nan"),
        pytest.param("abc", id="not-a-number"),
        pytest.param(None, id="none"),
    ],
)
def test_donations_during_stream_rejected(value):
    assert_rejected_for(
        RawStreamMetricRecord, make_stream(donations_during_stream=value), "donations_during_stream"
    )


@pytest.mark.xfail(
    strict=True,
    reason="DEFECT: float('inf') passes ge=0.0, so infinite stream donations are accepted. "
    "Fix: Field(..., ge=0.0, allow_inf_nan=False). Remove this xfail after the fix.",
)
def test_donations_during_stream_positive_infinity_rejected():
    assert_rejected_for(
        RawStreamMetricRecord, make_stream(donations_during_stream=math.inf), "donations_during_stream"
    )


# --------------------------------------------------------------------------- #
# validate_donations_batch: edges of the batch itself
# --------------------------------------------------------------------------- #


def test_batch_empty_list():
    assert validate_donations_batch([]) == ([], [])


def test_batch_single_valid_record():
    valid, bad = validate_donations_batch([make_donation()])
    assert len(valid) == 1
    assert bad == []


def test_batch_single_invalid_record():
    valid, bad = validate_donations_batch([make_donation(amount=0)])
    assert valid == []
    assert len(bad) == 1


def test_batch_splits_records_on_the_amount_boundary():
    items = [
        make_donation(transaction_id="tx_below", amount=0),
        make_donation(transaction_id="tx_above", amount=0.01),
    ]
    valid, bad = validate_donations_batch(items)
    assert [r.transaction_id for r in valid] == ["tx_above"]
    assert len(bad) == 1
    assert bad[0]["raw_data"] is items[0]
    assert "amount" in bad[0]["error"]


def test_batch_splits_records_on_the_transaction_id_length_boundary():
    items = [
        make_donation(transaction_id=_s(4)),
        make_donation(transaction_id=_s(5)),
        make_donation(transaction_id=_s(100)),
        make_donation(transaction_id=_s(101)),
    ]
    valid, bad = validate_donations_batch(items)
    assert [len(r.transaction_id) for r in valid] == [5, 100]
    assert [len(b["raw_data"]["transaction_id"]) for b in bad] == [4, 101]


def test_batch_preserves_input_order():
    items = [make_donation(transaction_id=f"tx_{i:05d}") for i in range(20)]
    valid, bad = validate_donations_batch(items)
    assert bad == []
    assert [r.transaction_id for r in valid] == [i["transaction_id"] for i in items]


@pytest.mark.parametrize(
    "item",
    [
        pytest.param({}, id="empty-dict"),
        pytest.param(None, id="none"),
        pytest.param("not-a-dict", id="string"),
    ],
)
def test_batch_malformed_items_go_to_bad_records_without_raising(item):
    valid, bad = validate_donations_batch([item, make_donation()])
    assert len(valid) == 1
    assert len(bad) == 1
    assert bad[0]["raw_data"] is item
    assert bad[0]["error"]
