"""Danh sách mã cổ phiếu: rổ VN50 (chỉ số VNX50 — 50 mã lớn nhất HOSE + HNX) và nhóm ngân hàng."""

import re

# Rổ VN50 lấy trực tiếp từ SSI (nhóm VNX50) để tự cập nhật khi rổ được cơ cấu lại.
# Danh sách dưới đây chỉ dùng dự phòng khi API lỗi — thành phần VNX50 tại ngày 07/10/2026.
VN50_GROUP = "VNX50"
VN50_FALLBACK = [
    "ACB", "BID", "BSR", "CTG", "DCM", "DPM", "DXG", "EIB", "FPT", "FRT",
    "GEE", "GEX", "GMD", "HCM", "HDB", "HPG", "IDC", "KBC", "KDH", "LPB",
    "MBB", "MSB", "MSN", "MWG", "NLG", "NVL", "PDR", "PLX", "PNJ", "POW",
    "PVS", "SHB", "SHS", "SSI", "STB", "TCB", "TPB", "VCB", "VCG", "VCI",
    "VHM", "VIB", "VIC", "VIX", "VJC", "VND", "VNM", "VPB", "VPI", "VRE",
]

# Ngân hàng niêm yết (HOSE, HNX, UPCoM)
BANKS = [
    "VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "HDB", "STB", "TPB",
    "SHB", "VIB", "LPB", "SSB", "EIB", "MSB", "OCB", "NAB", "ABB", "BVB",
    "KLB", "VAB", "BAB", "SGB", "PGB", "NVB", "VBB",
]

DEFAULT_SYMBOLS = ["VCB", "FPT", "HPG"]


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
