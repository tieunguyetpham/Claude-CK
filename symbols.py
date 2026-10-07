"""Danh sách mã cổ phiếu: rổ VN50 (50 mã vốn hóa lớn, thanh khoản cao) và nhóm ngân hàng."""

import re

# VN30 + 20 mã vốn hóa lớn, thanh khoản cao khác trên HOSE
VN50 = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "LPB", "MBB", "MSN", "MWG", "PLX", "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE",
    "DGC", "EIB", "FRT", "GEX", "HCM", "KBC", "KDH", "MSB", "NLG", "OCB",
    "PNJ", "POW", "REE", "VCI", "VND", "DCM", "DPM", "VHC", "HSG", "VCG",
]

# Ngân hàng niêm yết (HOSE, HNX, UPCoM)
BANKS = [
    "VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "HDB", "STB", "TPB",
    "SHB", "VIB", "LPB", "SSB", "EIB", "MSB", "OCB", "NAB", "ABB", "BVB",
    "KLB", "VAB", "BAB", "SGB", "PGB",
]

GROUPS = {"Rổ VN50": VN50, "Ngân hàng": BANKS}


def is_bank(symbol: str) -> bool:
    return symbol.upper() in BANKS


def parse_symbols(selected: list, typed: str) -> tuple[list, list]:
    """Gộp mã chọn + mã gõ tay, chuẩn hóa chữ hoa, bỏ trùng; trả (hợp lệ, không hợp lệ)."""
    raw = list(selected or []) + re.split(r"[,;\s]+", (typed or "").upper())
    valid, invalid = [], []
    for s in (x.strip() for x in raw):
        if not s:
            continue
        if not re.fullmatch(r"[A-Z0-9]{3,10}", s):
            if s not in invalid:
                invalid.append(s[:20])  # cắt ngắn chuỗi rác quá dài khi hiển thị
        elif s not in valid:
            valid.append(s)
    return valid, invalid
