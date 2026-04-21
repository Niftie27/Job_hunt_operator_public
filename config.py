"""
JH Operator — Configuration
============================
This is the ONE file you edit to control what gets fetched, what counts as relevant,
and how scoring works. Everything else reads from here.
"""

# ─── SOURCE DEFINITIONS ───────────────────────────────────────────────
# Each source has a type (greenhouse, ashby, lever, web3career, cryptojobslist)
# and an identifier (the company slug used in the URL).
#
# Example: https://job-boards.greenhouse.io/nansen → type="greenhouse", id="nansen"
# Example: https://jobs.ashbyhq.com/nethermind     → type="ashby", id="nethermind"
# Example: https://jobs.lever.co/moonpay           → type="lever", id="moonpay"

SOURCES = [
    # ── Greenhouse boards ──
    {"type": "greenhouse", "id": "bcbgroup",            "name": "BCB Group"},
    {"type": "greenhouse", "id": "bloxstaking",         "name": "Blox Staking / SSV Labs"},
    {"type": "greenhouse", "id": "nansen",              "name": "Nansen"},
    {"type": "greenhouse", "id": "avalabs",             "name": "Ava Labs (Avalanche)"},
    {"type": "greenhouse", "id": "wormholefoundation",  "name": "Wormhole Foundation"},
    {"type": "greenhouse", "id": "woofi",               "name": "WOOFi"},
    {"type": "greenhouse", "id": "chainalysis",         "name": "Chainalysis"},
    {"type": "greenhouse", "id": "consensys",           "name": "ConsenSys"},
    {"type": "greenhouse", "id": "offchainlabs",        "name": "Offchain Labs (Arbitrum)"},

    # ── Ashby boards ──
    {"type": "ashby", "id": "nethermind",    "name": "Nethermind"},
    {"type": "ashby", "id": "Zircuit",       "name": "Zircuit"},
    {"type": "ashby", "id": "plume-network", "name": "Plume Network"},
    {"type": "ashby", "id": "wormholelabs",  "name": "Wormhole Labs"},

    # ── Lever boards ──
    {"type": "lever", "id": "moonpay", "name": "MoonPay"},

    # ── New Lever boards ──
    {"type": "lever", "id": "immutable",      "name": "Immutable"},
    {"type": "lever", "id": "axiomzen",       "name": "Dapper Labs"},
    {"type": "lever", "id": "anchorage",      "name": "Anchorage Digital"},

    # ── New Ashby boards ──
    # {"type": "ashby", "id": "Rubicon",        "name": "Rubicon"},        # 404 on 2026-04-21, investigate later
    # {"type": "ashby", "id": "zealy",          "name": "Zealy"},          # 404 on 2026-04-21, investigate later
    {"type": "ashby", "id": "injective-labs", "name": "Injective"},

    # ── Getro boards ──
    # {"type": "getro", "id": "wormhole",       "name": "Wormhole Ecosystem (Getro)"},  # 404 on 2026-04-21, investigate later

    # ── Crypto job boards ──
    # These search across many companies at once
    {"type": "web3career",      "id": "solidity",           "name": "web3.career (solidity)"},
    {"type": "web3career",      "id": "blockchain",         "name": "web3.career (blockchain)"},
    {"type": "web3career",      "id": "smart-contract",     "name": "web3.career (smart-contract)"},
    {"type": "cryptojobslist",  "id": "solidity-jobs",      "name": "CryptoJobsList (solidity)"},
    {"type": "cryptojobslist",  "id": "blockchain-jobs",    "name": "CryptoJobsList (blockchain)"},
]


# ─── KEYWORD SCORING ──────────────────────────────────────────────────
# How relevance scoring works:
# - Each job title + description is checked against these keyword lists
# - Points are added for each match
# - Final score = sum of all matched keyword weights
# - Higher score = more relevant to you

# Strong match: these words in a title almost certainly mean it's for you
PRIMARY_KEYWORDS = {
    "solidity":         10,
    "smart contract":   10,
    "blockchain":        8,
    "web3":              8,
    "dapp":              7,
    "defi":              7,
    "dex":               6,
    "ethereum":          6,
    "evm":               6,
    "rust":              5,   # relevant for Solana/Anchor work
    "anchor":            7,
    "solana":            6,
    "cross-chain":       6,
    "bridge":            4,   # could be non-crypto, lower weight
    "l2":                5,
    "layer 2":           5,
    "nft":               4,
    "token":             4,
}

# Supporting match: these boost relevance but alone aren't enough
SECONDARY_KEYWORDS = {
    "full-stack":        3,
    "fullstack":         3,
    "full stack":        3,
    "backend":           2,
    "node.js":           2,
    "nodejs":            2,
    "react":             2,
    "next.js":           2,
    "nextjs":            2,
    "typescript":        2,
    "javascript":        2,
    "developer":         1,
    "engineer":          1,
    "protocol":          3,
    "crypto":            3,
    "decentralized":     3,
}

# ─── DEPRECATED (v0.5 only, not used by v0.6 pipeline) ────────────────
# These were used when the script tried to guess RELEVANT/MAYBE/SKIP.
# The v0.6 pipeline classifies by role_type + seniority + web3_score instead.
# Kept here for reference in case you want to restore old behavior.

NEGATIVE_KEYWORDS = {
    "staff":            -3,
    "principal":        -4,
    "director":         -5,
    "vp ":              -5,
    "vice president":   -5,
    "head of":          -4,
    "manager":          -2,
    "marketing":        -5,
    "sales":            -5,
    "legal":            -6,
    "counsel":          -6,
    "compliance":       -4,
    "recruiter":        -6,
    "designer":         -3,  # unless it's "protocol designer"
    "data scientist":   -3,
    "devops":           -2,
    "sre":              -2,
    "qa":               -2,
    "10+ years":        -4,
    "8+ years":         -3,
    "7+ years":         -2,
}

# ─── DEPRECATED (v0.5 only) ───────────────────────────────────────────
SCORE_RELEVANT = 8       # no longer used by v0.6 pipeline
SCORE_MAYBE = 4          # no longer used by v0.6 pipeline

# ─── TRACKER FILE ─────────────────────────────────────────────────────
TRACKER_PATH = "data/tracker.csv"

# ─── OUTPUT ───────────────────────────────────────────────────────────
OUTPUT_DIR = "output"
