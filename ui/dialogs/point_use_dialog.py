# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg='#ffffff')
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#ffffff')

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind('<Configure>', lambda event: self.canvas.itemconfig(self.canvas_window, width=event.width))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind("<Enter>", lambda _: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas.bind("<Leave>", lambda _: self.canvas.unbind_all("<MouseWheel>"))
        
    def _on_mousewheel(self, event):
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

def show_point_use_loading_dialog(parent):
    """상품 목록을 불러오는 동안 표시할 로딩 창"""
    dialog = tk.Toplevel(parent)
    dialog.title("💳 포인트 사용")
    dialog.geometry("320x150")
    dialog.resizable(False, False)
    dialog.configure(bg='#ffffff')
    dialog.transient(parent)
    dialog.grab_set()
    
    # 중앙 정렬
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - 160
    y = parent.winfo_y() + (parent.winfo_height() // 2) - 75
    dialog.geometry(f"320x150+{x}+{y}")
    
    label = tk.Label(
        dialog, text="🔄 빌마켓 상품 목록을\n불러오는 중입니다...",
        font=("맑은 고딕", 12, "bold"), bg='#ffffff', fg='#2c3e50'
    )
    label.pack(expand=True, pady=20)
    
    # 프로그레스바
    progress = ttk.Progressbar(dialog, mode='indeterminate', length=200)
    progress.pack(pady=(0, 20))
    progress.start(10)
    
    dialog.update()
    return dialog

def show_coupon_select_dialog(parent, current_points, coupon_list, favorites_list, on_select_callback, on_cancel_callback, on_toggle_favorite_callback, on_refresh_callback):
    """
    1단계: 상품 선택 다이얼로그
    """
    dialog = tk.Toplevel(parent)
    dialog.title("💳 포인트 사용 - 상품 선택")
    dialog.geometry("520x680") # 체크박스 공간 확보를 위해 높이 약간 조정
    dialog.resizable(False, False)
    dialog.configure(bg='#f8f9fa')
    dialog.transient(parent)
    dialog.grab_set()
    
    # 중앙 정렬
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - 260
    y = parent.winfo_y() + (parent.winfo_height() // 2) - 340
    dialog.geometry(f"520x680+{x}+{y}")
    
    # 제목
    tk.Label(
        dialog, text="💳 포인트 사용 - 상품 선택",
        font=("맑은 고딕", 16, "bold"), bg='#f8f9fa', fg='#2c3e50'
    ).pack(pady=(15, 10))
    
    # 포인트 정보 프레임
    info_frame = tk.Frame(dialog, bg='#ffffff', relief='solid', borderwidth=1)
    info_frame.pack(fill='x', padx=20, pady=(0, 10))
    
    tk.Label(
        info_frame, text=f"보유 포인트:  {current_points:,} P",
        font=("맑은 고딕", 12, "bold"), bg='#ffffff', fg='#27ae60', anchor='w'
    ).pack(fill='x', padx=15, pady=8)
    
    # 검색 및 새로고침 프레임
    search_frame = tk.Frame(dialog, bg='#f8f9fa')
    search_frame.pack(fill='x', padx=20, pady=(0, 5))
    
    tk.Label(
        search_frame, text="🔍 검색: ",
        font=("맑은 고딕", 11, "bold"), bg='#f8f9fa', fg='#2c3e50'
    ).pack(side='left', padx=(5, 5))
    
    search_var = tk.StringVar()
    search_entry = tk.Entry(
        search_frame, textvariable=search_var, font=("맑은 고딕", 11),
        relief='solid', borderwidth=1
    )
    search_entry.pack(side='left', fill='x', expand=True)
    search_entry.focus()
    
    def on_refresh():
        dialog.destroy()
        on_refresh_callback()
        
    refresh_btn = tk.Button(
        search_frame, text="🔄 새로고침", font=("맑은 고딕", 9, "bold"),
        bg='#e67e22', fg='white', activebackground='#d35400',
        relief='flat', cursor='hand2', padx=8, pady=2,
        command=on_refresh
    )
    refresh_btn.pack(side='right', padx=(10, 5))
    
    # 필터 프레임 (즐겨찾기만 보기)
    filter_frame = tk.Frame(dialog, bg='#f8f9fa')
    filter_frame.pack(fill='x', padx=20, pady=(0, 10))
    
    fav_only_var = tk.BooleanVar(value=False)
    fav_only_cb = tk.Checkbutton(
        filter_frame, text="⭐ 즐겨찾기만 보기", variable=fav_only_var,
        font=("맑은 고딕", 10), bg='#f8f9fa', activebackground='#f8f9fa',
        command=lambda: build_list(search_var.get())
    )
    fav_only_cb.pack(side='left', padx=(5, 0))
    
    # 상품 목록 컨테이너
    list_container = tk.Frame(dialog, bg='#ffffff', relief='solid', borderwidth=1)
    list_container.pack(fill='both', expand=True, padx=20, pady=(0, 15))
    
    scroll_frame = ScrollableFrame(list_container, bg='#ffffff')
    scroll_frame.pack(fill='both', expand=True)
    
    # 선택된 상품 변수 (guid 저장)
    selected_guid_var = tk.StringVar()
    row_widgets = []
    
    # 즐겨찾기 상태 셋 관리
    favorites_set = set(favorites_list)
    
    def on_row_click(guid):
        selected_guid_var.set(guid)
        update_rows_ui()
        
    def update_rows_ui():
        sel_guid = selected_guid_var.get()
        for guid, r_frame, radio, name_lbl, price_lbl, fav_lbl in row_widgets:
            if guid == sel_guid:
                r_frame.config(bg='#e8f8f5')
                name_lbl.config(bg='#e8f8f5')
                price_lbl.config(bg='#e8f8f5')
                radio.config(bg='#e8f8f5')
                fav_lbl.config(bg='#e8f8f5')
            else:
                r_frame.config(bg='#ffffff')
                name_lbl.config(bg='#ffffff')
                price_lbl.config(bg='#ffffff')
                radio.config(bg='#ffffff')
                fav_lbl.config(bg='#ffffff')
                
    # 1. "검색 결과가 없습니다" 라벨 미리 생성
    no_result_lbl = tk.Label(
        scroll_frame.scrollable_frame, text="검색 결과가 없습니다.",
        font=("맑은 고딕", 11), bg='#ffffff', fg='#7f8c8d'
    )
    
    # 2. 모든 행 위젯들 미리 생성 (성능 최적화의 핵심)
    all_row_widgets = []
    
    def toggle_fav(guid):
        if guid in favorites_set:
            favorites_set.remove(guid)
        else:
            favorites_set.add(guid)
            
        # UI 별표 라벨 상태 즉시 갱신
        for rw in all_row_widgets:
            if rw['guid'] == guid:
                is_fav = guid in favorites_set
                fav_char = "★" if is_fav else "☆"
                fav_color = "#f1c40f" if is_fav else "#bdc3c7"
                rw['fav_lbl'].config(text=fav_char, fg=fav_color)
                break
                
        on_toggle_favorite_callback(guid)
        build_list(search_var.get())
        
    for item in coupon_list:
        guid = item['guid']
        is_fav = guid in favorites_set
        
        # 행 프레임
        r_frame = tk.Frame(scroll_frame.scrollable_frame, bg='#ffffff', cursor='hand2')
        
        # 라디오버튼
        radio = tk.Radiobutton(
            r_frame, value=guid, variable=selected_guid_var,
            bg='#ffffff', activebackground='#ffffff',
            command=lambda g=guid: on_row_click(g)
        )
        radio.pack(side='left', padx=(10, 5))
        
        # 즐겨찾기 별표 라벨
        fav_char = "★" if is_fav else "☆"
        fav_color = "#f1c40f" if is_fav else "#bdc3c7"
        fav_lbl = tk.Label(
            r_frame, text=fav_char, font=("맑은 고딕", 12, "bold"),
            bg='#ffffff', fg=fav_color, cursor='hand2'
        )
        fav_lbl.pack(side='left', padx=(5, 5))
        fav_lbl.bind("<Button-1>", lambda e, g=guid: toggle_fav(g))
        
        # 가격 정보 (우측 위젯을 먼저 pack해야 상품명이 길어져도 가격이 짤리지 않음)
        price_text = f"{item['price']:,} P"
        price_lbl = tk.Label(
            r_frame, text=price_text, font=("맑은 고딕", 11, "bold"),
            bg='#ffffff', fg='#e67e22', anchor='e'
        )
        price_lbl.pack(side='right', padx=15)
        
        # 아이콘 + 이름
        display_name = f"{item['icon']} {item['name']}"
        name_lbl = tk.Label(
            r_frame, text=display_name, font=("맑은 고딕", 11),
            bg='#ffffff', fg='#2c3e50', anchor='w'
        )
        name_lbl.pack(side='left', fill='x', expand=True, padx=5)
        
        # 클릭 이벤트 바인딩 (별표 영역 제외)
        for widget in (r_frame, name_lbl, price_lbl):
            widget.bind("<Button-1>", lambda e, g=guid: on_row_click(g))
            
        # 호버 이벤트 바인딩 (클로저 지연 바인딩 문제 방지 팩토리 함수 사용)
        def make_hover_handlers(f=r_frame, r=radio, nl=name_lbl, pl=price_lbl, fl=fav_lbl, g=guid):
            def on_enter(e):
                if selected_guid_var.get() != g:
                    f.config(bg='#f2f4f4')
                    nl.config(bg='#f2f4f4')
                    pl.config(bg='#f2f4f4')
                    r.config(bg='#f2f4f4')
                    fl.config(bg='#f2f4f4')
            def on_leave(e):
                if selected_guid_var.get() != g:
                    f.config(bg='#ffffff')
                    nl.config(bg='#ffffff')
                    pl.config(bg='#ffffff')
                    r.config(bg='#ffffff')
                    fl.config(bg='#ffffff')
            return on_enter, on_leave
            
        on_enter, on_leave = make_hover_handlers()
        r_frame.bind("<Enter>", on_enter)
        r_frame.bind("<Leave>", on_leave)
        
        all_row_widgets.append({
            'guid': guid,
            'name': item['name'],
            'r_frame': r_frame,
            'radio': radio,
            'name_lbl': name_lbl,
            'price_lbl': price_lbl,
            'fav_lbl': fav_lbl
        })
        
    def build_list(filter_text=""):
        # 검색결과 없음 라벨 숨기기
        no_result_lbl.pack_forget()
        
        # 모든 행 프레임을 일괄적으로 숨김
        for rw in all_row_widgets:
            rw['r_frame'].pack_forget()
            
        visible_widgets = []
        for rw in all_row_widgets:
            guid = rw['guid']
            is_fav = guid in favorites_set
            if fav_only_var.get() and not is_fav:
                continue
            if filter_text.lower() in rw['name'].lower():
                visible_widgets.append(rw)
                
        if not visible_widgets:
            selected_guid_var.set("")
            no_result_lbl.pack(pady=40)
            return
            
        # 즐겨찾기 상품을 최상단으로 우선 정렬 (안정 정렬)
        visible_widgets.sort(key=lambda x: x['guid'] in favorites_set, reverse=True)
        
        # 현재 선택된 항목이 필터링된 목록에 없으면 첫 번째 항목 선택
        current_sel = selected_guid_var.get()
        if not any(rw['guid'] == current_sel for rw in visible_widgets):
            selected_guid_var.set(visible_widgets[0]['guid'])
            
        # 정렬된 순서대로 다시 pack 처리하여 화면 노출
        for rw in visible_widgets:
            rw['r_frame'].pack(fill='x', ipady=5, pady=1)
            
        # update_rows_ui 가 원활하게 돌 수 있도록 row_widgets 동기화
        row_widgets.clear()
        for rw in visible_widgets:
            row_widgets.append((rw['guid'], rw['r_frame'], rw['radio'], rw['name_lbl'], rw['price_lbl'], rw['fav_lbl']))
            
        update_rows_ui()
        
        # 목록 필터링/변경 시 스크롤을 맨 위로 고정하여 상단 공백 버그 해결
        scroll_frame.canvas.yview_moveto(0.0)
        
    # 검색어 필터링 연동
    search_var.trace_add("write", lambda *args: build_list(search_var.get()))
    
    # 초기 리스트 빌드
    build_list()
    
    # 버튼 액션
    def on_next():
        sel_guid = selected_guid_var.get()
        selected_item = next((item for item in coupon_list if item['guid'] == sel_guid), None)
        if not selected_item:
            messagebox.showerror("오류", "상품을 선택해주세요.")
            return
        dialog.destroy()
        on_select_callback(selected_item)
        
    def on_cancel():
        dialog.destroy()
        on_cancel_callback()
        
    # 하단 버튼 프레임
    btn_frame = tk.Frame(dialog, bg='#f8f9fa')
    btn_frame.pack(fill='x', side='bottom', pady=20)
    
    next_btn = tk.Button(
        btn_frame, text="다음 단계 ▶", font=("맑은 고딕", 12, "bold"),
        bg='#27ae60', fg='white', activebackground='#1e8449',
        width=14, relief='flat', cursor='hand2', command=on_next
    )
    next_btn.pack(side='right', padx=(10, 30))
    
    cancel_btn = tk.Button(
        btn_frame, text="취소", font=("맑은 고딕", 12),
        bg='#95a5a6', fg='white', activebackground='#7f8c8d',
        width=10, relief='flat', cursor='hand2', command=on_cancel
    )
    cancel_btn.pack(side='right', padx=10)
    
    dialog.bind('<Escape>', lambda e: on_cancel())
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    return dialog

def show_coupon_purchase_dialog(parent, current_points, coupon_item, phone_number, sender_name, on_confirm_callback, on_cancel_callback):
    """
    2단계: 수량/수신자 입력 다이얼로그 (배민/일반 상품 분기)
    """
    guid = coupon_item['guid']
    price = coupon_item['price']
    name = coupon_item['name']
    purchase_type = coupon_item.get('purchase_type', 'cart')
    icon = coupon_item.get('icon', '🎁')
    
    max_coupons = current_points // price if price > 0 else 0
    
    dialog = tk.Toplevel(parent)
    dialog.title(f"{icon} {name} 구매")
    
    # cart 타입이면 이름 필드가 추가되므로 높이를 약간 조절
    height = 420 if purchase_type == 'cart' else 380
    dialog.geometry(f"420x{height}")
    dialog.resizable(False, False)
    dialog.configure(bg='#f8f9fa')
    dialog.transient(parent)
    dialog.grab_set()
    
    # 중앙 정렬
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - 210
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
    dialog.geometry(f"420x{height}+{x}+{y}")
    
    # 제목
    tk.Label(
        dialog, text=f"{icon} {name} 구매",
        font=("맑은 고딕", 14, "bold"), bg='#f8f9fa', fg='#2c3e50'
    ).pack(pady=(15, 10))
    
    # 정보 프레임
    info_frame = tk.Frame(dialog, bg='#ffffff', relief='solid', borderwidth=1)
    info_frame.pack(fill='x', padx=30, pady=(0, 15))
    
    tk.Label(
        info_frame, text=f"현재 포인트:  {current_points:,} P",
        font=("맑은 고딕", 11), bg='#ffffff', fg='#2c3e50', anchor='w'
    ).pack(fill='x', padx=15, pady=(10, 3))
    
    tk.Label(
        info_frame, text=f"쿠폰 가격:  {price:,} P",
        font=("맑은 고딕", 11), bg='#ffffff', fg='#7f8c8d', anchor='w'
    ).pack(fill='x', padx=15, pady=(0, 3))
    
    max_color = '#27ae60' if max_coupons > 0 else '#e74c3c'
    tk.Label(
        info_frame, text=f"최대 구매 가능:  {max_coupons}개",
        font=("맑은 고딕", 11, "bold"), bg='#ffffff', fg=max_color, anchor='w'
    ).pack(fill='x', padx=15, pady=(0, 10))
    
    # 입력 폼 컨테이너
    form_frame = tk.Frame(dialog, bg='#f8f9fa')
    form_frame.pack(fill='x', padx=35)
    
    row_idx = 0
    
    # [CART 방식 분기] 보내는 사람 이름 입력란 (실제로는 rcvName/ordName에 매핑)
    name_var = None
    if purchase_type == 'cart':
        tk.Label(
            form_frame, text="받는 사람 이름:", font=("맑은 고딕", 11, "bold"),
            bg='#f8f9fa', fg='#2c3e50', anchor='e'
        ).grid(row=row_idx, column=0, sticky='w', pady=6)
        
        name_var = tk.StringVar(value=sender_name or "")
        name_entry = tk.Entry(
            form_frame, textvariable=name_var, width=15, font=("맑은 고딕", 11),
            relief='solid', borderwidth=1
        )
        name_entry.grid(row=row_idx, column=1, sticky='w', padx=(10, 0), pady=6)
        row_idx += 1
        
    # 휴대폰 번호 입력
    tk.Label(
        form_frame, text="받는 사람 번호:", font=("맑은 고딕", 11, "bold"),
        bg='#f8f9fa', fg='#2c3e50', anchor='e'
    ).grid(row=row_idx, column=0, sticky='w', pady=6)
    
    phone_var = tk.StringVar(value=phone_number)
    phone_entry = tk.Entry(
        form_frame, textvariable=phone_var, width=15, font=("맑은 고딕", 11),
        relief='solid', borderwidth=1
    )
    phone_entry.grid(row=row_idx, column=1, sticky='w', padx=(10, 0), pady=6)
    row_idx += 1
    
    # 수량 입력
    tk.Label(
        form_frame, text="구매 수량:", font=("맑은 고딕", 11, "bold"),
        bg='#f8f9fa', fg='#2c3e50', anchor='e'
    ).grid(row=row_idx, column=0, sticky='w', pady=6)
    
    qty_var = tk.IntVar(value=1)
    qty_spinbox = tk.Spinbox(
        form_frame, from_=1, to=max(99, max_coupons),
        textvariable=qty_var, width=5, font=("맑은 고딕", 11, "bold"),
        justify='center', relief='solid', borderwidth=1
    )
    qty_spinbox.grid(row=row_idx, column=1, sticky='w', padx=(10, 0), pady=6)
    
    if max_coupons > 0:
        tk.Label(
            form_frame, text=f"개 (1~{max_coupons})",
            font=("맑은 고딕", 10), bg='#f8f9fa', fg='#7f8c8d'
        ).grid(row=row_idx, column=1, sticky='w', padx=(75, 0), pady=6)
    else:
        tk.Label(
            form_frame, text="개 (포인트 부족)",
            font=("맑은 고딕", 10), bg='#f8f9fa', fg='#e74c3c'
        ).grid(row=row_idx, column=1, sticky='w', padx=(75, 0), pady=6)
        
    def on_confirm():
        quantity = qty_var.get()
        entered_phone = phone_var.get().strip()
        entered_name = name_var.get().strip() if name_var else ""
        
        if purchase_type == 'cart' and not entered_name:
            messagebox.showerror("오류", "받는 사람 이름을 입력해주세요.")
            return
            
        if not entered_phone:
            messagebox.showerror("오류", "받는 사람 번호를 입력해주세요.")
            return
            
        if quantity < 1:
            messagebox.showerror("오류", "수량은 1개 이상이어야 합니다.")
            return
            
        if max_coupons > 0 and quantity > max_coupons:
            if not messagebox.askyesno("확인", f"보유 포인트로 구매 가능한 수량({max_coupons}개)보다 많습니다.\n계속 진행하시겠습니까?"):
                return
                
        total_cost = quantity * price
        dialog.destroy()
        on_confirm_callback(quantity, entered_phone, entered_name, coupon_item)
        
    def on_cancel():
        dialog.destroy()
        on_cancel_callback()
        
    # 버튼 프레임
    btn_frame = tk.Frame(dialog, bg='#f8f9fa')
    btn_frame.pack(fill='x', side='bottom', pady=20)
    
    confirm_btn = tk.Button(
        btn_frame, text="✅ 구매하기", font=("맑은 고딕", 12, "bold"),
        bg='#27ae60', fg='white', activebackground='#1e8449',
        width=12, relief='flat', cursor='hand2', command=on_confirm
    )
    confirm_btn.pack(side='left', padx=(55, 10))
    
    cancel_btn = tk.Button(
        btn_frame, text="❌ 취소", font=("맑은 고딕", 12),
        bg='#e74c3c', fg='white', activebackground='#c0392b',
        width=12, relief='flat', cursor='hand2', command=on_cancel
    )
    cancel_btn.pack(side='left', padx=10)
    
    dialog.bind('<Escape>', lambda e: on_cancel())
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    return dialog
