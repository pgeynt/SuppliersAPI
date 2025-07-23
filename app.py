from flask import Flask, jsonify, request
import json
import cloudscraper
from suppliers.bulut_scraper import BulutScraper
from suppliers.eksa_scraper import EksaScraper
from suppliers.art_scraper import ArtScraper
from suppliers.asnet_scraper import AsnetScraper
from suppliers.oksid_scraper import OksidScraper
from suppliers.kadioglu_scraper import KadiogluScraper
from suppliers.biosis_scraper import BiosisScraper
from suppliers.reser_scraper import ReserScraper
import concurrent.futures

# Flask uygulamamızı oluşturuyoruz
app = Flask(__name__)

# CloudScraper instance'ı oluştur
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    }
)

# JSON dosyasını okuma fonksiyonu
def read_suppliers():
    try:
        with open('suppliers.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return {"suppliers": []}

def get_scraper(supplier):
    # Supplier'a göre uygun scraper'ı döndür
    if supplier['supplier_name'] == 'Bulut':
        return BulutScraper(supplier)
    elif supplier['supplier_name'] == 'Eksa':
        return EksaScraper(supplier)
    elif supplier['supplier_name'] == 'Art':
        return ArtScraper(supplier)
    elif supplier['supplier_name'] == 'Asnet':
        return AsnetScraper(supplier)
    elif supplier['supplier_name'] == 'Oksid':
        return OksidScraper(supplier)
    elif supplier['supplier_name'] == 'Kadioglu':
        return KadiogluScraper(supplier)
    elif supplier['supplier_name'] == 'Biosis':
        return BiosisScraper(supplier)
    elif supplier['supplier_name'] == 'Reser':
        return ReserScraper(supplier)
    else:
        raise ValueError(f"'{supplier['supplier_name']}' için scraper bulunamadı")

def search_supplier(supplier, search_text):
    try:
        scraper = get_scraper(supplier)
        result = scraper.perform_search(search_text)
        result['supplier_name'] = supplier['supplier_name']
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"{supplier['supplier_name']} için hata: {str(e)}",
            "supplier_name": supplier['supplier_name'],
            "results": [],
            "total_results": 0,
            "search_text": search_text
        }

@app.route('/search', methods=['POST'])
def search():
    # İstek gövdesinden verileri al
    data = request.get_json()
    
    if not data or 'supplier_ids' not in data or 'search_text' not in data:
        return jsonify({"error": "supplier_ids (liste olarak) ve search_text gerekli"}), 400
    
    if not isinstance(data['supplier_ids'], list):
        return jsonify({"error": "supplier_ids bir liste olmalıdır"}), 400
    
    # Tedarikçileri oku
    suppliers_data = read_suppliers()
    
    # İstenen ID'lere sahip tedarikçileri bul
    suppliers = []
    for supplier_id in data['supplier_ids']:
        supplier = next((s for s in suppliers_data['suppliers'] if s['id'] == supplier_id), None)
        if supplier:
            suppliers.append(supplier)
    
    if not suppliers:
        return jsonify({"error": "Hiçbir tedarikçi bulunamadı"}), 404
    
    # Paralel olarak tüm tedarikçilerde arama yap
    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(suppliers)) as executor:
        future_to_supplier = {
            executor.submit(search_supplier, supplier, data['search_text']): supplier 
            for supplier in suppliers
        }
        
        for future in concurrent.futures.as_completed(future_to_supplier):
            result = future.result()
            all_results.append(result)
    
    # Sonuçları düzenle
    successful_results = []
    failed_results = []
    no_results = []
    total_products = 0
    
    for result in all_results:
        if result['status'] == 'success':
            successful_results.append({
                'supplier_name': result['supplier_name'],
                'total_products': result['total_results'],
                'products': result['results']
            })
            total_products += result['total_results']
        elif result['status'] == 'error':
            failed_results.append({
                'supplier_name': result['supplier_name'],
                'error_message': result['message']
            })
        elif result['status'] == 'no_results':
            no_results.append(result['supplier_name'])
    
    response = {
        "status": "completed",
        "search_text": data['search_text'],
        "summary": {
            "total_suppliers_searched": len(all_results),
            "successful_searches": len(successful_results),
            "failed_searches": len(failed_results),
            "suppliers_with_no_results": len(no_results),
            "total_products_found": total_products
        },
        "results": {
            "successful_searches": successful_results,
            "failed_searches": failed_results,
            "suppliers_with_no_results": no_results
        }
    }
    
    return jsonify(response)

# Tüm tedarikçileri getiren endpoint
@app.route('/suppliers', methods=['GET'])
def get_suppliers():
    data = read_suppliers()
    return jsonify(data)

# Eğer bu dosya direkt çalıştırılırsa, uygulamayı başlatıyoruz
if __name__ == '__main__':
    # Debug modu açık olarak uygulamayı 5000 portunda çalıştırıyoruz
    app.run(debug=True, port=5000)
