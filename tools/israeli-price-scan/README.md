# Israeli price-transparency scanner — Dr Pepper Zero in Tel Aviv

Scrapes the price XML files that Israeli food retailers are required to publish, and
finds which stores near a given point stock a given product.

## Portals covered

| Portal | Module | Chains |
|---|---|---|
| `url.publishedprices.co.il` | `pp_client.py` | Rami Levy, Tiv Taam, Yohananof, Dor Alon/AM:PM, Super Yuda, Osher Ad, Keshet Teamim, Freshmarket, Politzer, Salah Dabah, Stop Market, Cofix, Yellow/Paz |
| `prices.shufersal.co.il` | `shufersal.py` | Shufersal (Sheli / Deal / Express / Yesh) |
| `prices.carrefour.co.il` | `carrefour.py` | Carrefour, Yenot Bitan |
| `*.binaprojects.com` | `bina.py` | Good Pharm, King Store, Bareket, Super Sapir, Zol VeBegadol, Shuk HaIr, Maayan 2000, Shefa Birkat Hashem, City Market Kiryat Gat |
| `citymarket-shops.co.il` | `citymarket.py` | City Market group |

Portal quirks handled: the login CSRF token on publishedprices rotates after
authentication; binaprojects serves `.gz`-named files that are actually ZIP archives and
hides the blob URL behind `Download.aspx`; Shufersal signs blob URLs per listing page.

## Pipeline

1. `pp_stores.py` — pull every chain's `Stores` file (store id → address, CBS city code).
2. `scan_nationwide.py {pp,shufersal,carrefour,bina,citymarket}` — sweep every store's
   latest `PriceFull` and collect every Dr Pepper item found anywhere in the country.
3. `consolidate.py` — build the barcode → product map from all the names retailers gave
   each barcode, so a SKU can be classified as zero-sugar even where one store's own item
   name omits it.
4. `final_verify.py` — re-read every Tel Aviv store and match by **barcode**, not name.
   This is what caught `8435185953711` listed as `דוקטר זירו` (no "פפר" in the name).
5. `geocode.py` — Nominatim lookup + haversine distance from Ben Gurion Blvd.

## Notes

* `Price*` is a delta; always take `PriceFull*`.
* Tel Aviv is CBS city code `5000`; many chains put the code, not the name, in `<City>`.
* A published price row means the SKU is in the store's price list, not that it is
  physically in stock right now.
