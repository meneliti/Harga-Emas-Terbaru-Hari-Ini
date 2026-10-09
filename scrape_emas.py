#!/usr/bin/env python3
"""
Harga Emas Scraper
==================
Mengambil harga emas batangan (Logam Mulia ANTAM & penjual lain) dari 18 penyedia
via logam-mulia-api.iamutaki.workers.dev, lalu memperbarui tabel harga di README.md:
harga per gram tiap penyedia + buyback, diurutkan termurah -> termahal.

Cara pakai:
    python3 scrape_emas.py            # update README.md
    python3 scrape_emas.py --print    # hanya tampilkan hasil di terminal

Tidak butuh API key / dependensi eksternal (stdlib murni, Python 3.8+).
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

BASE = "https://logam-mulia-api.iamutaki.workers.dev/api/prices"
README = "README.md"

PENYEDIA = [
    "anekalogam", "hargaemas-org", "lakuemas", "sakumas", "kursdolar",
    "cermati", "indogold", "hargaemas-net", "hargaemas-com", "treasury",
    "logammulia", "emasku", "hartadinataabadi", "galeri24", "sampoernagold",
    "bankbsi", "brankaslm", "pegadaian",
]

WIB = timezone(timedelta(hours=7))
BULAN_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
            "Agustus", "September", "Oktober", "November", "Desember"]


def fetch(source):
    url = f"{BASE}/{source}"
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def rupiah(v):
    if v is None:
        return "–"
    return f"Rp{v:,.0f}".replace(",", ".")


def tgl_id(iso):
    d = datetime.fromisoformat(iso)
    return f"{d.day} {BULAN_ID[d.month - 1]} {d.year}"


def collect():
    """Kumpulkan harga per gram (1 gr) dari tiap penyedia."""
    rows = []
    dates = set()
    for src in PENYEDIA:
        try:
            d = fetch(src)
        except Exception as e:
            print(f"  skip {src}: {e}")
            continue
        for x in d.get("data", []):
            w = x.get("weight") or 0
            unit = (x.get("weightUnit") or "").lower()
            if unit not in ("gr", "gram") or abs(w - 1.0) > 1e-9:
                continue
            if not x.get("sellPrice") or x["sellPrice"] < 1_000_000:
                # buang harga tak wajar (kurs non-emas, emas digital pecahan, dsb.)
                continue
            if x.get("materialType") and "digital" in x["materialType"].lower():
                continue
            dates.add(x.get("recordedDate") or "")
            rows.append({
                "penyedia": x.get("displayName") or src,
                "jenis": (x.get("materialType") or "").strip()[:60],
                "jual": x["sellPrice"],
                "buyback": x.get("buybackPrice") or None,
                "tanggal": x.get("recordedDate"),
            })
    return rows, dates


def build_table(rows):
    rows = sorted(rows, key=lambda r: r["jual"])
    lines = []
    lines.append("| Peringkat | Penyedia | Jenis Emas | Harga Jual/gram | Buyback/gram | Selisih Jual–Buyback |")
    lines.append("|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        selisih = (r["jual"] - r["buyback"]) if r["buyback"] else None
        lines.append(
            f"| {i} | **{r['penyedia']}** | {r['jenis'] or 'Emas Batangan'} "
            f"| {rupiah(r['jual'])} | {rupiah(r['buyback'])} | {rupiah(selisih)} |"
        )
    return "\n".join(lines), rows


def main():
    show_only = "--print" in sys.argv
    print("Mengambil harga dari 18 penyedia...")
    rows, dates = collect()
    n_penyedia = len(set(r["penyedia"] for r in rows))
    print(f"Dapat {len(rows)} baris harga per-gram dari {n_penyedia} penyedia")
    if not rows:
        print("Tidak ada data, batal.")
        return 1

    table, sorted_rows = build_table(rows)
    if show_only:
        print(table)
        return 0

    now = datetime.now(WIB)
    updated = now.strftime(f"%d {BULAN_ID[now.month - 1]} %Y, %H:%M WIB")
    tgl_data = tgl_id(max(d for d in dates if d)) if dates else updated.split(",")[0]
    termurah, termahal = sorted_rows[0], sorted_rows[-1]
    rata = sum(r["jual"] for r in sorted_rows) // len(sorted_rows)

    header = f"""# 💰 Harga Emas Terbaru Hari Ini

Pantauan **harga emas batangan per gram** dari **18 penyedia emas resmi di Indonesia** — ANTAM (Logam Mulia), Pegadaian, Bank BSI, dan penjual lainnya — diurutkan dari **termurah ke termahal**. Data diperbarui otomatis **setiap 6 jam**.

> 📅 **Data per tanggal: {tgl_data}** — terakhir diperbarui: {updated}

## 📊 Ringkasan Harga Emas per Gram

| Indikator | Harga |
|---|---|
| 🟢 **Termurah** | **{rupiah(termurah['jual'])}** ({termurah['penyedia']}) |
| 🔴 **Termahal** | {rupiah(termahal['jual'])} ({termahal['penyedia']}) |
| ⚖️ **Rata-rata 18 penyedia** | {rupiah(rata)} |

## 📋 Tabel Harga Emas per Gram (Termurah → Termahal)

{table}
"""
    footer = """
## 📖 Keterangan

- **Harga Jual/gram** — harga beli emas batangan 1 gram oleh konsumen
- **Buyback/gram** — harga jual kembali emas ke penyedia (buyback)
- **Selisih** — spread jual–buyback; makin kecil makin menguntungkan pemilik emas
- Data dikumpulkan dari 18 penyedia: ANTAM (Aneka Logam, Logam Mulia), Pegadaian, Bank BSI, Indogold, Treasury, Lakuemas, Sakumas, dan lainnya

## ⚙️ Cara Kerja

Script `scrape_emas.py` mengambil data dari agregator harga logam mulia, menyaring **hanya gramasi 1 gram**, lalu memperbarui tabel di halaman ini secara otomatis setiap 6 jam.

Jalankan sendiri:

```bash
python3 scrape_emas.py          # update README.md
python3 scrape_emas.py --print  # lihat hasil di terminal
```

Tanpa dependensi eksternal — cukup Python 3.8+.

---

*by PT. Pastiin Siber Indonesia*
"""
    content = header + "\n" + table + "\n" + footer
    with open(README, "w") as f:
        f.write(content)
    print(f"README.md diperbarui ({len(rows)} penyedia, tanggal {tgl_data})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
