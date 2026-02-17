import requests
import csv

SHOP = "bachmann-handel.de"

url = f"https://{SHOP}/products.json?limit=250"
products = requests.get(url).json()["products"]

rows = []

for p in products:
    handle = p.get("handle","")
    title = p.get("title","")
    link = f"https://{SHOP}/products/{handle}"

    for v in p.get("variants",[]):
        price = v.get("price","")
        ean = v.get("barcode","")

        if price == "0.00":
            continue

        rows.append([
            title,
            price,
            "EUR",
            link,
            ean,
            "Neu",
            "0.00",
            "2-4 Tage"
        ])

with open("idealo.csv","w",newline="",encoding="utf-8") as f:
    writer = csv.writer(f,delimiter=";")
    writer.writerow(["title","price","currency","link","ean","condition","shipping","delivery"])
    writer.writerows(rows)

print("Feed erstellt")
