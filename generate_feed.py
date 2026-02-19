import csv
import requests

SHOP = "bachmann-handel.de"
TEMPLATE_IN = "idealo_template.csv"
OUT_FEED = "idealo.csv"

BS3000_DESC = (
    "BEITZ BS-3000 X3 Elite eine Professionelle Geldzählmaschine mit modernster Sensorik für zuverlässiges "
    "Zählen und Prüfen von Banknoten. Ausgestattet mit Dual-CIS-Technologie, UV-, MG-, IR- und MT-Erkennung "
    "sowie Seriennummern-Erfassung für höchste Sicherheit. Ideal für Handel, Banken, Geldtransporte, "
    "Tankstellen und Unternehmen mit hohem Bargeldaufkommen. Robuste Bauweise, hohe Zählgeschwindigkeit "
    "und präzise Wert- und Stückzählung."
)

def fetch_all_products():
    """
    Shopify /products.json liefert max. 250 pro Seite.
    Pagination via since_id (funktioniert zuverlässig ohne API-Key).
    """
    all_products = []
    since_id = 0

    for _ in range(50):  # Safety-Limit
        url = f"https://{SHOP}/products.json?limit=250&since_id={since_id}"
        r = requests.get(url, timeout=45)
        r.raise_for_status()
        products = r.json().get("products", [])
        if not products:
            break

        all_products.extend(products)
        since_id = products[-1].get("id", since_id)

    return all_products

def pick_best_image(product: dict) -> str:
    # bevorzugt: product["image"]["src"], sonst erstes Bild
    img = ""
    img_obj = product.get("image")
    if isinstance(img_obj, dict):
        img = (img_obj.get("src") or "").strip()
    if not img:
        imgs = product.get("images") or []
        if imgs and isinstance(imgs[0], dict):
            img = (imgs[0].get("src") or "").strip()
    return img

def build_variant_index(products):
    """
    Index: SKU -> (price, url, ean, image)
    """
    idx = {}

    for p in products:
        handle = (p.get("handle") or "").strip()
        if not handle:
            continue

        url = f"https://{SHOP}/products/{handle}"
        img = pick_best_image(p)

        for v in p.get("variants") or []:
            sku = (v.get("sku") or "").strip()
            if not sku:
                continue

            price = (v.get("price") or "").strip()  # Shopify liefert "123.45"
            ean = (v.get("barcode") or "").strip()

            idx[sku] = {
                "price": price,
                "url": url,
                "ean": ean,
                "image": img,
            }

    return idx

def looks_too_short(text: str) -> bool:
    t = (text or "").strip()
    return len(t) < 60  # Schwelle: zu kurz für Portale

# --- Daten holen
products = fetch_all_products()
variant_idx = build_variant_index(products)

# --- Template lesen (utf-8-sig = frisst BOM korrekt)
with open(TEMPLATE_IN, "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f, delimiter=";", quotechar='"')
    fieldnames = reader.fieldnames
    rows = list(reader)

missing_skus = []

# --- Update Logik
for row in rows:
    sku = (row.get("sku") or "").strip()
    if not sku:
        continue

    data = variant_idx.get(sku)
    if not data:
        missing_skus.append(sku)
        continue

    # Dynamische Felder aktualisieren:
    if data["price"]:
        row["price"] = data["price"]  # immer Punktformat
    if data["url"]:
        row["url"] = data["url"]
    if data["ean"]:
        row["eans"] = data["ean"]
    if data["image"]:
        row["imageUrls"] = data["image"]

    # BS-3000 Description automatisch „auffüllen“, falls im Template zu kurz
    title = (row.get("title") or "").upper()
    if "BS-3000" in title:
        if looks_too_short(row.get("description", "")):
            row["description"] = BS3000_DESC

# --- Output schreiben (Excel-kompatibel: UTF-8 mit BOM + Semikolon)
with open(OUT_FEED, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
        delimiter=";",          # Deutschland/Excel
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"OK: {OUT_FEED} geschrieben. Zeilen: {len(rows)}")
if missing_skus:
    print("WARN: SKUs im Template, aber nicht im Shopify gefunden:")
    for s in missing_skus:
        print(" -", s)
