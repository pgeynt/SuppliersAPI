from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import cloudscraper
import time

class KadiogluScraper:
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
            
            # Ürün kartlarını bul
            product_cards = self.driver.find_elements(By.CLASS_NAME, "product-cart-wrap")
            results = []
            
            # Her ürün kartı için yeni sekmede detay sayfasını aç
            for card in product_cards:
                try:
                    product_link = card.find_element(By.CSS_SELECTOR, "div.product-img a").get_attribute('href')
                    
                    # Yeni sekmede ürün detayını aç
                    self.driver.execute_script(f"window.open('{product_link}', '_blank')")
                    time.sleep(2)
                    
                    # Yeni sekmeye geç
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    
                    # Ürün adı
                    urun_adi = self.driver.find_element(By.XPATH, '//*[@id="form1"]/main/div[2]/div/div/div/div[1]/div[2]/div/h2').text.strip()
                    
                    # Stok durumu
                    stok_durumu = self.driver.find_element(By.XPATH, '//*[@id="form1"]/main/div[2]/div/div/div/div[1]/div[2]/div/div[5]/div[1]/span').text.strip()
                    
                    # KDV Hariç fiyatlar
                    kdv_haric = {
                        "TL": self.driver.find_element(By.XPATH, '//*[@id="form1"]/main/div[2]/div/div/div/div[1]/div[2]/div/div[2]/div[1]/table/tbody/tr[2]/td[1]').text.strip(),
                        "USD": self.driver.find_element(By.XPATH, '//*[@id="form1"]/main/div[2]/div/div/div/div[1]/div[2]/div/div[2]/div[1]/table/tbody/tr[2]/td[2]').text.strip(),
                        "EUR": self.driver.find_element(By.XPATH, '//*[@id="form1"]/main/div[2]/div/div/div/div[1]/div[2]/div/div[2]/div[1]/table/tbody/tr[2]/td[3]').text.strip()
                    }
                    
                    # KDV Dahil fiyatlar
                    kdv_dahil = {
                        "TL": self.driver.find_element(By.XPATH, '//*[@id="form1"]/main/div[2]/div/div/div/div[1]/div[2]/div/div[2]/div[2]/table/tbody/tr[2]/td[1]').text.strip(),
                        "USD": self.driver.find_element(By.XPATH, '//*[@id="form1"]/main/div[2]/div/div/div/div[1]/div[2]/div/div[2]/div[2]/table/tbody/tr[2]/td[2]').text.strip(),
                        "EUR": self.driver.find_element(By.XPATH, '//*[@id="form1"]/main/div[2]/div/div/div/div[1]/div[2]/div/div[2]/div[2]/table/tbody/tr[2]/td[3]').text.strip()
                    }
                    
                    # Ek bilgiler
                    additional_info = {
                        "Barkod": self.driver.find_element(By.XPATH, '//*[@id="form1"]/main/div[2]/div/div/div/div[1]/div[2]/div/div[6]/ul[2]/li[1]/span').text.strip(),
                        "KDV": self.driver.find_element(By.XPATH, '//*[@id="form1"]/main/div[2]/div/div/div/div[1]/div[2]/div/div[6]/ul[1]/li[3]/span').text.strip()
                    }
                    
                    result = {
                        "urun_adi": urun_adi,
                        "stok_durumu": stok_durumu,
                        "fiyatlar": {
                            "kdv_haric": kdv_haric,
                            "kdv_dahil": kdv_dahil
                        },
                        "ek_bilgiler": additional_info
                    }
                    
                    results.append(result)
                    
                    # Sekmeyi kapat ve ana sekmeye geri dön
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    
                except Exception as e:
                    print(f"Ürün detay okuma hatası: {str(e)}")
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
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