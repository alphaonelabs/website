"""
Tests for Cart, Checkout, and Donation API handlers:
  * api_get_cart()
  * api_add_cart_item()
  * api_remove_cart_item()
  * api_clear_cart()
  * api_create_checkout()
  * api_complete_checkout()
  * api_create_donation_checkout()
"""

import json
import time
from unittest.mock import AsyncMock, patch
import pytest

from tests.helpers import (
    load_worker,
    MockRequest,
    MockRow,
    MockDB,
    make_env,
    make_stmt,
    json_request,
)

worker = load_worker()

JWT_SECRET = "test-jwt-secret"
VALID_GUEST_TOKEN = "gct_12345678901234567890123456"


def _parse(resp):
    return json.loads(resp.body)


def _user_token(uid="usr-1", username="alice", role="member"):
    return worker.create_token(uid, username, role, JWT_SECRET)


def _user_headers(uid="usr-1", username="alice", role="member"):
    return {"Authorization": f"Bearer {_user_token(uid, username, role)}"}


def _guest_headers(token=VALID_GUEST_TOKEN):
    return {
        "X-Guest-Cart": token,
        "User-Agent": "Mozilla/5.0 TestBrowser",
    }


def _guest_human_payload(extra=None):
    now_ms = int(time.time() * 1000)
    data = {
        "human_started_at": now_ms - 1000,
        "human_confirmed_at": now_ms,
    }
    if extra:
        data.update(extra)
    return data


# ===========================================================================
# 1. api_get_cart()
# ===========================================================================

class TestApiGetCart:
    def _req(self, headers=None):
        return MockRequest(method="GET", url="http://localhost/api/cart", headers=headers or {})

    async def test_unauthenticated_without_guest_token_returns_401(self):
        env = make_env()
        r = await worker.api_get_cart(self._req(), env)
        assert r.status == 401
        data = _parse(r)
        assert data["error"] == "Authentication or guest cart token required"

    async def test_guest_get_cart_empty_when_no_active_cart(self):
        env = make_env(db=MockDB([
            make_stmt(first=None),  # SELECT id FROM activity_carts WHERE guest_id=...
        ]))
        r = await worker.api_get_cart(self._req(headers=_guest_headers()), env)
        assert r.status == 200
        data = _parse(r)
        assert data["cart"] is None
        assert data["items"] == []
        assert data["subtotal_cents"] == 0
        assert data["owner_kind"] == "guest"

    async def test_authenticated_get_cart_empty(self):
        env = make_env(db=MockDB([
            make_stmt(first=None),  # SELECT id FROM activity_carts WHERE user_id=...
        ]))
        r = await worker.api_get_cart(self._req(headers=_user_headers()), env)
        assert r.status == 200
        data = _parse(r)
        assert data["cart"] is None
        assert data["items"] == []
        assert data["subtotal_cents"] == 0
        assert data["owner_kind"] == "user"

    async def test_authenticated_get_cart_with_items_calculates_subtotal(self):
        cart_row = MockRow(id="cart-100")
        item1 = MockRow(
            id="ci-1",
            activity_id="act-1",
            session_id="",
            quantity=2,
            unit_price_cents=1500,
            title_snapshot="Python Course",
            title="Python Course",
            status="published",
            slug="python-course",
            image_url="",
        )
        item2 = MockRow(
            id="ci-2",
            activity_id="act-2",
            session_id="sess-1",
            quantity=1,
            unit_price_cents=3000,
            title_snapshot="Data Science Workshop",
            title="Data Science Workshop",
            status="published",
            slug="ds-workshop",
            image_url="",
        )

        env = make_env(db=MockDB([
            make_stmt(first=cart_row),         # SELECT id FROM activity_carts
            make_stmt(all_results=[item1, item2]),  # SELECT ... FROM activity_cart_items
        ]))
        r = await worker.api_get_cart(self._req(headers=_user_headers()), env)
        assert r.status == 200
        data = _parse(r)
        assert data["cart"]["id"] == "cart-100"
        assert len(data["items"]) == 2
        # (2 * 1500) + (1 * 3000) = 3000 + 3000 = 6000 cents ($60.00)
        assert data["subtotal_cents"] == 6000
        assert data["currency"] == "USD"
        assert data["items"][0]["line_total_cents"] == 3000
        assert data["items"][1]["line_total_cents"] == 3000


# ===========================================================================
# 2. api_add_cart_item()
# ===========================================================================

class TestApiAddCartItem:
    def _req(self, payload, headers=None):
        return json_request("/api/cart/items", payload, headers=headers or {})

    async def test_missing_activity_id_returns_400(self):
        env = make_env()
        r = await worker.api_add_cart_item(self._req({}, headers=_user_headers()), env)
        assert r.status == 400
        data = _parse(r)
        assert "activity_id is required" in data["error"]

    async def test_activity_not_found_returns_404(self):
        env = make_env(db=MockDB([
            make_stmt(first=None),  # SELECT id,title,price_cents,status FROM activities
        ]))
        r = await worker.api_add_cart_item(
            self._req({"activity_id": "act-nonexistent"}, headers=_user_headers()), env
        )
        assert r.status == 404
        data = _parse(r)
        assert data["error"] == "Activity not found"

    async def test_waitlist_activity_rejected_with_400(self):
        act_row = MockRow(id="act-wl", title="Waitlist Activity", price_cents=1000, status="waitlist")
        env = make_env(db=MockDB([
            make_stmt(first=act_row),  # SELECT id,title,price_cents,status FROM activities
        ]))
        r = await worker.api_add_cart_item(
            self._req({"activity_id": "act-wl"}, headers=_user_headers()), env
        )
        assert r.status == 400
        data = _parse(r)
        assert "waiting room" in data["error"]

    async def test_guest_without_human_check_returns_429(self):
        act_row = MockRow(id="act-1", title="Intro to Robotics", price_cents=2000, status="published")
        env = make_env(db=MockDB([
            make_stmt(first=act_row),
        ]))
        # Missing human_started_at and human_confirmed_at -> elapsed < 350ms
        r = await worker.api_add_cart_item(
            self._req({"activity_id": "act-1"}, headers=_guest_headers()), env
        )
        assert r.status == 429
        data = _parse(r)
        assert data["error"] == "Please try again"

    async def test_guest_honeypot_field_returns_429(self):
        act_row = MockRow(id="act-1", title="Intro to Robotics", price_cents=2000, status="published")
        env = make_env(db=MockDB([
            make_stmt(first=act_row),
        ]))
        payload = _guest_human_payload({"activity_id": "act-1", "website": "https://spambot.com"})
        r = await worker.api_add_cart_item(self._req(payload, headers=_guest_headers()), env)
        assert r.status == 429
        data = _parse(r)
        assert "human check" in data["error"]

    async def test_authenticated_successful_add_item_creates_cart_if_needed(self):
        act_row = MockRow(id="act-1", title="Intro to Robotics", price_cents=2000, status="published")
        item_row = MockRow(
            id="ci-1",
            activity_id="act-1",
            session_id="",
            quantity=1,
            unit_price_cents=2000,
            title_snapshot="Intro to Robotics",
            title="Intro to Robotics",
            status="published",
            slug="intro-to-robotics",
            image_url="",
        )

        env = make_env(db=MockDB([
            make_stmt(first=act_row),   # 1. SELECT activity
            make_stmt(first=None),      # 2. SELECT active cart (not found -> create)
            make_stmt(),                # 3. INSERT INTO activity_carts
            make_stmt(),                # 4. INSERT OR IGNORE INTO activity_cart_items
            make_stmt(),                # 5. UPDATE activity_carts set updated_at
            make_stmt(first=MockRow(id="cart-new")),  # 6. _cart_payload -> _active_cart_id
            make_stmt(all_results=[item_row]),        # 7. _cart_payload -> SELECT items
        ]))

        r = await worker.api_add_cart_item(
            self._req({"activity_id": "act-1"}, headers=_user_headers()), env
        )
        assert r.status == 200
        data = _parse(r)
        assert len(data["items"]) == 1
        assert data["items"][0]["activity_id"] == "act-1"
        assert data["subtotal_cents"] == 2000

    async def test_guest_successful_add_item_with_human_verification(self):
        act_row = MockRow(id="act-1", title="Python 101", price_cents=0, status="published")
        cart_row = MockRow(id="cart-guest")
        item_row = MockRow(
            id="ci-g1",
            activity_id="act-1",
            session_id="",
            quantity=1,
            unit_price_cents=0,
            title_snapshot="Python 101",
            title="Python 101",
            status="published",
            slug="python-101",
            image_url="",
        )

        env = make_env(db=MockDB([
            make_stmt(first=act_row),   # 1. SELECT activity
            make_stmt(first=cart_row),  # 2. SELECT active cart (found)
            make_stmt(first=MockRow(cnt=1)), # 3. Guest cart items count check (<20)
            make_stmt(),                # 4. INSERT item
            make_stmt(),                # 5. UPDATE cart
            make_stmt(first=cart_row),  # 6. _cart_payload -> SELECT active cart
            make_stmt(all_results=[item_row]),  # 7. _cart_payload -> SELECT items
        ]))

        payload = _guest_human_payload({"activity_id": "act-1"})
        r = await worker.api_add_cart_item(self._req(payload, headers=_guest_headers()), env)
        assert r.status == 200
        data = _parse(r)
        assert data["owner_kind"] == "guest"
        assert len(data["items"]) == 1

    async def test_guest_cart_limit_20_activities_exceeded_returns_400(self):
        act_row = MockRow(id="act-1", title="Python 101", price_cents=0, status="published")
        cart_row = MockRow(id="cart-guest")

        env = make_env(db=MockDB([
            make_stmt(first=act_row),   # 1. SELECT activity
            make_stmt(first=cart_row),  # 2. SELECT active cart
            make_stmt(first=MockRow(cnt=20)), # 3. Guest cart item count is already 20!
        ]))

        payload = _guest_human_payload({"activity_id": "act-1"})
        r = await worker.api_add_cart_item(self._req(payload, headers=_guest_headers()), env)
        assert r.status == 400
        data = _parse(r)
        assert "limited to 20 activities" in data["error"]


# ===========================================================================
# 3. api_remove_cart_item()
# ===========================================================================

class TestApiRemoveCartItem:
    def _req(self, item_id, headers=None):
        return MockRequest(method="DELETE", url=f"http://localhost/api/cart/items/{item_id}", headers=headers or {})

    async def test_unauthenticated_without_guest_token_returns_401(self):
        env = make_env()
        r = await worker.api_remove_cart_item(self._req("ci-1"), env, "ci-1")
        assert r.status == 401

    async def test_remove_cart_item_when_no_active_cart_returns_empty_payload(self):
        env = make_env(db=MockDB([
            make_stmt(first=None),  # _active_cart_id: no active cart
        ]))
        r = await worker.api_remove_cart_item(
            self._req("ci-1", headers=_user_headers()), env, "ci-1"
        )
        assert r.status == 200
        data = _parse(r)
        assert data["cart"] is None
        assert data["items"] == []

    async def test_authenticated_remove_cart_item_success(self):
        cart_row = MockRow(id="cart-1")
        env = make_env(db=MockDB([
            make_stmt(first=cart_row),  # 1. _active_cart_id
            make_stmt(),                # 2. DELETE FROM activity_cart_items
            make_stmt(),                # 3. UPDATE activity_carts set updated_at
            make_stmt(first=cart_row),  # 4. _cart_payload -> _active_cart_id
            make_stmt(all_results=[]),  # 5. _cart_payload -> items (now empty)
        ]))
        r = await worker.api_remove_cart_item(
            self._req("ci-1", headers=_user_headers()), env, "ci-1"
        )
        assert r.status == 200
        data = _parse(r)
        assert data["items"] == []
        assert data["subtotal_cents"] == 0


# ===========================================================================
# 4. api_clear_cart()
# ===========================================================================

class TestApiClearCart:
    def _req(self, headers=None):
        return MockRequest(method="DELETE", url="http://localhost/api/cart", headers=headers or {})

    async def test_unauthenticated_without_guest_token_returns_401(self):
        env = make_env()
        r = await worker.api_clear_cart(self._req(), env)
        assert r.status == 401

    async def test_clear_cart_when_no_active_cart(self):
        env = make_env(db=MockDB([
            make_stmt(first=None),  # _active_cart_id -> None
        ]))
        r = await worker.api_clear_cart(self._req(headers=_user_headers()), env)
        assert r.status == 200
        data = _parse(r)
        assert data["cart"] is None

    async def test_authenticated_clear_cart_success(self):
        cart_row = MockRow(id="cart-1")
        env = make_env(db=MockDB([
            make_stmt(first=cart_row),  # 1. _active_cart_id
            make_stmt(),                # 2. DELETE FROM activity_cart_items WHERE cart_id=?
            make_stmt(),                # 3. UPDATE activity_carts set updated_at
            make_stmt(first=cart_row),  # 4. _cart_payload -> _active_cart_id
            make_stmt(all_results=[]),  # 5. _cart_payload -> SELECT items
        ]))
        r = await worker.api_clear_cart(self._req(headers=_user_headers()), env)
        assert r.status == 200
        data = _parse(r)
        assert data["items"] == []


# ===========================================================================
# 5. api_create_checkout()
# ===========================================================================

class TestApiCreateCheckout:
    def _req(self, payload=None, headers=None):
        return json_request("/api/checkout", payload or {}, headers=headers or {})

    async def test_empty_cart_returns_400(self):
        env = make_env(db=MockDB([
            make_stmt(first=None),  # no active cart
        ]))
        r = await worker.api_create_checkout(self._req(headers=_user_headers()), env)
        assert r.status == 400
        data = _parse(r)
        assert "Add at least one activity to your cart" in data["error"]

    async def test_free_activity_checkout_user_enrolled_directly(self):
        cart_row = MockRow(id="cart-free")
        free_item = MockRow(
            id="ci-f1",
            activity_id="act-free-1",
            session_id="",
            quantity=1,
            unit_price_cents=0,
            title_snapshot="Free Community Meetup",
            title="Free Community Meetup",
            status="published",
            slug="free-meetup",
            image_url="",
        )

        mock_enroll_stmt = make_stmt()
        mock_enroll_stmt.bind.return_value.run = AsyncMock(
            return_value=MockRow(meta={"changes": 1})
        )

        env = make_env(db=MockDB([
            make_stmt(first=cart_row),            # 1. _active_cart_id
            make_stmt(all_results=[free_item]),   # 2. _cart_payload items
            mock_enroll_stmt,                     # 3. INSERT INTO enrollments
            make_stmt(),                          # 4. INSERT INTO activity_checkout_sessions
            make_stmt(),                          # 5. UPDATE activity_carts SET status='checked_out'
        ]))

        r = await worker.api_create_checkout(self._req(headers=_user_headers()), env)
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert data["data"]["free_checkout"] is True
        assert data["data"]["enrolled"] == 1
        assert data["data"]["guest"] is False
        assert data["data"]["session_id"].startswith("free_")

    async def test_free_activity_checkout_guest(self):
        cart_row = MockRow(id="cart-guest-free")
        free_item = MockRow(
            id="ci-f1",
            activity_id="act-free-1",
            session_id="",
            quantity=1,
            unit_price_cents=0,
            title_snapshot="Free Class",
            title="Free Class",
            status="published",
            slug="free-class",
            image_url="",
        )

        env = make_env(db=MockDB([
            make_stmt(first=cart_row),            # 1. _active_cart_id
            make_stmt(all_results=[free_item]),   # 2. _cart_payload items
            make_stmt(),                          # 3. INSERT INTO activity_checkout_sessions
            make_stmt(),                          # 4. UPDATE activity_carts SET status='checked_out'
        ]))

        payload = _guest_human_payload()
        r = await worker.api_create_checkout(self._req(payload, headers=_guest_headers()), env)
        assert r.status == 200
        data = _parse(r)
        assert data["data"]["free_checkout"] is True
        assert data["data"]["guest"] is True

    async def test_paid_checkout_initiates_stripe_session(self):
        cart_row = MockRow(id="cart-paid")
        paid_item = MockRow(
            id="ci-p1",
            activity_id="act-paid-1",
            session_id="",
            quantity=1,
            unit_price_cents=4500,
            title_snapshot="Advanced Python",
            title="Advanced Python",
            status="published",
            slug="adv-python",
            image_url="",
        )

        env = make_env(db=MockDB([
            make_stmt(first=cart_row),            # 1. _active_cart_id
            make_stmt(all_results=[paid_item]),   # 2. _cart_payload items
            make_stmt(),                          # 3. INSERT INTO activity_checkout_sessions
        ]))

        stripe_mock = AsyncMock(return_value={
            "id": "cs_test_paid_123",
            "url": "https://checkout.stripe.com/pay/cs_test_paid_123",
            "payment_status": "pending",
            "amount_total": 4500,
            "currency": "USD",
        })

        with patch.object(worker, "_stripe_form_request", new=stripe_mock):
            r = await worker.api_create_checkout(self._req(headers=_user_headers()), env)
            assert r.status == 200
            data = _parse(r)
            assert data["data"]["session_id"] == "cs_test_paid_123"
            assert data["data"]["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_paid_123"
            assert stripe_mock.called

    async def test_paid_checkout_stripe_failure_returns_500(self):
        cart_row = MockRow(id="cart-paid")
        paid_item = MockRow(
            id="ci-p1",
            activity_id="act-paid-1",
            session_id="",
            quantity=1,
            unit_price_cents=5000,
            title_snapshot="Guitar Lessons",
            title="Guitar Lessons",
            status="published",
            slug="guitar",
            image_url="",
        )

        env = make_env(db=MockDB([
            make_stmt(first=cart_row),
            make_stmt(all_results=[paid_item]),
        ]))

        stripe_mock = AsyncMock(side_effect=RuntimeError("Stripe network timeout"))
        with patch.object(worker, "_stripe_form_request", new=stripe_mock):
            r = await worker.api_create_checkout(self._req(headers=_user_headers()), env)
            assert r.status == 500
            data = _parse(r)
            assert "Stripe network timeout" in data["error"]


# ===========================================================================
# 6. api_complete_checkout()
# ===========================================================================

class TestApiCompleteCheckout:
    def _req(self, payload, headers=None):
        return json_request("/api/checkout/complete", payload, headers=headers or {})

    async def test_invalid_session_id_format_returns_400(self):
        env = make_env()
        r = await worker.api_complete_checkout(
            self._req({"session_id": "invalid_id_format"}, headers=_user_headers()), env
        )
        assert r.status == 400
        data = _parse(r)
        assert "Valid Stripe checkout session_id is required" in data["error"]

    async def test_mismatched_owner_kind_returns_403(self):
        stripe_mock = AsyncMock(return_value={
            "metadata": {"owner_kind": "guest", "guest_id": "other-guest"},
            "payment_status": "paid",
        })
        env = make_env()
        with patch.object(worker, "_stripe_get_request", new=stripe_mock):
            r = await worker.api_complete_checkout(
                self._req({"session_id": "cs_test_12345"}, headers=_user_headers()), env
            )
            assert r.status == 403
            data = _parse(r)
            assert "Checkout session does not belong to this cart" in data["error"]

    async def test_mismatched_user_id_returns_403(self):
        stripe_mock = AsyncMock(return_value={
            "metadata": {"owner_kind": "user", "user_id": "different-user-id"},
            "payment_status": "paid",
        })
        env = make_env()
        with patch.object(worker, "_stripe_get_request", new=stripe_mock):
            r = await worker.api_complete_checkout(
                self._req({"session_id": "cs_test_12345"}, headers=_user_headers(uid="usr-1")), env
            )
            assert r.status == 403
            data = _parse(r)
            assert "Checkout session does not belong to this user" in data["error"]

    async def test_unpaid_session_returns_400(self):
        stripe_mock = AsyncMock(return_value={
            "metadata": {"owner_kind": "user", "user_id": "usr-1"},
            "payment_status": "unpaid",
        })
        env = make_env()
        with patch.object(worker, "_stripe_get_request", new=stripe_mock):
            r = await worker.api_complete_checkout(
                self._req({"session_id": "cs_test_12345"}, headers=_user_headers(uid="usr-1")), env
            )
            assert r.status == 400
            data = _parse(r)
            assert "Payment is not complete yet" in data["error"]

    async def test_successful_paid_completion_for_user_creates_enrollments(self):
        stripe_mock = AsyncMock(return_value={
            "metadata": {"owner_kind": "user", "user_id": "usr-1", "cart_id": "cart-paid"},
            "payment_status": "paid",
            "amount_total": 4500,
        })

        item_row = MockRow(activity_id="act-paid-1")
        mock_enroll_stmt = make_stmt()
        mock_enroll_stmt.bind.return_value.run = AsyncMock(
            return_value=MockRow(meta={"changes": 1})
        )

        env = make_env(db=MockDB([
            make_stmt(all_results=[item_row]),  # 1. SELECT activity_id FROM activity_cart_items
            mock_enroll_stmt,                   # 2. INSERT OR IGNORE INTO enrollments
            make_stmt(),                        # 3. UPDATE activity_carts SET status='checked_out'
            make_stmt(),                        # 4. UPDATE activity_checkout_sessions SET status='paid'
        ]))

        with patch.object(worker, "_stripe_get_request", new=stripe_mock):
            r = await worker.api_complete_checkout(
                self._req({"session_id": "cs_test_12345"}, headers=_user_headers(uid="usr-1")), env
            )
            assert r.status == 200
            data = _parse(r)
            assert data["success"] is True
            assert data["data"]["enrolled"] == 1
            assert data["data"]["guest"] is False

    async def test_successful_paid_completion_for_guest(self):
        guest_id = worker._guest_cart_id(MockRequest(method="POST", headers=_guest_headers()), make_env())
        stripe_mock = AsyncMock(return_value={
            "metadata": {"owner_kind": "guest", "guest_id": guest_id, "cart_id": "cart-guest-paid"},
            "payment_status": "paid",
            "amount_total": 3500,
            "customer_details": {"email": "guest@example.com"},
        })

        env = make_env(db=MockDB([
            make_stmt(all_results=[]),  # 1. SELECT activity_id FROM activity_cart_items
            make_stmt(),                # 2. UPDATE activity_carts SET status='checked_out'
            make_stmt(),                # 3. UPDATE activity_checkout_sessions SET status='paid'
        ]))

        with patch.object(worker, "_stripe_get_request", new=stripe_mock):
            r = await worker.api_complete_checkout(
                self._req({"session_id": "cs_test_12345"}, headers=_guest_headers()), env
            )
            assert r.status == 200
            data = _parse(r)
            assert data["success"] is True
            assert data["data"]["guest"] is True


# ===========================================================================
# 7. api_create_donation_checkout()
# ===========================================================================

class TestApiCreateDonationCheckout:
    def _req(self, payload, headers=None):
        return json_request("/api/donations/checkout", payload, headers=headers or {})

    async def test_donation_below_minimum_returns_400(self):
        env = make_env()
        r = await worker.api_create_donation_checkout(self._req({"amount_cents": 50}), env)
        assert r.status == 400
        data = _parse(r)
        assert "Donation amount must be at least $1.00" in data["error"]

    async def test_donation_exceeding_maximum_returns_400(self):
        env = make_env()
        r = await worker.api_create_donation_checkout(self._req({"amount_cents": 2000000}), env)
        assert r.status == 400
        data = _parse(r)
        assert "Donation amount is too large" in data["error"]

    async def test_guest_donation_success(self):
        stripe_mock = AsyncMock(return_value={
            "id": "cs_donation_123",
            "url": "https://checkout.stripe.com/pay/cs_donation_123",
        })

        env = make_env(db=MockDB([
            make_stmt(),  # INSERT INTO donation_checkout_sessions
        ]))

        with patch.object(worker, "_stripe_form_request", new=stripe_mock):
            r = await worker.api_create_donation_checkout(
                self._req({"amount_cents": 2500, "email": "supporter@example.com", "message": "Keep it up!"}),
                env,
            )
            assert r.status == 200
            data = _parse(r)
            assert data["success"] is True
            assert data["data"]["session_id"] == "cs_donation_123"
            assert data["data"]["checkout_url"] == "https://checkout.stripe.com/pay/cs_donation_123"

    async def test_authenticated_donation_success_attaches_user_id(self):
        stripe_mock = AsyncMock(return_value={
            "id": "cs_donation_auth_456",
            "url": "https://checkout.stripe.com/pay/cs_donation_auth_456",
        })

        env = make_env(db=MockDB([
            make_stmt(),  # INSERT INTO donation_checkout_sessions
        ]))

        with patch.object(worker, "_stripe_form_request", new=stripe_mock):
            r = await worker.api_create_donation_checkout(
                self._req({"amount_cents": 5000}, headers=_user_headers(uid="usr-donor-1")),
                env,
            )
            assert r.status == 200
            data = _parse(r)
            assert data["data"]["session_id"] == "cs_donation_auth_456"

    async def test_donation_stripe_failure_returns_500(self):
        stripe_mock = AsyncMock(side_effect=RuntimeError("Stripe API down"))
        env = make_env()
        with patch.object(worker, "_stripe_form_request", new=stripe_mock):
            r = await worker.api_create_donation_checkout(
                self._req({"amount_cents": 1000}), env
            )
            assert r.status == 500
            data = _parse(r)
            assert "Could not create donation checkout" in data["error"]
