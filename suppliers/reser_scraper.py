from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import cloudscraper
import time

class ReserScraper:
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
            response = self.scraper.get(self.supplier['website'])
            if response.status_code != 200:
                raise Exception(f"Site erişimi başarısız: {response.status_code}")
            
            self.driver.get(self.supplier['website'])
            
            dealer_code_input = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, self.supplier['xpaths']['dealer_code'])))
            dealer_code_input.send_keys(self.supplier['dealer_code'])
            
            username_input = self.driver.find_element(By.XPATH, self.supplier['xpaths']['username'])
            username_input.send_keys(self.supplier['credentials']['username'])
            
            password_input = self.driver.find_element(By.XPATH, self.supplier['xpaths']['password'])
            password_input.send_keys(self.supplier['credentials']['password'])
            
            login_button = self.driver.find_element(By.XPATH, self.supplier['xpaths']['login_button'])
            login_button.click()
            
            time.sleep(3)
            
        except Exception as e:
            raise Exception(f"Login hatası: {str(e)}")
    
    def search_product(self, search_text):
        try:
            search_input = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, self.supplier['xpaths']['search_input'])))
            search_input.clear()
            search_input.send_keys(search_text)
            search_input.send_keys(Keys.RETURN)
            
            time.sleep(3)
            
            # Ürün tablosunu bul
            product_table = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//*[@id='myTable']/tbody")))
            
            # Ürün satırlarını bul (promotion-head_kategori hariç)
            product_rows = product_table.find_elements(By.CSS_SELECTOR, "tr.cat-list-stok")
            results = []
            
            for row in product_rows:
                try:
                    # Ürün adı
                    urun_adi = row.find_element(By.CSS_SELECTOR, "td:nth-child(5) a").get_attribute('title')
                    
                    # Fiyatlar
                    size_ozel = row.find_element(By.CSS_SELECTOR, "td:nth-child(6)").text.strip()
                    bayi_fiyat = row.find_element(By.CSS_SELECTOR, "td:nth-child(7)").text.strip()
                    tesk_fiyat = row.find_element(By.CSS_SELECTOR, "td:nth-child(8)").text.strip()
                    
                    # KDV ve Stok
                    kdv = row.find_element(By.CSS_SELECTOR, "td:nth-child(9)").text.strip()
                    stok = row.find_element(By.CSS_SELECTOR, "td:nth-child(10)").text.strip()
                    
                    result = {
                        "urun_adi": urun_adi,
                        "fiyatlar": {
                            "size_ozel": size_ozel,
                            "bayi_fiyat": bayi_fiyat,
                            "tesk_fiyat": tesk_fiyat
                        },
                        "kdv": kdv,
                        "stok_durumu": stok
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    print(f"Ürün satırı okuma hatası: {str(e)}")
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