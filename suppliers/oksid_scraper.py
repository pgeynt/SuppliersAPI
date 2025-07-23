from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import cloudscraper
import time
import requests
from PIL import Image
from io import BytesIO
import base64

class OksidScraper:
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
    
    def solve_captcha(self, image_element):
        try:
            # Captcha resminin src attribute'unu al
            image_url = image_element.get_attribute('src')
            captcha_text = None  # Değişkeni başta tanımla
            
            # Eğer relative URL ise absolute URL'e çevir
            if not image_url.startswith('http'):
                # Doğru base URL'i oluştur
                base_url = "https://www.oksid.com.tr"
                if not image_url.startswith('/'):
                    image_url = '/' + image_url
                image_url = base_url + image_url
            
            print(f"Captcha URL: {image_url}")  # Debug için URL'i yazdır
            
            # İlk yöntem: URL ile dene
            try:
                # OCR Space API'ye istek at
                payload = {
                    'url': image_url,
                    'isOverlayRequired': False,
                    'apikey': self.supplier['credentials']['ocr_api_key'],
                    'language': 'eng',
                    'scale': True,
                    'OCREngine': 2,
                    'filetype': 'PNG'
                }
                
                response = requests.post(
                    'https://api.ocr.space/parse/image',
                    data=payload,
                    timeout=30
                )
                
                result = response.json()
                print(f"OCR API Yanıtı: {result}")
                
                if result.get('ParsedResults') and result['ParsedResults'][0].get('ParsedText'):
                    captcha_text = ''.join(c for c in result['ParsedResults'][0]['ParsedText'].strip() if c.isalnum())
                    print(f"URL ile Çözülen Captcha: {captcha_text}")
            except Exception as e:
                print(f"URL yöntemi hatası: {str(e)}")
            
            # İkinci yöntem: Screenshot ile dene
            if not captcha_text:
                try:
                    # Screenshot al
                    image_element.screenshot('captcha.png')
                    
                    # Resmi base64'e çevir
                    with open('captcha.png', 'rb') as image_file:
                        base64_image = base64.b64encode(image_file.read()).decode()
                    
                    # OCR Space API'ye base64 ile istek at
                    payload = {
                        'base64Image': f'data:image/png;base64,{base64_image}',
                        'isOverlayRequired': False,
                        'apikey': self.supplier['credentials']['ocr_api_key'],
                        'language': 'eng',
                        'scale': True,
                        'OCREngine': 2,
                        'filetype': 'PNG'
                    }
                    
                    response = requests.post(
                        'https://api.ocr.space/parse/image',
                        data=payload,
                        timeout=30
                    )
                    
                    result = response.json()
                    print(f"Base64 OCR API Yanıtı: {result}")
                    
                    if result.get('ParsedResults') and result['ParsedResults'][0].get('ParsedText'):
                        captcha_text = ''.join(c for c in result['ParsedResults'][0]['ParsedText'].strip() if c.isalnum())
                        print(f"Screenshot ile Çözülen Captcha: {captcha_text}")
                except Exception as e:
                    print(f"Screenshot yöntemi hatası: {str(e)}")
            
            if captcha_text:
                return captcha_text
            else:
                raise Exception("Hiçbir yöntem ile captcha çözülemedi")
            
        except Exception as e:
            print(f"Captcha çözme hatası detayı: {str(e)}")
            raise Exception(f"Captcha çözme hatası: {str(e)}")
    
    def login(self):
        try:
            # Önce CloudScraper ile siteye erişim sağla
            response = self.scraper.get(self.supplier['website'])
            if response.status_code != 200:
                raise Exception(f"Site erişimi başarısız: {response.status_code}")
            
            # Selenium ile devam et
            self.driver.get(self.supplier['website'])
            
            # Kullanıcı adı gir
            username_input = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, self.supplier['xpaths']['username'])))
            username_input.send_keys(self.supplier['credentials']['username'])
            
            # Şifre gir
            password_input = self.driver.find_element(By.XPATH, self.supplier['xpaths']['password'])
            password_input.send_keys(self.supplier['credentials']['password'])
            
            # Captcha'yı çöz
            captcha_image = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, self.supplier['xpaths']['captcha_image'])))
            
            # Birkaç deneme hakkı ver
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    captcha_text = self.solve_captcha(captcha_image)
                    
                    # Captcha'yı gir
                    captcha_input = self.driver.find_element(By.XPATH, self.supplier['xpaths']['captcha_input'])
                    captcha_input.clear()
                    captcha_input.send_keys(captcha_text)
                    
                    # Login butonuna tıkla
                    login_button = self.driver.find_element(By.XPATH, self.supplier['xpaths']['login_button'])
                    login_button.click()
                    
                    # Login işleminin tamamlanması için bekleme
                    time.sleep(3)
                    
                    # Başarılı login kontrolü (ana sayfaya yönlendirme)
                    if self.supplier['main_page'] in self.driver.current_url:
                        print("Login başarılı!")
                        break
                    else:
                        print(f"Login denemesi {attempt + 1} başarısız, yeniden deneniyor...")
                        if attempt < max_attempts - 1:
                            # Yeni captcha için sayfayı yenile
                            self.driver.refresh()
                            time.sleep(2)
                            captcha_image = self.wait.until(EC.presence_of_element_located(
                                (By.XPATH, self.supplier['xpaths']['captcha_image'])))
                        else:
                            raise Exception("Maximum login denemesi aşıldı")
                    
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise Exception(f"Login başarısız: {str(e)}")
                    print(f"Deneme {attempt + 1} başarısız: {str(e)}")
                    continue
            
        except Exception as e:
            raise Exception(f"Login hatası: {str(e)}")

    def search_product(self, search_text):
        try:
            # Ana sayfaya git
            self.driver.get(self.supplier['main_page'])
            
            # Arama kutusunu bul ve metni gir
            search_input = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, self.supplier['xpaths']['search_input'])))
            search_input.clear()
            search_input.send_keys(search_text)
            search_input.send_keys(Keys.RETURN)
            
            time.sleep(3)
            
            # Ürün container'ını bul
            product_container = self.wait.until(EC.presence_of_element_located(
                (By.CLASS_NAME, "colProductIn.shwstock.shwcheck.colPrdList.product45")))
            
            # Ürün linklerini bul (sadece slideImg altındakiler)
            product_links = product_container.find_elements(By.CSS_SELECTOR, "ul li span.slideImg a.ihlog.product_click")
            results = []
            
            # Her ürün için yeni sekmede aç
            for link in product_links:
                try:
                    product_url = link.get_attribute('href')
                    
                    # Yeni sekmede ürün detayını aç
                    self.driver.execute_script(f"window.open('{product_url}', '_blank')")
                    time.sleep(2)
                    
                    # Yeni sekmeye geç
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    
                    # Ürün bilgilerini topla
                    urun_adi = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div[1]/div[1]/div[2]/div[4]/h1").text.strip()
                    
                    # KDV Hariç fiyat (tam ve küsürat birleştirme)
                    kdv_haric_tam = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div[1]/div[1]/div[2]/div[4]/ul/li[1]/span[2]").text.strip()
                    kdv_haric_kusurat = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div[1]/div[1]/div[2]/div[4]/ul/li[1]/span[2]/span").text.strip()
                    kdv_haric_dolar = f"{kdv_haric_tam}{kdv_haric_kusurat} USD"
                    
                    # KDV Dahil fiyatlar
                    kdv_dahil_dolar = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div[1]/div[1]/div[2]/div[4]/ul/li[2]/span[2]").text.strip()
                    kdv_dahil_tl = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div[1]/div[1]/div[2]/div[4]/ul/li[2]/strong").text.strip()
                    
                    # Tavsiye edilen SK fiyatları
                    sk_fiyat_dolar = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div[1]/div[1]/div[2]/div[4]/ul/li[3]/span[2]").text.strip()
                    sk_fiyat_tl = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div[1]/div[1]/div[2]/div[4]/ul/li[3]/span[3]/strong").text.strip()
                    
                    # Stok durumu
                    stok_durumu = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div[1]/div[1]/div[2]/div[4]/div[4]/div[1]/span").text.strip()
                    
                    result = {
                        "urun_adi": urun_adi,
                        "fiyatlar": {
                            "kdv_haric": {
                                "USD": kdv_haric_dolar
                            },
                            "kdv_dahil": {
                                "USD": kdv_dahil_dolar,
                                "TL": kdv_dahil_tl
                            },
                            "tavsiye_edilen_sk": {
                                "USD": sk_fiyat_dolar,
                                "TL": sk_fiyat_tl
                            }
                        },
                        "stok_durumu": stok_durumu
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