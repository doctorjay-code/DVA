# -*- coding: utf-8 -*-
"""
포인트 사용 모듈 (배달의민족 및 빌마켓 쿠폰 자동 구매)
닥터빌 포인트로 빌마켓 상품 쿠폰을 자동 구매합니다.
"""

import time
import re
import os
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from .base_module import BaseModule

# 상수 정의
COUPON_PRICE = 9700  # 배달의민족 10,000원 쿠폰 가격 (포인트)
COUPON_VALUE = 10000  # 쿠폰 실제 가치 (원)
POINTS_PAGE_URL = "https://www.doctorville.co.kr/my/point/pointUseHistoryList"
COUPON_ORDER_URL = "https://mcircle.bizmarketb2b.com/Order/MCouponBulkOrder.aspx?guid=14152303&cate=0"
MY_PAGE_URL = "https://www.doctorville.co.kr/my/main"

class BaeminModule(BaseModule):
    def __init__(self, web_automation, gui_logger=None):
        super().__init__(web_automation, gui_logger)
    
    def get_current_points(self):
        """현재 포인트를 조회합니다."""
        try:
            from modules.points_check_module import PointsCheckModule
            points_module = PointsCheckModule(self.web_automation, self.gui_logger)
            
            if hasattr(self, 'gui_callbacks'):
                points_module.set_callbacks(self.gui_callbacks)
                if 'gui_instance' in self.gui_callbacks and self.gui_callbacks['gui_instance']:
                    points_module.gui_instance = self.gui_callbacks['gui_instance']
            
            result = points_module.get_user_info_summary()
            
            # 결과 데이터 추출 (표준화된 dict 또는 기존 dict 대응)
            data = result.get('data', result) if isinstance(result, dict) else {}
            
            if data and 'points' in data:
                points_str = str(data['points']).replace(',', '').replace('P', '').strip()
                try:
                    return int(points_str)
                except ValueError:
                    self.log_warning(f"포인트 파싱 실패: {data['points']}")
                    return 0
            return 0
            
        except Exception as e:
            self.log_error(f"포인트 조회 중 오류: {str(e)}")
            return 0
    
    def calculate_max_coupons(self, points, coupon_price=None):
        """최대 구매 가능한 쿠폰 수를 계산합니다."""
        price = coupon_price if coupon_price is not None else COUPON_PRICE
        return points // price
    
    def get_phone_number(self):
        """설정된 휴대폰 번호를 반환합니다."""
        phone_number = ""  # 기본 fallback값
        if hasattr(self, 'gui_callbacks') and 'gui_instance' in self.gui_callbacks and self.gui_callbacks['gui_instance']:
            try:
                val = self.gui_callbacks['gui_instance'].get_setting('baemin_phone')
                if val:
                    phone_number = str(val).strip()
            except Exception as e:
                self.log_warning(f"설정에서 휴대폰 번호 로드 실패: {e}")
        self.log_success(f"휴대폰 번호: {phone_number}")
        return phone_number

    def scrape_coupon_list(self) -> list:
        """
        빌마켓 카테고리 페이지를 Selenium으로 크롤링하여 상품 목록을 반환합니다.
        """
        main_window = None
        try:
            if not self.web_automation or not self.web_automation.driver:
                self.log_error("웹드라이버가 초기화되지 않았습니다.")
                return []
                
            driver = self.web_automation.driver
            main_window = driver.current_window_handle
            self.log_info("상품 목록 수집을 위해 빌마켓으로 이동 중...")
            
            # 빌마켓 세션 활성화 및 카테고리 페이지 이동
            if "pointUseHistoryList" not in driver.current_url:
                driver.get(POINTS_PAGE_URL)
                time.sleep(2)
            
            driver.execute_script("openPointShop();")
            
            # 빌마켓 탭 전환
            for i in range(10):
                if len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])
                    break
                time.sleep(0.5)
            else:
                self.log_error("빌마켓 탭이 열리지 않았습니다.")
                return []
                
            driver.get("https://mcircle.bizmarketb2b.com/Event/Category.aspx?Uid=21006")
            time.sleep(3)
            
            # HTML 파싱
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # swiper-slide 및 item_box 찾기
            items = soup.find_all(class_='swiper-slide') + soup.find_all(class_='item_box')
            seen_guids = set()
            coupon_list = []
            
            for item in items:
                a_tag = item.find('a', href=True)
                if not a_tag:
                    continue
                href = a_tag['href']
                
                guid_match = re.search(r'guid=(\d+)', href)
                if not guid_match:
                    continue
                guid = guid_match.group(1)
                
                if guid in seen_guids:
                    continue
                seen_guids.add(guid)
                
                # 상품명
                name_div = item.find(class_='item_n')
                if not name_div:
                    continue
                name = name_div.text.strip()
                
                # 포인트 가격
                price_div = item.find(class_='item_price_n')
                if not price_div:
                    continue
                price_text = ''.join(c for c in price_div.text if c.isdigit())
                if not price_text:
                    continue
                price = int(price_text)
                
                # 쿠폰 실제 가치 (원) - 이름에서 추출
                value = price
                value_match = re.search(r'(\d+)\s*(만원|천원|원)', name)
                if value_match:
                    val_num = int(value_match.group(1))
                    val_unit = value_match.group(2)
                    if val_unit == '만원':
                        value = val_num * 10000
                    elif val_unit == '천원':
                        value = val_num * 1000
                    else:
                        value = val_num
                
                # 아이콘 설정
                icon = "🎁"
                if "배달의민족" in name or "배민" in name:
                    icon = "🛵"
                elif "네이버" in name or "N페이" in name:
                    icon = "💚"
                elif "카카오" in name:
                    icon = "💛"
                elif any(chk in name for chk in ["치킨", "굽네", "교촌", "BBQ", "BHC"]):
                    icon = "🍗"
                elif any(chk in name for chk in ["스타벅스", "커피", "카페"]):
                    icon = "☕"
                elif any(chk in name for chk in ["주유", "GS칼텍스", "현대오일뱅크"]):
                    icon = "⛽"
                elif any(chk in name for chk in ["영화", "롯데시네마", "CGV"]):
                    icon = "🎬"
                elif "올리브영" in name:
                    icon = "💄"
                    
                purchase_type = 'bulk' if '배달의민족' in name else 'cart'
                
                coupon_list.append({
                    'name': name,
                    'price': price,
                    'value': value,
                    'guid': guid,
                    'purchase_type': purchase_type,
                    'icon': icon
                })
                
            self.log_success(f"상품 목록 수집 완료: 총 {len(coupon_list)}개 상품 발견")
            return coupon_list
            
        except Exception as e:
            self.log_error(f"상품 목록 크롤링 실패: {str(e)}")
            return []
        finally:
            if self.web_automation and self.web_automation.driver:
                driver = self.web_automation.driver
                try:
                    if main_window and driver.current_window_handle != main_window:
                        self.log_info("임시 빌마켓 탭을 닫고 메인 페이지로 돌아갑니다.")
                        driver.close()
                        driver.switch_to.window(main_window)
                except:
                    if len(driver.window_handles) > 0:
                        driver.switch_to.window(driver.window_handles[0])
            
    def _split_phone_number(self, phone):
        """휴대폰 번호를 세 부분으로 분할합니다."""
        digits = ''.join(c for c in phone if c.isdigit())
        if len(digits) == 11:
            return digits[0:3], digits[3:7], digits[7:11]
        elif len(digits) == 10:
            return digits[0:3], digits[3:6], digits[6:10]
        else:
            return "010", digits[3:7] if len(digits)>3 else "", digits[7:] if len(digits)>7 else ""

    def execute(self, quantity=1, phone_number='', coupon_item=None, sender_name=''):
        """선택한 상품 쿠폰을 지정 수량만큼 구매합니다."""
        main_window = None
        try:
            if not self.web_automation or not self.web_automation.driver:
                return self.create_result(False, "웹드라이버가 초기화되지 않았습니다. 먼저 로그인해주세요.")
            
            if not phone_number:
                return self.create_result(False, "받은 사람 번호가 없습니다.")
                
            # 기본값 설정 (배민 10,000원 쿠폰)
            if not coupon_item:
                coupon_item = {
                    'name': '배달의민족 10,000원',
                    'price': 9700,
                    'value': 10000,
                    'guid': '14152303',
                    'purchase_type': 'bulk'
                }
                
            guid = coupon_item.get('guid')
            purchase_type = coupon_item.get('purchase_type', 'bulk')
            product_name = coupon_item.get('name', '')
            
            driver = self.web_automation.driver
            main_window = driver.current_window_handle
            
            self.log_info(f"{coupon_item.get('icon', '🎁')} {product_name} {quantity}개 구매를 시작합니다...")
            self.log_info("🔄 빌마켓으로 이동 중...")
            
            if "pointUseHistoryList" not in driver.current_url:
                driver.get(POINTS_PAGE_URL)
                time.sleep(2)
            
            driver.execute_script("openPointShop();")
            self.log_info("빌마켓 버튼 클릭 완료")
            
            for i in range(10):
                if len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])
                    self.log_info("빌마켓 탭으로 전환")
                    break
                time.sleep(0.5)
            else:
                return self.create_result(False, "빌마켓 탭이 열리지 않았습니다")
                
            if purchase_type == 'bulk':
                # --- 기존 Bulk Order (배달의민족) 결제 로직 ---
                coupon_order_url = f"https://mcircle.bizmarketb2b.com/Order/MCouponBulkOrder.aspx?guid={guid}&cate=0"
                driver.get(coupon_order_url)
                for i in range(20):
                    if "MCouponBulkOrder" in driver.current_url:
                        break
                    time.sleep(0.5)
                else:
                    return self.create_result(False, f"쿠폰 페이지 로딩 실패: {driver.current_url}")
                
                self.log_success("쿠폰 주문 페이지 도착!")
                time.sleep(1)
                
                phone_lines = "\n".join([phone_number] * quantity)
                self.log_info(f"연락처 입력 중... ({phone_number} × {quantity}개)")
                
                textarea = self.find_element_safe(By.ID, "rcvMobiles")
                textarea.clear()
                textarea.send_keys(phone_lines)
                
                self.log_info("입력완료 클릭...")
                driver.execute_script("chckMobiles();")
                time.sleep(1)
                
                try:
                    cnt_element = self.find_element_safe(By.ID, "rcvMobileCnt", timeout=5)
                    cnt = cnt_element.text.strip()
                    self.log_info(f"총 발송 수량: {cnt}건")
                except:
                    pass
                
                self.log_info("다음 버튼 클릭...")
                driver.execute_script("document.getElementById('btnPayment').click();")
                
                try:
                    WebDriverWait(driver, 5).until(EC.alert_is_present())
                    alert = driver.switch_to.alert
                    self.log_info(f"알림창 확인: {alert.text}")
                    alert.accept()
                    time.sleep(2)
                except:
                    pass
                
                self.log_success("결제 페이지 도착!")
                time.sleep(1)
                
                try:
                    price_element = self.find_element_safe(By.CSS_SELECTOR, "#total_goods_price span")
                    price_text = price_element.text.strip().replace(',', '')
                    self.log_info(f"상품금액: {price_text}원")
                    
                    point_input = self.find_element_safe(By.ID, "point_etc1")
                    point_input.clear()
                    point_input.send_keys(price_text)
                    self.log_success(f"엠서클 포인트 {price_text}원 입력 완료")
                except Exception as e:
                    return self.create_result(False, f"포인트 입력 실패: {str(e)}")
                
                self.log_info("포인트 적용 클릭...")
                driver.execute_script("document.getElementById('chkMcircelPoint').click();")
                time.sleep(1.5)
                
                # SweetAlert / 커스텀 모달 확인 팝업 닫기
                try:
                    ok_buttons = driver.find_elements(By.XPATH, "//*[text()='확인']")
                    for btn in ok_buttons:
                        if btn.is_displayed():
                            btn.click()
                            self.log_success("포인트 적용 안내 팝업 확인 완료")
                            break
                except Exception as e:
                    self.log_warning(f"포인트 적용 팝업 확인 실패 (무시 가능): {e}")
                    
                time.sleep(1)
                
                try:
                    WebDriverWait(driver, 3).until(EC.alert_is_present())
                    alert = driver.switch_to.alert
                    alert_text = alert.text
                    self.log_info(f"포인트 적용 알림: {alert_text}")
                    
                    if "포인트보다 많은 금액" in alert_text or "부족" in alert_text:
                         alert.accept()
                         return self.create_result(False, f"포인트 적용 실패: {alert_text}")
                    
                    alert.accept()
                    self.log_success("포인트 적용 완료")
                except:
                    self.log_info("알림창 없음, 진행 시도")
                
                self.log_info("동의 항목 체크 중...")
                driver.execute_script("document.getElementById('agreeFlow').click();")
                time.sleep(0.3)
                driver.execute_script("document.getElementById('chkReSale').click();")
                time.sleep(0.3)
                self.log_success("개인정보 제공 동의 & 재판매 금지 동의 체크 완료")
                
                return self._complete_payment(driver, main_window, product_name, quantity)
                
            elif purchase_type == 'cart':
                # --- 신규 Cart Order (일반 상품) 바로구매 결제 로직 ---
                product_url = f"https://mcircle.bizmarketb2b.com/Goods/Content.aspx?guid={guid}&catecode=14592&eventuid=21006"
                
                driver.get(product_url)
                time.sleep(3)
                
                loop_count = 1
                qty_to_buy = quantity
                
                # 수량 조절 (1보다 크면 조절 시도)
                if quantity > 1:
                    try:
                        ea_input = self.find_element_safe(By.CSS_SELECTOR, "input[id^='ea_']", timeout=5)
                        if ea_input:
                            ea_id = ea_input.get_attribute("id") or ""
                            ea_suffix = ea_id.split("ea_")[1] if "ea_" in ea_id else "1"
                            
                            ea_input.clear()
                            ea_input.send_keys(str(quantity))
                            driver.execute_script(f"FneaMoneyTxt('{ea_suffix}');")
                            self.log_info(f"수량을 {quantity}개(ID: {ea_id})로 변경 완료")
                            time.sleep(1)
                    except Exception as eq:
                        err_msg = str(eq).lower()
                        if "invalid element state" in err_msg or "readonly" in err_msg:
                            self.log_warning("ℹ 이 상품은 빌마켓 정책상 수량 변경이 불가능한 1개 고정 상품입니다. 1개씩 여러 번 결제합니다.")
                        else:
                            self.log_warning(f"상세페이지 수량 변경 실패, 1개씩 여러 번 결제합니다: {eq}")
                        loop_count = quantity
                        qty_to_buy = 1
                
                final_res = None
                for step in range(loop_count):
                    is_last = (step == loop_count - 1)
                    if loop_count > 1:
                        self.log_info(f"🔄 다중 반복 구매 진행 중: ({step+1}/{loop_count})")
                        if step > 0:
                            driver.get(product_url)
                            time.sleep(3)
                
                    self.log_info("바로구매 버튼 실행...")
                    driver.execute_script("GoodsContent.CartInsert('D')")
                    time.sleep(4)
                    
                    if "Order/Order.aspx" not in driver.current_url:
                        return self.create_result(False, f"결제 페이지 로딩 실패: {driver.current_url}")
                        
                    self.log_success("결제 페이지 도착!")
                    
                    # 보내는 사람 설정
                    if not sender_name:
                        sender_name = os.environ.get('ACCOUNT_NAME', '')
                    if sender_name:
                        self.log_info(f"보내는 사람 입력 중: {sender_name}")
                        ord_name_input = self.find_element_safe(By.ID, "ordName")
                        ord_name_input.clear()
                        ord_name_input.send_keys(sender_name)
                    
                    # 받는 사람 이름 설정
                    receiver_name = sender_name or "수신인"
                    self.log_info(f"받는 사람 이름 입력 중: {receiver_name}")
                    rcv_name_input = self.find_element_safe(By.ID, "rcvName")
                    rcv_name_input.clear()
                    rcv_name_input.send_keys(receiver_name)
                    
                    # 받는 사람 번호 설정
                    p1, p2, p3 = self._split_phone_number(phone_number)
                    self.log_info(f"받는 사람 번호 입력 중: {p1}-{p2}-{p3}")
                    driver.find_element(By.ID, "rcvMobile1").clear()
                    driver.find_element(By.ID, "rcvMobile1").send_keys(p1)
                    driver.find_element(By.ID, "rcvMobile2").clear()
                    driver.find_element(By.ID, "rcvMobile2").send_keys(p2)
                    driver.find_element(By.ID, "rcvMobile3").clear()
                    driver.find_element(By.ID, "rcvMobile3").send_keys(p3)
                    
                    # MMS 내용 설정
                    try:
                        memo_input = self.find_element_safe(By.ID, "orderMemo", timeout=3)
                        if memo_input:
                            memo_input.clear()
                            memo_input.send_keys(".")
                            self.log_success("MMS 내용에 '.' 입력 완료")
                    except Exception as em:
                        self.log_warning(f"MMS 내용 입력 실패 (무시 가능): {em}")
                    
                    # 결제할 포인트 가져오기
                    try:
                        price_text = ""
                        # 1. 결제 페이지의 실제 상품 금액 또는 결제 예정 금액 엘리먼트에서 값을 우선 가져옴
                        try:
                            price_element = self.find_element_safe(By.CSS_SELECTOR, "#total_pay_price span", timeout=3)
                            if not price_element:
                                price_element = self.find_element_safe(By.CSS_SELECTOR, "#total_goods_price span", timeout=3)
                            
                            if price_element:
                                val = price_element.text.strip().replace(',', '')
                                val_clean = "".join(c for c in val if c.isdigit())
                                if val_clean and int(val_clean) > 0:
                                    price_text = val_clean
                                    self.log_info(f"결제 페이지 실제 결제금액 감지: {price_text}원")
                        except Exception as ep_chk:
                            self.log_warning(f"결제 페이지 금액 크롤링 실패 (Fallback 계산법 사용): {ep_chk}")
     
                        # 2. 크롤링 실패 시 fallback 계산 적용
                        if not price_text:
                            price = coupon_item.get('price', 0)
                            total_cost = price * qty_to_buy
                            price_text = str(total_cost)
                            self.log_info(f"계산된 결제 금액(Fallback): {price_text}원")
                        else:
                            # 크롤링 성공 시 수량 역산 동기화
                            single_price = coupon_item.get('price', 0)
                            if single_price > 0:
                                actual_qty = int(price_text) // single_price
                                if actual_qty > 0 and actual_qty != qty_to_buy:
                                    self.log_info(f"실제 결제 수량 동기화: {qty_to_buy}개 -> {actual_qty}개")
                                    qty_to_buy = actual_qty
                        
                        point_input = self.find_element_safe(By.ID, "point_etc1", timeout=10)
                        if not point_input:
                            return self.create_result(False, "포인트 입력창(point_etc1)을 찾을 수 없습니다. 페이지 로딩 지연이거나 필드가 누락되었습니다.")
                            
                        driver.execute_script("arguments[0].scrollIntoView(true);", point_input)
                        time.sleep(0.5)
                        
                        try:
                            point_input.clear()
                            point_input.send_keys(price_text)
                        except Exception as pe:
                            self.log_warning(f"일반 텍스트 입력 실패로 JS 강제 주입 시도: {pe}")
                            driver.execute_script(f"arguments[0].value = '{price_text}';", point_input)
                            
                        self.log_success(f"엠서클 포인트 {price_text}원 입력 완료")
                    except Exception as e:
                        return self.create_result(False, f"포인트 입력 실패: {str(e)}")
                        
                    self.log_info("포인트 적용 클릭...")
                    driver.execute_script("document.getElementById('chkMcircelPoint').click();")
                    time.sleep(1.5)
                    
                    # SweetAlert2 혹은 HTML 얼럿 닫기
                    try:
                        ok_buttons = driver.find_elements(By.XPATH, "//*[text()='확인']")
                        for btn in ok_buttons:
                            if btn.is_displayed():
                                btn.click()
                                self.log_success("포인트 적용 안내 팝업 확인 완료")
                                break
                    except Exception as e:
                        self.log_warning(f"포인트 적용 팝업 닫기 실패 (무시 가능): {e}")
                        
                    time.sleep(1)
                    
                    self.log_info("동의 항목 체크 중...")
                    driver.execute_script("document.getElementById('agreeFlow').click();")
                    time.sleep(0.3)
                    driver.execute_script("document.getElementById('chkReSale').click();")
                    time.sleep(0.3)
                    self.log_success("개인정보 제공 동의 & 재판매 금지 동의 체크 완료")
                    
                    final_res = self._complete_payment(driver, main_window, product_name, quantity if is_last else qty_to_buy, is_last=is_last)
                    if not final_res.get('success', False):
                        return final_res
                
                return final_res
                
        except Exception as e:
            error_msg = f"쿠폰 구매 중 오류: {str(e)}"
            self.log_error(error_msg)
            return self.create_result(False, error_msg)
        finally:
            pass

    def _is_auto_payment_enabled(self):
        """포인트 자동 결제 설정 여부 확인"""
        try:
            from pathlib import Path
            import json
            base_dir = Path(__file__).parent.parent
            settings_path = base_dir / "data" / "settings.json"
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('auto_point_payment', False)
        except Exception as e:
            self.logger.error(f"설정 파일 읽기 오류: {e}")
        return False

    def _complete_payment(self, driver, main_window, product_name, quantity, is_last=True):
        """결제 자동 클릭 혹은 수동 대기 후 탭 닫기 및 포인트 체크"""
        auto_pay = self._is_auto_payment_enabled()
        
        if auto_pay:
            self.log_info("포인트 자동 결제를 진행합니다...")
            try:
                payment_btn = None
                # 결제하기 버튼 탐색 (ID 우선)
                for selector in ["btnPayment", "btnPay", "payment_btn"]:
                    try:
                        payment_btn = driver.find_element(By.ID, selector)
                        if payment_btn and payment_btn.is_displayed():
                            break
                    except:
                        pass
                
                if not payment_btn:
                    try:
                        payment_btn = driver.find_element(By.XPATH, "//*[text()='결제하기']")
                    except:
                        pass
                
                if payment_btn:
                    driver.execute_script("arguments[0].scrollIntoView(true);", payment_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", payment_btn)
                    self.log_info("결제하기 버튼 클릭 완료")
                else:
                    return self.create_result(False, "결제하기 버튼을 찾을 수 없어 결제를 완료하지 못했습니다.")
                
                # 안내 얼럿 수락 시도
                try:
                    WebDriverWait(driver, 3).until(EC.alert_is_present())
                    alert = driver.switch_to.alert
                    self.log_info(f"결제 안내 알림창 감지: {alert.text}")
                    alert.accept()
                except:
                    pass
            except Exception as ep:
                return self.create_result(False, f"자동 결제 처리 중 오류 발생: {str(ep)}")
        else:
            self.log_info("👉 브라우저 결제창에서 [결제하기] 버튼을 직접 눌러 결제를 완료해 주세요.")
            self.log_info("👉 주문이 완료되면 이 창은 자동으로 닫히고 포인트 정보가 갱신됩니다.")
        
        # 주문 완료 감지 루프 (최대 180초 대기)
        start_time = time.time()
        timeout = 180
        success_detected = False
        
        while time.time() - start_time < timeout:
            try:
                current_url = driver.current_url
                if "OrderFinish" in current_url or "OrderEnd" in current_url or "Finish" in current_url:
                    success_detected = True
                    break
                
                # 주문완료 관련 텍스트가 바디에 렌더링되었는지 확인
                body_text = driver.find_element(By.TAG_NAME, "body").text
                if "주문이 완료되었습니다" in body_text or "구매가 완료되었습니다" in body_text:
                    success_detected = True
                    break
            except Exception as e:
                # 탭이 닫히거나 스레드 종료 시 예외 발생 대처
                pass
            time.sleep(0.5)
        
        if success_detected:
            if is_last:
                # 탭 닫고 메인 윈도우 전환
                try:
                    driver.close()
                    driver.switch_to.window(main_window)
                    self.log_success(f"{product_name} 결제 완료 및 창 자동 닫기 처리")
                except Exception as ew:
                    self.log_warning(f"창 닫기 혹은 메인 화면 전환 오류 (무시 가능): {ew}")
            else:
                self.log_success(f"{product_name} 단건 결제 성공 (다음 구매를 진행합니다.)")
                
            return self.create_result(True, f"{product_name} {quantity}개 구매가 완료되었습니다.")
        else:
            return self.create_result(False, "포인트 결제 확인 대기 시간 초과 또는 결제 실패")
