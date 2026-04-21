#!/usr/bin/env python3
"""
JH Operator — ATS Detector
============================
Run ONCE locally to discover which companies from JH_Jobs_links.md
use Greenhouse, Ashby, or Lever under the hood.

Usage:
    python3 detect_ats.py

Saves ready-to-paste config.py entries to output/ats-detection-results.json
"""

import urllib.request
import urllib.error
import re
import time
import json
import os
import ssl


PAGES_TO_CHECK = [
    # ── "Other Url" section of JH_Jobs_links.md ──
    ("Offchain Labs (Arbitrum)",  "https://www.offchainlabs.com/careers"),
    ("SSV Labs",                  "https://ssvlabs.io/"),
    ("BCB Group careers",         "https://www.bcbgroup.com/careers/"),
    ("Avalanche (avax.network)",  "https://jobs.avax.network/jobs"),
    ("Taiko",                     "https://taiko.xyz/careers"),
    ("Sui",                       "https://jobs.sui.io/jobs"),
    ("Phantom",                   "https://phantom.com/careers"),
    ("Immutable",                 "https://www.immutable.com/careers"),
    ("LayerZero",                 "https://layerzero.network/careers"),
    ("SatoshiLabs",               "https://satoshilabs.com/careers"),
    ("Zerion",                    "https://zerion.io/careers"),
    ("Alchemy",                   "https://www.alchemy.com/careers"),
    ("Anysphere (Cursor)",        "https://anysphere.inc/"),
    ("Rubicon",                   "https://www.rubicon.finance/jobs"),
    ("Dune",                      "https://dune.com/careers"),
    ("Elixir",                    "https://elixirjobs.net/"),
    ("Messari",                   "https://messari.io/careers"),
    ("Frax",                      "https://frax.finance/careers"),
    ("Token Terminal",            "https://tokenterminal.com/careers"),
    ("CryptoJobs.com",            "https://www.cryptojobs.com/jobs"),
    ("Arkham",                    "https://info.arkm.com/careers"),
    ("Moralis",                   "https://talent.moralis.io/jobs"),
    ("Zealy",                     "https://zealy.io/careers"),
    ("EtherMail",                 "https://ethermail.breezy.hr/"),
    ("Animoca Brands",            "https://careers.animocabrands.com/jobs"),
    ("FalconX",                   "https://www.falconx.io/careers"),
    ("Chainalysis",               "https://www.chainalysis.com/careers/job-openings/"),
    ("Chainlink",                 "https://chainlinklabs.com/open-roles"),
    ("Injective",                 "https://injectivelabs.org/careers"),
    ("Wormhole ecosystem",        "https://wormhole.com/ecosystem/careers"),
    ("Wormhole Getro",            "https://wormhole.getro.com/jobs"),

    # ── "Crypto Companies" section ──
    ("Kraken",                    "https://www.kraken.com/careers"),
    ("Crypto.com",                "https://crypto.com/company/careers"),
    ("Coinbase",                  "https://www.coinbase.com/en-gb/careers/positions"),
    ("Gemini",                    "https://www.gemini.com/careers"),
    ("QuickNode",                 "https://www.quicknode.com/careers"),
    ("Dapper Labs",               "https://www.dapperlabs.com/careers"),
    ("Anchorage Digital",         "https://www.anchorage.com/careers"),
    ("Celo",                      "https://celo.org/jobs"),
    ("DFINITY (ICP)",             "https://dfinity.org/careers"),
    ("dYdX",                      "https://dydx.exchange/careers"),
    ("OpenSea",                   "https://opensea.io/careers"),
    ("Protocol Labs",             "https://protocol.ai/join"),
    ("Blaize",                    "https://blaize.tech/careers/"),
    ("Blockchain.com",            "https://www.blockchain.com/careers"),

    # ── Crypto job boards worth checking ──
    ("CryptocurrencyJobs",        "https://cryptocurrencyjobs.co"),
    ("Remote3",                   "https://remote3.co"),
    ("ThirdWork",                 "https://thirdwork.xyz"),
    ("BlockchainDevs.net",        "https://blockchaindevs.net"),
    ("PortfolioJobs (Jump)",      "https://portfoliojobs.jumpcrypto.com"),
]


ATS_PATTERNS = {
    "greenhouse": [
        r"boards-api\.greenhouse\.io",
        r"boards\.greenhouse\.io/(\w+)",
        r"job-boards\.greenhouse\.io/([a-zA-Z0-9_-]+)",
        r"job-boards\.eu\.greenhouse\.io/([a-zA-Z0-9_-]+)",
        r"api\.greenhouse\.io",
        r"grnh\.se",
    ],
    "ashby": [
        r"jobs\.ashbyhq\.com/([a-zA-Z0-9_-]+)",
        r"api\.ashbyhq\.com",
    ],
    "lever": [
        r"jobs\.lever\.co/([a-zA-Z0-9_-]+)",
        r"api\.lever\.co",
    ],
    "workable": [
        r"apply\.workable\.com/([a-zA-Z0-9_-]+)",
    ],
    "breezy": [
        r"([a-zA-Z0-9_-]+)\.breezy\.hr",
    ],
    "getro": [
        r"([a-zA-Z0-9_-]+)\.getro\.com",
    ],
    "smartrecruiters": [
        r"careers\.smartrecruiters\.com/([a-zA-Z0-9_-]+)",
        r"jobs\.smartrecruiters\.com/([a-zA-Z0-9_-]+)",
    ],
}

SUPPORTED_ATS = {"greenhouse", "ashby", "lever"}


def _fetch_page(url, timeout=15):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.url, resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return "", str(e)


def check_page(name, url):
    result = {"name": name, "url": url, "ats": None, "slug": None,
              "supported": False, "config_entry": None, "error": None}

    final_url, html = _fetch_page(url)
    if not final_url:
        result["error"] = html[:100]
        return result

    text = f"{final_url} {html[:50000]}"

    for ats_name, patterns in ATS_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["ats"] = ats_name
                if match.groups():
                    result["slug"] = match.group(1)
                result["supported"] = ats_name in SUPPORTED_ATS
                if result["supported"] and result["slug"]:
                    slug = result["slug"].rstrip("/").strip()
                    result["config_entry"] = (
                        f'{{"type": "{ats_name}", "id": "{slug}", '
                        f'"name": "{name}"}}'
                    )
                break
        if result["ats"]:
            break

    return result


def main():
    print("=" * 70)
    print("  JH Operator — ATS Detector")
    print(f"  Checking {len(PAGES_TO_CHECK)} career pages...")
    print("=" * 70)
    print()

    results = []
    for name, url in PAGES_TO_CHECK:
        print(f"  {name:30s} ... ", end="", flush=True)
        result = check_page(name, url)

        if result["error"]:
            print(f"❌ {result['error'][:50]}")
        elif result["ats"]:
            tag = "✅" if result["supported"] else "⚠️ "
            slug = f" → {result['slug']}" if result["slug"] else ""
            print(f"{tag} {result['ats']}{slug}")
        else:
            print("❓ No known ATS")

        results.append(result)
        time.sleep(0.3)

    # ── Summary ──
    print("\n" + "=" * 70)
    print("  RESULTS")
    print("=" * 70)

    ready = [r for r in results if r["config_entry"]]
    unsupported = [r for r in results if r["ats"] and not r["supported"]]
    no_ats = [r for r in results if not r["ats"] and not r["error"]]
    errors = [r for r in results if r["error"]]

    if ready:
        print(f"\n✅ READY TO ADD ({len(ready)}):")
        print("   Copy-paste into SOURCES in config.py:\n")
        for r in ready:
            print(f"    {r['config_entry']},")
        print("\n   ⚠ Remove duplicates that are already in config.py!")

    if unsupported:
        print(f"\n⚠️  NEED NEW FETCHER ({len(unsupported)}):")
        for r in unsupported:
            print(f"    {r['name']:30s} → {r['ats']} ({r['slug'] or '?'})")

    if no_ats:
        print(f"\n❓ NO ATS — needs Playwright later ({len(no_ats)}):")
        for r in no_ats:
            print(f"    {r['name']:30s} — {r['url']}")

    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for r in errors:
            print(f"    {r['name']:30s} — {r['error'][:60]}")

    os.makedirs("output", exist_ok=True)
    with open("output/ats-detection-results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to output/ats-detection-results.json")


if __name__ == "__main__":
    main()
