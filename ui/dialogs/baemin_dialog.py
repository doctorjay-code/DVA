# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox
from modules.baemin_module import COUPON_PRICE, COUPON_VALUE

def show_baemin_purchase_dialog(parent, current_points, max_coupons, phone_number, on_confirm_callback, on_cancel_callback):
    """
    배달의민족 쿠폰 구매 수량 입력 다이얼로그를 생성하고 표시합니다.
    
    Args:
        parent: 부모 윈도우 (root 등)
        current_points (int): 현재 보유 포인트
        max_coupons (int): 최대 구매 가능 수량
        phone_number (str): 기본 입력될 휴대폰 번호
        on_confirm_callback (callable): 구매 확인 시 실행할 콜백 (인자: quantity, phone_number)
        on_cancel_callback (callable): 구매 취소 시 실행할 콜백
    """
    dialog = tk.Toplevel(parent)
    dialog.title("🛵 배달의민족 쿠폰 구매")
    dialog.geometry("400x380")
    dialog.resizable(False, False)
    dialog.configure(bg='#f8f9fa')
    dialog.transient(parent)
    dialog.grab_set()
    
    # 중앙 정렬
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
    y = parent.winfo_y() + (parent.winfo_height() // 2) - 190
    dialog.geometry(f"400x380+{x}+{y}")
    
    # 제목
    tk.Label(
        dialog, text="🛵 배달의민족 쿠폰 구매",
        font=("맑은 고딕", 16, "bold"), bg='#f8f9fa', fg='#2c3e50'
    ).pack(pady=(20, 15))
    
    # 정보 프레임
    info_frame = tk.Frame(dialog, bg='#ffffff', relief='solid', borderwidth=1)
    info_frame.pack(fill='x', padx=30, pady=(0, 15))
    
    tk.Label(
        info_frame, text=f"현재 포인트:  {current_points:,}P",
        font=("맑은 고딕", 12), bg='#ffffff', fg='#2c3e50', anchor='w'
    ).pack(fill='x', padx=15, pady=(12, 4))
    
    tk.Label(
        info_frame, text=f"쿠폰 가격:  {COUPON_PRICE:,}P (={COUPON_VALUE:,}원 쿠폰)",
        font=("맑은 고딕", 11), bg='#ffffff', fg='#7f8c8d', anchor='w'
    ).pack(fill='x', padx=15, pady=(0, 4))
    
    max_color = '#27ae60' if max_coupons > 0 else '#e74c3c'
    tk.Label(
        info_frame, text=f"최대 구매 가능:  {max_coupons}개",
        font=("맑은 고딕", 12, "bold"), bg='#ffffff', fg=max_color, anchor='w'
    ).pack(fill='x', padx=15, pady=(0, 12))
    
    # 받는 사람 번호
    phone_frame = tk.Frame(dialog, bg='#f8f9fa')
    phone_frame.pack(pady=(0, 10))
    
    tk.Label(
        phone_frame, text="받는 사람:",
        font=("맑은 고딕", 12), bg='#f8f9fa', fg='#2c3e50'
    ).pack(side='left', padx=(0, 10))
    
    phone_var = tk.StringVar(value=phone_number)
    phone_entry = tk.Entry(
        phone_frame, textvariable=phone_var, width=15,
        font=("맑은 고딕", 14, "bold"),
        justify='center'
    )
    phone_entry.pack(side='left')
    
    # 구매 수량
    qty_frame = tk.Frame(dialog, bg='#f8f9fa')
    qty_frame.pack(pady=(0, 15))
    
    tk.Label(
        qty_frame, text="구매 수량:",
        font=("맑은 고딕", 12), bg='#f8f9fa', fg='#2c3e50'
    ).pack(side='left', padx=(0, 10))
    
    qty_var = tk.IntVar(value=1)
    
    qty_spinbox = tk.Spinbox(
        qty_frame, from_=1, to=max(99, max_coupons),
        textvariable=qty_var, width=5,
        font=("맑은 고딕", 14, "bold"),
        justify='center'
    )
    qty_spinbox.pack(side='left')
    
    if max_coupons > 0:
        tk.Label(
            qty_frame, text=f"개  (1~{max_coupons})",
            font=("맑은 고딕", 11), bg='#f8f9fa', fg='#7f8c8d'
        ).pack(side='left', padx=(5, 0))
    else:
        tk.Label(
            qty_frame, text="개 (포인트 부족하지만 진행 가능)",
            font=("맑은 고딕", 11), bg='#f8f9fa', fg='#e74c3c'
        ).pack(side='left', padx=(5, 0))
    
    # 버튼 내부 로직
    def on_confirm():
        quantity = qty_var.get()
        entered_phone = phone_var.get().strip()
        
        if not entered_phone:
            messagebox.showerror("오류", "받는 사람 번호를 입력해주세요.")
            return
            
        if quantity < 1:
            messagebox.showerror("오류", "수량은 1개 이상이어야 합니다.")
            return
            
        if max_coupons > 0 and quantity > max_coupons:
            if not messagebox.askyesno("확인", f"보유 포인트로 구매 가능한 수량({max_coupons}개)보다 많습니다.\n계속 진행하시겠습니까?"):
                return
            
        total_cost = quantity * COUPON_PRICE
        dialog.destroy()
        on_confirm_callback(quantity, entered_phone, total_cost)

    def on_cancel():
        dialog.destroy()
        on_cancel_callback()
    
    # 버튼 프레임
    btn_frame = tk.Frame(dialog, bg='#f8f9fa')
    btn_frame.pack(pady=(0, 20))
    
    confirm_btn = tk.Button(
        btn_frame, text="✅ 구매하기", font=("맑은 고딕", 12, "bold"),
        bg='#27ae60', fg='white', activebackground='#1e8449',
        width=12, relief='flat', cursor='hand2',
        command=on_confirm
    )
    confirm_btn.pack(side='left', padx=10)
    
    cancel_btn = tk.Button(
        btn_frame, text="❌ 취소", font=("맑은 고딕", 12),
        bg='#e74c3c', fg='white', activebackground='#c0392b',
        width=12, relief='flat', cursor='hand2',
        command=on_cancel
    )
    cancel_btn.pack(side='left', padx=10)
    
    # ESC로 닫기
    dialog.bind('<Escape>', lambda e: on_cancel())
    
    return dialog
