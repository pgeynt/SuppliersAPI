from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import cloudscraper
import time

class BulutScraper:
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
        # Web sitesine git
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
    
    def search_product(self, search_text):
        # Arama kutusunu bul ve metni gir
        search_input = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, self.supplier['xpaths']['search_input'])))
        search_input.send_keys(search_text)
        
        # Arama butonuna tıkla
        search_button = self.driver.find_element(By.XPATH, self.supplier['xpaths']['search_button'])
        search_button.click()
        
        # Sonuçların yüklenmesi için bekleme
        time.sleep(3)
        
        # Ürün kartlarını bul
        product_cards = self.driver.find_elements(By.CLASS_NAME, "product")
        
        # Sonuçları topla
        results = []
        
        for card in product_cards:
            try:
                # Ürün adını al
                name_element = card.find_element(By.CLASS_NAME, "name")
                urun_adi = name_element.text.strip()
                
                # Stok kodunu al
                stok_no = card.find_element(By.CLASS_NAME, "stokno").text.strip()
                
                # Özel fiyatı al
                ozel_fiyat_element = card.find_element(By.CLASS_NAME, "price1")
                ozel_fiyat = ozel_fiyat_element.find_element(By.CLASS_NAME, "price").text.strip()
                
                # Bayi fiyatını al
                bayi_fiyat_element = card.find_element(By.CLASS_NAME, "price2")
                bayi_fiyat = bayi_fiyat_element.find_element(By.CLASS_NAME, "price").text.strip()
                
                # Stok durumunu al
                stok_elements = card.find_elements(By.CLASS_NAME, "stock")
                stok_bilgisi = []
                for stok in stok_elements:
                    try:
                        miktar = stok.find_element(By.TAG_NAME, "span").text.strip()
                        tip = stok.find_element(By.CLASS_NAME, "sname").text.strip()
                        stok_bilgisi.append(f"{tip} {miktar}")
                    except:
                        continue
                
                result = {
                    "stok_kodu": stok_no,
                    "urun_adi": urun_adi,
                    "ozel_fiyat": ozel_fiyat,
                    "bayi_fiyat": bayi_fiyat,
                    "stok_bilgisi": stok_bilgisi
                }
                
                # Boş olmayan sonuçları ekle
                if result["urun_adi"] and (result["ozel_fiyat"] or result["bayi_fiyat"]):
                    results.append(result)
                    
            except Exception as e:
                print(f"Ürün kartı okuma hatası: {str(e)}")
                continue
        
        return results
    
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