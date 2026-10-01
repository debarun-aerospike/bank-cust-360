"""
Customer 360 Gate 3 seeder — writes schema-guide sets into namespace `bank`.

Usage (always via uv):
  uv sync
  uv run python seed.py --customers 100 --port 13000
  uv run python seed.py --customers 5000000 --checkpoint-every 10000 --port 13000

Does not increment inventory per record (avoids hot key); checkpoints `inventory`/`totals`.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
from typing import Any

import aerospike
from aerospike import exception as ae
from faker import Faker

NS = "bank"
HOSTS: list[tuple[str, int]] = [("127.0.0.1", 3000)]
USER: str | None = None
PASSWORD: str | None = None

PRODUCTS: list[dict[str, Any]] = [
    {"code": "SB-REG", "description": "Regular Savings Account", "productLine": "SAVINGS_CURRENT"},
    {"code": "CA-PREM", "description": "Premium Current Account", "productLine": "SAVINGS_CURRENT"},
    {"code": "FD-1Y", "description": "1-Year Fixed Deposit", "productLine": "TERM_DEPOSIT"},
    {"code": "FD-5Y", "description": "5-Year Term Deposit", "productLine": "TERM_DEPOSIT"},
    {"code": "HL-STD", "description": "Standard Home Loan", "productLine": "LOAN"},
    {"code": "PL-FLEX", "description": "Flexible Personal Loan", "productLine": "LOAN"},
    {"code": "CC-GOLD", "description": "Gold Credit Card", "productLine": "CARD"},
    {"code": "CC-PLAT", "description": "Platinum Credit Card", "productLine": "CARD"},
]

SALUTATIONS = ["Mr", "Ms", "Mrs", "Mx"]

# Country / alias → Faker locale. Default India → en_IN.
COUNTRY_LOCALES: dict[str, str] = {
    "india": "en_IN",
    "in": "en_IN",
    "united states": "en_US",
    "usa": "en_US",
    "us": "en_US",
    "united kingdom": "en_GB",
    "uk": "en_GB",
    "gb": "en_GB",
    "australia": "en_AU",
    "au": "en_AU",
    "canada": "en_CA",
    "ca": "en_CA",
    "germany": "de_DE",
    "de": "de_DE",
    "france": "fr_FR",
    "fr": "fr_FR",
    "japan": "ja_JP",
    "jp": "ja_JP",
    "brazil": "pt_BR",
    "br": "pt_BR",
    "spain": "es_ES",
    "es": "es_ES",
    "mexico": "es_MX",
    "mx": "es_MX",
    "italy": "it_IT",
    "it": "it_IT",
    "netherlands": "nl_NL",
    "nl": "nl_NL",
    "singapore": "en_US",
    "sg": "en_US",
    "indonesia": "id_ID",
    "philippines": "en_PH",
    "ph": "en_PH",
    "malaysia": "ms_MY",
    "thailand": "th_TH",
    "th": "th_TH",
    "vietnam": "vi_VN",
    "vn": "vi_VN",
    "cambodia": "en_US",
    "myanmar": "en_US",
    "laos": "en_US",
    "brunei": "en_US",
    "uae": "ar_AA",
    "united arab emirates": "ar_AA",
}

# Country / alias → ISO 4217 currency for seeded accounts.
COUNTRY_CURRENCIES: dict[str, str] = {
    "india": "INR",
    "in": "INR",
    "united states": "USD",
    "usa": "USD",
    "us": "USD",
    "united kingdom": "GBP",
    "uk": "GBP",
    "gb": "GBP",
    "australia": "AUD",
    "au": "AUD",
    "canada": "CAD",
    "ca": "CAD",
    "germany": "EUR",
    "de": "EUR",
    "france": "EUR",
    "fr": "EUR",
    "japan": "JPY",
    "jp": "JPY",
    "brazil": "BRL",
    "br": "BRL",
    "spain": "EUR",
    "es": "EUR",
    "mexico": "MXN",
    "mx": "MXN",
    "italy": "EUR",
    "it": "EUR",
    "netherlands": "EUR",
    "nl": "EUR",
    "singapore": "SGD",
    "sg": "SGD",
    "indonesia": "IDR",
    "philippines": "PHP",
    "ph": "PHP",
    "malaysia": "MYR",
    "thailand": "THB",
    "th": "THB",
    "vietnam": "VND",
    "vn": "VND",
    "cambodia": "KHR",
    "myanmar": "MMK",
    "laos": "LAK",
    "brunei": "BND",
    "uae": "AED",
    "united arab emirates": "AED",
}

# Weighted product-line picks for ~avg 2 accounts/customer (max 5).
LINE_SPECS = [
    ("S", "SAVINGS_CURRENT", ["SB-REG", "CA-PREM"]),
    ("F", "TERM_DEPOSIT", ["FD-1Y", "FD-5Y"]),
    ("L", "LOAN", ["HL-STD", "PL-FLEX"]),
    ("C", "CARD", ["CC-GOLD", "CC-PLAT"]),
]


def resolve_locale(country: str) -> tuple[str, str]:
    """Return (display country, faker locale). Unknown countries fall back to en_US."""
    raw = (country or "India").strip() or "India"
    key = raw.lower()
    if key in COUNTRY_LOCALES:
        return raw.title() if len(raw) > 3 else raw.upper(), COUNTRY_LOCALES[key]
    # Allow passing a Faker locale directly (e.g. en_IN).
    if "_" in key and len(key) <= 8:
        return raw, raw
    return raw.title(), "en_US"


def resolve_currency(country: str) -> str:
    """ISO 4217 currency for the ingest country. Default INR."""
    key = (country or "India").strip().lower() or "india"
    if key in COUNTRY_CURRENCIES:
        return COUNTRY_CURRENCIES[key]
    return "INR"


def deposit_booking_amounts(rng: random.Random) -> tuple[int, int, int]:
    """ledger/hold/float in minor units; available (ledger-hold-float) always ≥ 0."""
    ledger = rng.randint(10_000_00, 500_000_00)
    hold_cap = min(5_000_00, ledger // 10)
    hold = rng.randint(0, hold_cap)
    remaining = ledger - hold
    float_cap = min(2_000_00, remaining // 20) if remaining > 0 else 0
    flo = rng.randint(0, float_cap) if float_cap > 0 else 0
    # Defensive: never let holds exceed ledger.
    if hold + flo > ledger:
        flo = max(0, ledger - hold)
    return ledger, hold, flo


def prompt_country(cli_value: str | None) -> str:
    if cli_value is not None and cli_value.strip():
        return cli_value.strip()
    if sys.stdin.isatty():
        entered = input("Country for person names [India]: ").strip()
        return entered or "India"
    return "India"


def parse_hosts(hosts_csv: str, default_port: int) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for part in (hosts_csv or "").split(","):
        item = part.strip()
        if not item:
            continue
        if ":" in item:
            host, _, port_s = item.rpartition(":")
            host = host.strip()
            if not host:
                continue
            out.append((host, int(port_s.strip())))
        else:
            out.append((item, default_port))
    return out


def connect() -> Any:
    config: dict[str, Any] = {"hosts": HOSTS}
    if USER:
        config["user"] = USER
        config["password"] = PASSWORD or ""
    return aerospike.client(config)


def write_policy() -> Any:
    # send/store user key with record
    return {"key": aerospike.POLICY_KEY_SEND}


def put_products(client: Any) -> None:
    wp = write_policy()
    for p in PRODUCTS:
        key = (NS, "products", p["code"])
        client.put(
            key,
            {
                "description": p["description"],
                "productLine": p["productLine"],
                "active": True,
            },
            meta={"ttl": aerospike.TTL_NEVER_EXPIRE},
            policy=wp,
        )


def product_by_code(code: str) -> dict[str, Any]:
    for p in PRODUCTS:
        if p["code"] == code:
            return p
    raise KeyError(code)


def write_inventory(client: Any, counts: dict[str, int]) -> None:
    key = (NS, "inventory", "totals")
    bins = {
        "custCnt": counts["custCnt"],
        "acctCnt": counts["acctCnt"],
        "acctS": counts["acctS"],
        "acctF": counts["acctF"],
        "acctL": counts["acctL"],
        "acctC": counts["acctC"],
        "prodCnt": counts["prodCnt"],
        "updatedAt": int(time.time() * 1000),
    }
    client.put(
        key,
        bins,
        meta={"ttl": aerospike.TTL_NEVER_EXPIRE},
        policy=write_policy(),
    )


def cust_id(n: int) -> str:
    return f"{n:07d}"


def acct_id(prefix: str, seq: int) -> str:
    return f"{prefix}{seq:012d}"


def person_name(fake: Faker, rng: random.Random) -> tuple[str, str]:
    salutation = rng.choice(SALUTATIONS)
    try:
        name = fake.name()
    except Exception:  # noqa: BLE001
        name = f"{fake.first_name()} {fake.last_name()}"
    # Keep banking-style display: no trailing period on salutation.
    return salutation, " ".join(name.split())


def seed_customer(
    client: Any,
    cid: str,
    acct_seq: list[int],
    rng: random.Random,
    counts: dict[str, int],
    fake: Faker,
    currency: str,
) -> None:
    wp = write_policy()
    meta = {"ttl": aerospike.TTL_NEVER_EXPIRE}
    salutation, name = person_name(fake, rng)
    # Keep early demo IDs Active; ~5% of the rest are Dormant.
    # Account status tracks customer status so Active account filter never
    # surfaces a Dormant customer's Active accounts.
    if int(cid) <= 10:
        cust_status = "Active"
    else:
        cust_status = "Active" if rng.random() > 0.05 else "Dormant"
    client.put(
        (NS, "customers", cid),
        {
            "salutation": salutation,
            "name": name,
            "status": cust_status,
            "lastTouchAt": 0,
        },
        meta=meta,
        policy=wp,
    )
    counts["custCnt"] += 1

    n_accts = 2 if rng.random() < 0.85 else rng.randint(1, 5)
    lines = rng.sample(LINE_SPECS, k=min(n_accts, len(LINE_SPECS)))
    while len(lines) < n_accts:
        lines.append(rng.choice(LINE_SPECS))

    primary_ids: list[str] = []
    joint_ids: list[str] = []

    for prefix, product_line, codes in lines:
        acct_seq[0] += 1
        aid = acct_id(prefix, acct_seq[0])
        code = rng.choice(codes)
        prod = product_by_code(code)
        ownership = "PRIMARY"
        owner_ids = [cid]
        # ~10% joint with a synthetic neighbor id (may not exist as customer — demo only)
        if rng.random() < 0.1 and int(cid) > 1:
            ownership = "JOINT"
            other = cust_id(max(1, int(cid) - 1))
            owner_ids = [cid, other]

        client.put(
            (NS, "accounts", aid),
            {
                "productLine": product_line,
                "currency": currency,
                "acctStatus": cust_status,
                "productCode": code,
                "productDesc": prod["description"],
                "ownership": ownership,
                "ownerIds": owner_ids,
                "openedAt": "2024-01-15",
            },
            meta=meta,
            policy=wp,
        )

        if prefix in ("S", "F"):
            ledger, hold, flo = deposit_booking_amounts(rng)
            client.put(
                (NS, "booking", aid),
                {"ledger": ledger, "hold": hold, "float": flo},
                meta=meta,
                policy=wp,
            )
            counts["acctS" if prefix == "S" else "acctF"] += 1
        else:
            principal = rng.randint(50_000_00, 5_000_000_00)
            interest = rng.randint(0, principal // 50)
            client.put(
                (NS, "booking", aid),
                {"principal": principal, "interest": interest},
                meta=meta,
                policy=wp,
            )
            counts["acctL" if prefix == "L" else "acctC"] += 1

        counts["acctCnt"] += 1
        if ownership == "PRIMARY":
            primary_ids.append(aid)
        else:
            joint_ids.append(aid)

    acct_ids = primary_ids + joint_ids
    client.put(
        (NS, "cust_accts", cid),
        {"acctIds": acct_ids},
        meta=meta,
        policy=wp,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Customer 360 Aerospike data")
    parser.add_argument("--customers", type=int, default=100, help="Number of customers to load")
    parser.add_argument(
        "--hosts",
        default=None,
        help="Comma-separated seed nodes host[:port] (overrides --host/--port; "
        "also reads AEROSPIKE_HOSTS)",
    )
    parser.add_argument("--host", default=None, help="Single seed host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Default port when omitted on a host")
    parser.add_argument("--user", default=None, help="Aerospike user (or AEROSPIKE_USER)")
    parser.add_argument("--password", default=None, help="Aerospike password (or AEROSPIKE_PASSWORD)")
    parser.add_argument("--checkpoint-every", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--country",
        default=None,
        help="Country for Faker person names (default: prompt, or India if non-interactive)",
    )
    args = parser.parse_args()

    if args.customers < 1 or args.customers > 9_999_999:
        print("customers must be 1..9999999 (7-digit id space)", file=sys.stderr)
        return 2

    country_input = prompt_country(args.country)
    country_label, locale = resolve_locale(country_input)
    currency = resolve_currency(country_input)
    fake = Faker(locale)
    Faker.seed(args.seed)
    fake.seed_instance(args.seed)

    default_port = args.port if args.port is not None else int(os.environ.get("AEROSPIKE_PORT") or "3000")
    hosts_csv = args.hosts or os.environ.get("AEROSPIKE_HOSTS") or ""
    single_host = args.host or os.environ.get("AEROSPIKE_HOST") or "127.0.0.1"

    global HOSTS, USER, PASSWORD
    if hosts_csv.strip():
        HOSTS = parse_hosts(hosts_csv, default_port)
    else:
        HOSTS = [(single_host.strip() or "127.0.0.1", default_port)]
    USER = (args.user if args.user is not None else os.environ.get("AEROSPIKE_USER") or "").strip() or None
    PASSWORD = args.password if args.password is not None else os.environ.get("AEROSPIKE_PASSWORD")

    print(
        f"Connecting to Aerospike {HOSTS} namespace={NS} "
        f"names={country_label} (locale={locale}) currency={currency} "
        f"auth={'on' if USER else 'off'} ..."
    )
    try:
        client = connect()
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to connect: {exc}", file=sys.stderr)
        return 1

    try:
        put_products(client)
        counts = {
            "custCnt": 0,
            "acctCnt": 0,
            "acctS": 0,
            "acctF": 0,
            "acctL": 0,
            "acctC": 0,
            "prodCnt": len(PRODUCTS),
        }
        write_inventory(client, counts)

        rng = random.Random(args.seed)
        acct_seq = [0]
        t0 = time.time()
        for i in range(1, args.customers + 1):
            seed_customer(client, cust_id(i), acct_seq, rng, counts, fake, currency)
            if i % args.checkpoint_every == 0:
                write_inventory(client, counts)
                elapsed = time.time() - t0
                rate = i / elapsed if elapsed else 0
                print(f"checkpoint customers={i} accounts={counts['acctCnt']} rate={rate:.0f}/s")

        write_inventory(client, counts)
        elapsed = time.time() - t0
        print(
            f"Done. customers={counts['custCnt']} accounts={counts['acctCnt']} "
            f"names={country_label} currency={currency} in {elapsed:.1f}s. "
            f"Demo IDs: 0000001 .. {cust_id(args.customers)}"
        )
        return 0
    except ae.AerospikeError as exc:
        print(f"Aerospike error: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
