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
    {"type": "greenhouse", "id": "bcbgroup",            "name": "BCB Group", "category": "crypto"},
    {"type": "greenhouse", "id": "bloxstaking",         "name": "Blox Staking / SSV Labs", "category": "crypto"},
    {"type": "greenhouse", "id": "nansen",              "name": "Nansen", "category": "crypto"},
    # {"type": "greenhouse", "id": "avalabs",            "name": "Ava Labs (Avalanche)"},   # 404 on 2026-04-21, investigate later
    # {"type": "greenhouse", "id": "wormholefoundation", "name": "Wormhole Foundation"},    # 404 on 2026-04-21, investigate later
    {"type": "greenhouse", "id": "woofi",               "name": "WOOFi", "category": "crypto"},
    # {"type": "greenhouse", "id": "chainalysis",        "name": "Chainalysis"},            # 404 on 2026-04-21, investigate later
    {"type": "greenhouse", "id": "consensys",           "name": "ConsenSys", "category": "crypto"},
    # {"type": "greenhouse", "id": "offchainlabs",       "name": "Offchain Labs (Arbitrum)"},  # 404 on 2026-04-21, investigate later

    # ── Ashby boards ──
    {"type": "ashby", "id": "nethermind",    "name": "Nethermind", "category": "crypto"},
    {"type": "ashby", "id": "Zircuit",       "name": "Zircuit", "category": "crypto"},
    # {"type": "ashby", "id": "plume-network", "name": "Plume Network"},                   # 404 on 2026-04-21, investigate later
    {"type": "ashby", "id": "wormholelabs",  "name": "Wormhole Labs", "category": "crypto"},

    # ── Lever boards ──
    {"type": "lever", "id": "moonpay", "name": "MoonPay", "category": "crypto"},

    # ── New Lever boards ──
    {"type": "lever", "id": "immutable",      "name": "Immutable", "category": "crypto"},
    # {"type": "lever", "id": "axiomzen",       "name": "Dapper Labs"},  # 404 on 2026-04-21 and 2026-04-22 — slug likely stale
    {"type": "lever", "id": "anchorage",      "name": "Anchorage Digital", "category": "crypto"},

    # ── New Ashby boards ──
    # {"type": "ashby", "id": "Rubicon",        "name": "Rubicon"},        # 404 on 2026-04-21, investigate later
    # {"type": "ashby", "id": "zealy",          "name": "Zealy"},          # 404 on 2026-04-21, investigate later
    {"type": "ashby", "id": "injective-labs", "name": "Injective", "category": "crypto"},

    # ── Getro boards ──
    # {"type": "getro", "id": "wormhole",       "name": "Wormhole Ecosystem (Getro)"},  # 404 on 2026-04-21, investigate later

    # ── Career pages (Playwright scraper) ──
    {"type": "career_page", "id": "https://phantom.app/careers",               "name": "Phantom", "category": "crypto"},
    {"type": "career_page", "id": "https://layerzero.network/careers",          "name": "LayerZero", "category": "crypto"},
    {"type": "career_page", "id": "https://satoshilabs.com/careers",            "name": "SatoshiLabs", "default_location": "Prague, Czech Republic", "category": "crypto"},
    {"type": "career_page", "id": "https://www.alchemy.com/careers",            "name": "Alchemy", "category": "crypto"},
    {"type": "career_page", "id": "https://chainlinklabs.com/careers",          "name": "Chainlink", "category": "crypto"},
    {"type": "career_page", "id": "https://www.kraken.com/careers",             "name": "Kraken", "category": "crypto"},
    {"type": "career_page", "id": "https://dydx.exchange/careers",              "name": "dYdX", "category": "crypto"},
    {"type": "career_page", "id": "https://opensea.io/careers",                 "name": "OpenSea", "category": "crypto"},
    {"type": "ashby",       "id": "quicknode",                                  "name": "QuickNode", "category": "crypto"},
    {"type": "greenhouse",  "id": "gemini",                                     "name": "Gemini", "category": "crypto"},
    {"type": "career_page", "id": "https://dfinity.org/careers",                "name": "DFINITY", "category": "crypto"},
    {"type": "lever",       "id": "zerion",                                     "name": "Zerion", "category": "crypto"},
    {"type": "career_page", "id": "https://info.arkm.com/careers",              "name": "Arkham", "category": "crypto"},
    {"type": "greenhouse",  "id": "falconx",                                    "name": "FalconX", "category": "crypto"},
    {"type": "career_page", "id": "https://www.blockchain.com/careers",         "name": "Blockchain.com", "category": "crypto"},
    {"type": "career_page", "id": "https://tokenterminal.com/careers",          "name": "Token Terminal", "category": "crypto"},
    {"type": "career_page", "id": "https://taiko.xyz/careers",                  "name": "Taiko", "category": "crypto"},
    # {"type": "career_page", "id": "https://frax.finance/careers",               "name": "Frax", "category": "crypto"},  # dead 2026-04-23, no working career page
    {"type": "career_page", "id": "https://cryptocurrencyjobs.co/startups/frax-finance/", "name": "Frax (via aggregator)", "category": "crypto"},
    {"type": "career_page", "id": "https://www.blaize.com/careers/",            "name": "Blaize", "category": "crypto"},  # was blaize.tech (expired 2026-04-23)

    # ── Tracker-derived sources (v0.9.6 discovery) ──
    {"type": "lever",      "id": "tokenmetrics",   "name": "Token Metrics", "category": "crypto"},
    {"type": "lever",      "id": "animocabrands",  "name": "Animoca Brands", "category": "crypto"},
    {"type": "greenhouse", "id": "bitpanda",        "name": "Bitpanda", "category": "crypto"},
    {"type": "greenhouse", "id": "b2c2",            "name": "B2c2", "category": "crypto"},
    {"type": "greenhouse", "id": "pact",            "name": "Pact Labs", "category": "crypto"},
    {"type": "ashby",      "id": "odin",            "name": "Odin", "category": "crypto"},
    {"type": "ashby",      "id": "somnia",          "name": "Somnia", "category": "crypto"},
    {"type": "greenhouse", "id": "make",            "name": "Make", "category": "crypto"},

    {"type": "career_page", "id": "https://1password.com/careers",           "name": "1Password", "category": "crypto"},
    {"type": "career_page", "id": "https://www.paxos.com/careers",           "name": "Paxos", "category": "crypto"},
    {"type": "career_page", "id": "https://www.improbable.io/careers",       "name": "Improbable", "category": "crypto"},
    {"type": "career_page", "id": "https://keyrock.com/careers/",            "name": "Keyrock", "category": "crypto"},
    {"type": "career_page", "id": "https://www.modular.com/company/careers", "name": "Modular", "category": "crypto"},
    {"type": "career_page", "id": "https://devbrother.com/career",           "name": "DevBrother", "category": "crypto"},

    # ── Crypto-aligned sources (watchlist discovery v0.9.11) ──
    # etherfi.io was a scam redirect — switched to Ashby (slug "ether.fi")
    {"type": "ashby",       "id": "ether.fi",                                "name": "Ether.fi", "category": "crypto"},
    # {"type": "career_page", "id": "https://winnables.io/careers",            "name": "Winnables", "category": "crypto"},  # dead 2026-04-23, domain expired
    # {"type": "career_page", "id": "https://pod.io/careers",                  "name": "Pod Network", "category": "crypto"},  # dead 2026-04-23, domain gone
    # halborn.io redirects to scam SEO spam; halborn.com is the real domain.
    # Ashby/Lever/Greenhouse APIs all 404, so use the career page directly.
    {"type": "career_page", "id": "https://halborn.com/careers",             "name": "Halborn", "category": "crypto"},
    {"type": "career_page", "id": "https://cryptosec.com/crypto-security-jobs/", "name": "Cryptosec", "category": "crypto"},
    {"type": "career_page", "id": "https://www.digitalasset.com/careers",    "name": "Digital Asset", "category": "crypto"},
    {"type": "ashby",       "id": "braiins",                                 "name": "Braiins", "category": "crypto"},
    {"type": "ashby",       "id": "onramp",                                  "name": "OnRamp", "category": "crypto"},
    {"type": "career_page", "id": "https://www.langchain.com/careers",       "name": "LangChain", "category": "crypto"},

    # ── Crypto job boards ──
    # These search across many companies at once
    {"type": "web3career",      "id": "solidity",           "name": "web3.career (solidity)", "category": "crypto"},
    {"type": "web3career",      "id": "blockchain",         "name": "web3.career (blockchain)", "category": "crypto"},
    {"type": "web3career",      "id": "smart-contract",     "name": "web3.career (smart-contract)", "category": "crypto"},
    {"type": "cryptojobslist",  "id": "solidity-jobs",      "name": "CryptoJobsList (solidity)", "category": "crypto"},
    {"type": "cryptojobslist",  "id": "blockchain-jobs",    "name": "CryptoJobsList (blockchain)", "category": "crypto"},

    # ── General/tech companies (non-crypto, opt-in via --mode all) ──
    {"type": "ashby",       "id": "purestorage",                                                "name": "Pure Storage", "category": "general"},
    {"type": "greenhouse",  "id": "ipfabric",                                                   "name": "IP Fabric", "category": "general"},
    {"type": "ashby",       "id": "gooddata",                                                   "name": "GoodData", "category": "general"},
    {"type": "ashby",       "id": "runway",                                                     "name": "Runway", "category": "general"},
    {"type": "greenhouse",  "id": "momence",                                                    "name": "Momence", "category": "general"},
    {"type": "greenhouse",  "id": "wrike",                                                      "name": "Wrike", "category": "general"},
    {"type": "career_page", "id": "https://twine.com/careers",                                  "name": "Twine", "category": "general"},
    {"type": "career_page", "id": "https://mtransform.com/careers",                             "name": "mTransform", "category": "general"},
    {"type": "career_page", "id": "https://careers.pixel8labs.com/215b05e5068e4c07b231ae7f27500502", "name": "Pixel8Labs", "category": "general"},
    {"type": "career_page", "id": "https://europroptrading.com/careers",                        "name": "EUROPROP Trading", "category": "general"},
    {"type": "career_page", "id": "https://www.quantumtechnologies.com/careers",                "name": "Quantum Technologies", "category": "general"},
    {"type": "career_page", "id": "https://coltech.com/careers",                                "name": "Coltech", "category": "general"},
    {"type": "career_page", "id": "https://quantfi.com/careers",                                "name": "QuantFi", "category": "general"},
    {"type": "career_page", "id": "https://bloxspace.com/careers",                              "name": "Blox Space", "category": "general"},
    {"type": "career_page", "id": "https://idc.io/careers",                                     "name": "IDC", "category": "general"},
    {"type": "career_page", "id": "https://careers.roblox.com/jobs",                            "name": "Roblox", "category": "general"},
    {"type": "career_page", "id": "https://2n.io/careers",                                      "name": "2N", "category": "general"},
    {"type": "career_page", "id": "https://www.wppmedia.com/careers",                           "name": "WPP Media", "category": "general"},
    {"type": "career_page", "id": "https://apify.com/jobs",                                     "name": "Apify", "category": "general"},
    {"type": "career_page", "id": "https://www.mapbox.com/careers",                             "name": "MapBox", "category": "general"},
    {"type": "career_page", "id": "https://myedspace.io/careers",                               "name": "MyEdSpace", "category": "general"},
    {"type": "career_page", "id": "https://g20.io/careers",                                     "name": "G-20 Group", "category": "general"},
    {"type": "career_page", "id": "https://www.8am.com/careers/",                               "name": "8am", "category": "general"},
    {"type": "career_page", "id": "https://activa.io/careers",                                  "name": "Activa Digital", "category": "general"},
    {"type": "career_page", "id": "https://praktikaai.com/careers",                             "name": "Praktika.ai", "category": "general"},
    {"type": "career_page", "id": "https://www.yelp.careers/us/en",                             "name": "Yelp", "category": "general"},
    {"type": "career_page", "id": "https://ftmo.io/careers",                                    "name": "FTMO", "category": "general"},
    {"type": "career_page", "id": "https://www.searchapi.io/careers",                           "name": "SearchApi", "category": "general"},
    {"type": "career_page", "id": "https://huspy.com/careers",                                  "name": "Huspy", "category": "general"},
    {"type": "career_page", "id": "https://www.filevine.com/jobs/",                             "name": "Filevine", "category": "general"},
    {"type": "career_page", "id": "https://resistantai.com/careers",                            "name": "Resistant AI", "category": "general"},
    {"type": "career_page", "id": "https://granton.com/careers",                                "name": "Granton", "category": "general"},
    {"type": "career_page", "id": "https://nice.io/careers",                                    "name": "NiCE", "category": "general"},
    {"type": "career_page", "id": "https://www.paylocity.com/careers/",                         "name": "Paylocity", "category": "general"},
    {"type": "career_page", "id": "https://ppl3.com/careers",                                   "name": "ppl3", "category": "general"},
    {"type": "career_page", "id": "https://libeara.com/careers/",                               "name": "Libeara", "category": "general"},
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
