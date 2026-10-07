"""Danh sách mã cổ phiếu: rổ chỉ số VN100 (100 mã vốn hóa lớn nhất HOSE) và nhóm ngân hàng."""

import re

# Rổ chỉ số lấy trực tiếp từ SSI để tự cập nhật khi rổ được cơ cấu lại.
# Đổi rổ (VN30, VNX50, VN100...) chỉ cần sửa BASKET_GROUP và danh sách dự phòng.
BASKET_GROUP = "VN100"
BASKET_MIN_SIZE = 80  # SSI trả ít hơn số này -> coi như lỗi, dùng danh sách dự phòng
# Chỉ dùng dự phòng khi API lỗi — thành phần VN100 tại ngày 07/10/2026.
BASKET_FALLBACK = [
    "ACB", "ANV", "BAF", "BCM", "BID", "BMP", "BSI", "BSR", "BVH", "BWE",
    "CII", "CMG", "CTD", "CTG", "CTR", "CTS", "DBC", "DCM", "DGW", "DIG",
    "DPM", "DSE", "DXG", "EIB", "EVF", "FPT", "FRT", "FTS", "GAS", "GEE",
    "GEX", "GMD", "GVR", "HAG", "HCM", "HDB", "HDG", "HHV", "HPG", "HSG",
    "HT1", "KBC", "KDC", "KDH", "KOS", "LPB", "MBB", "MCH", "MSB", "MSN",
    "MWG", "NAB", "NKG", "NLG", "NT2", "NVL", "OCB", "PAN", "PC1", "PDR",
    "PHR", "PLX", "PNJ", "POW", "PVD", "PVT", "REE", "SAB", "SBT", "SHB",
    "SIP", "SJS", "SSB", "SSI", "STB", "TAL", "TCB", "TCH", "TCX", "TPB",
    "VCB", "VCG", "VCI", "VCK", "VGC", "VHC", "VHM", "VIB", "VIC", "VIX",
    "VJC", "VND", "VNM", "VPB", "VPI", "VPL", "VPX", "VRE", "VSC", "VTP",
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
