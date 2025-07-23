from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import cloudscraper
import time

class AsnetScraper:
    def __init__(self, supplier_data):
        self.supplier = supplier_data
        self.driver = None
        self.wait = None
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
    
    def setup_driver(self):
        # CloudScraper için özel Chrome seçenekleri
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": self.scraper.headers['User-Agent']
        })
        self.wait = WebDriverWait(self.driver, 10)
    
    def login(self):
        try:
            # Önce CloudScraper ile siteye erişim sağla
            response = self.scraper.get(self.supplier['website'])
            if response.status_code != 200:
                raise Exception(f"Site erişimi başarısız: {response.status_code}")
            
            # Selenium ile devam et
            self.driver.get(self.supplier['website'])
            
            # Dealer code gir
            dealer_code_input = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, self.supplier['xpaths']['dealer_code'])))
            dealer_code_input.send_keys(self.supplier['dealer_code'])
            
            # Kullanıcı adı gir
            username_input = self.driver.find_element(By.XPATH, self.supplier['xpaths']['username'])
            username_input.send_keys(self.supplier['credentials']['username'])
            
            # Şifre gir
            password_input = self.driver.find_element(By.XPATH, self.supplier['xpaths']['password'])
            password_input.send_keys(self.supplier['credentials']['password'])
            
            # Login butonuna tıkla
            login_button = self.driver.find_element(By.XPATH, self.supplier['xpaths']['login_button'])
            login_button.click()
            
            # Login işleminin tamamlanması için bekleme
            time.sleep(3)
            
        except Exception as e:
            raise Exception(f"Login hatası: {str(e)}")
    
    def search_product(self, search_text):
        try:
            # Arama kutusunu bul ve metni gir
            search_input = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, self.supplier['xpaths']['search_input'])))
            search_input.clear()  # Önceki aramayı temizle
            search_input.send_keys(search_text)
            
            # Enter tuşuna bas
            search_input.send_keys(Keys.RETURN)
            
            # Sonuçların yüklenmesi için bekleme
            time.sleep(3)
            
            # Ürün kartlarını bul
            product_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.mb30.urun-list.col-12.urun-single")
            
            # Sonuçları topla
            results = []
            
            for card in product_cards:
                try:
                    # Ürün adını al
                    urun_adi = card.find_element(By.CSS_SELECTOR, "span.urun__baslik").text.strip()
                    
                    # Fiyat bilgisini al
                    fiyat_element = card.find_element(By.CSS_SELECTOR, "span.urun__fiyat")
                    fiyat_text = fiyat_element.text.strip()
                    # "51,74 USD" formatındaki fiyatı düzenle
                    fiyat = fiyat_text.replace('\n', '').replace('sup>', '')
                    
                    # Stok bilgisini al
                    stok_element = card.find_element(By.CSS_SELECTOR, "span.urun__stok")
                    stok_text = stok_element.text.strip()
                    # "Ankara : (100+)" formatındaki stok bilgisini düzenle
                    stok_bilgisi = stok_text.strip()
                    
                    result = {
                        "urun_adi": urun_adi,
                        "fiyat": fiyat,
                        "stok_bilgisi": stok_bilgisi
                    }
                    
                    # Boş olmayan sonuçları ekle
                    if result["urun_adi"] and result["fiyat"]:
                        results.append(result)
                        
                except Exception as e:
                    print(f"Ürün kartı okuma hatası: {str(e)}")
                    continue
            
            return results
            
        except Exception as e:
            print(f"Arama işlemi hatası: {str(e)}")
            return []
    
    def close_driver(self):
        if self.driver:
            self.driver.quit()
    
    def perform_search(self, search_text):
        try:
            self.setup_driver()
            self.login()
            results = self.search_product(search_text)
            self.close_driver()
            
            if len(results) == 0:
                return {
                    "status": "no_results",
                    "message": f"Arama yapıldı fakat '{search_text}' için ürün bulunamadı",
                    "results": [],
                    "total_results": 0,
                    "search_text": search_text
                }
            
            return {
                "status": "success",
                "message": "İşlemler başarıyla tamamlandı",
                "results": results,
                "total_results": len(results),
                "search_text": search_text
            }
            
        except Exception as e:
            self.close_driver()
            return {
                "status": "error",
                "message": f"Bir hata oluştu: {str(e)}",
                "results": [],
                "total_results": 0,
                "search_text": search_text
            } 