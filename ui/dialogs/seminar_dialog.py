# -*- coding: utf-8 -*-
"""
세미나 정보 표시 및 관리 다이얼로그
"""
import tkinter as tk
from tkinter import ttk

def show_seminar_info_dialog(parent, initial_seminars, callbacks):
    """
    세미나 정보를 표시하는 새 창을 생성합니다.
    
    Args:
        parent: 부모 윈도우
        initial_seminars: 초기 세미나 데이터 리스트
        callbacks: 다이얼로그에서 발생하는 이벤트를 처리할 콜백 딕셔너리
            - on_apply: (list) 체크된 세미나 신청
            - on_cancel: (list) 체크된 세미나 취소
            - on_refresh: (function) 데이터 새로고침 요청
            - on_action: (detail_link, status) 더블클릭 시 동작 수행 (신청/취소/입장 등)
            - log_message: (str) 로그 출력
    """
    
    # 윈도우 설정
    window = tk.Toplevel(parent)
    window.title("📅 닥터빌 세미나 목록 정보")
    window.geometry("1200x800")
    window.configure(bg='#f0f0f0')
    
    # 제목
    title_label = tk.Label(window, text="📅 닥터빌 세미나 목록 정보", 
                          font=("맑은 고딕", 16, "bold"), 
                          bg='#f0f0f0', fg='#2c3e50')
    title_label.pack(pady=10)
    
    # 설명
    desc_label = tk.Label(window, text="더블클릭하면 해당 세미나 페이지로 이동 및 동작을 수행합니다", 
                         font=("맑은 고딕", 10), 
                         bg='#f0f0f0', fg='#7f8c8d')
    desc_label.pack(pady=5)
    
    # 버튼 프레임 생성
    button_frame = tk.Frame(window, bg='#f0f0f0')
    button_frame.pack(fill=tk.X, padx=10, pady=5)
    
    # 버튼들 생성
    btn_select_apply = tk.Button(button_frame, text="선택신청", 
                                font=("맑은 고딕", 10, "bold"),
                                bg='#6c757d', fg='white',
                                width=10, height=1)
    btn_select_apply.pack(side=tk.LEFT, padx=3)
    
    btn_select_cancel = tk.Button(button_frame, text="선택취소", 
                                 font=("맑은 고딕", 10, "bold"),
                                 bg='#6c757d', fg='white',
                                 width=10, height=1)
    btn_select_cancel.pack(side=tk.LEFT, padx=3)
    
    btn_available_select = tk.Button(button_frame, text="신청가능선택", 
                                    font=("맑은 고딕", 10, "bold"),
                                    bg='#6c757d', fg='white',
                                    width=10, height=1)
    btn_available_select.pack(side=tk.LEFT, padx=3)
    
    btn_clear_all = tk.Button(button_frame, text="체크초기화", 
                             font=("맑은 고딕", 10, "bold"),
                             bg='#6c757d', fg='white',
                             width=10, height=1)
    btn_clear_all.pack(side=tk.LEFT, padx=3)

    btn_refresh = tk.Button(button_frame, text="🔄 새로고침", 
                           font=("맑은 고딕", 10, "bold"),
                           bg='#3498db', fg='white',
                           width=12, height=1)
    btn_refresh.pack(side=tk.RIGHT, padx=3)
    
    # 프레임 생성
    main_frame = tk.Frame(window, bg='#f0f0f0')
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 트리뷰 생성
    columns = ('선택', '날짜', '요일', '시간', '강의명', '강의자', '신청인원', '신청상태')
    tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=20)
    
    # 컬럼 설정
    tree.heading('선택', text='선택')
    tree.heading('날짜', text='날짜')
    tree.heading('요일', text='요일')
    tree.heading('시간', text='시간')
    tree.heading('강의명', text='강의명')
    tree.heading('강의자', text='강의자')
    tree.heading('신청인원', text='신청인원')
    tree.heading('신청상태', text='신청상태')
    
    # 컬럼 너비 설정
    tree.column('선택', width=50, anchor='center')
    tree.column('날짜', width=80, anchor='center')
    tree.column('요일', width=80, anchor='center')
    tree.column('시간', width=100, anchor='center')
    tree.column('강의명', width=300, anchor='w')
    tree.column('강의자', width=200, anchor='w')
    tree.column('신청인원', width=100, anchor='center')
    tree.column('신청상태', width=100, anchor='center')
    
    # 스크롤바 추가
    scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def get_checked_items():
        checked = []
        for item in tree.get_children():
            values = tree.item(item, "values")
            tags = tree.item(item, "tags")
            if len(values) > 0 and values[0] == "☑" and 'date_separator' not in tags:
                seminar_info = {
                    'title': values[4],
                    'date': values[1],
                    'time': values[3],
                    'status': values[7],
                    'detail_link': tags[0] if tags else '',
                    'status_tag': None
                }
                for tag in tags:
                    if tag in ['신청가능', '신청완료', '신청마감', '입장하기', '대기중']:
                        seminar_info['status_tag'] = tag
                        break
                checked.append(seminar_info)
        return checked

    def update_data(seminars):
        for item in tree.get_children():
            tree.delete(item)
        
        current_date = None
        for s in seminars:
            if current_date != s['date']:
                current_date = s['date']
                tree.insert('', 'end', values=("", f"📅 {s['date']} {s['day']}", "", "", "", "", "", ""), tags=('date_separator',))
            
            # 상태 태그 결정
            status = s['status']
            tag = '기타'
            if '신청가능' in status: tag = '신청가능'
            elif '신청완료' in status: tag = '신청완료'
            elif '신청마감' in status: tag = '신청마감'
            elif '입장하기' in status: tag = '입장하기'
            elif '대기중' in status: tag = '대기중'
            
            tree.insert('', 'end', values=(
                "☐", s['date'], s['day'], s['time'], s['title'], s['lecturer'], s['person'], s['status']
            ), tags=(s['detail_link'], tag))

    # 버튼 명령 설정
    btn_select_apply.config(command=lambda: callbacks['on_apply'](get_checked_items()))
    btn_select_cancel.config(command=lambda: callbacks['on_cancel'](get_checked_items()))
    btn_available_select.config(command=lambda: manage_checkboxes("select_available"))
    btn_clear_all.config(command=lambda: manage_checkboxes("clear_all"))
    btn_refresh.config(command=lambda: callbacks['on_refresh']())

    def manage_checkboxes(action_type):
        for item in tree.get_children():
            values = tree.item(item, "values")
            tags = tree.item(item, "tags")
            if 'date_separator' not in tags:
                if action_type == "select_available":
                    if len(values) > 7 and '신청가능' in values[7]:
                        new_values = list(values)
                        new_values[0] = "☑"
                        tree.item(item, values=new_values)
                elif action_type == "clear_all":
                    if len(values) > 0 and values[0] == "☑":
                        new_values = list(values)
                        new_values[0] = "☐"
                        tree.item(item, values=new_values)

    def on_click(event):
        item = tree.identify_row(event.y)
        if not item: return
        column = tree.identify_column(event.x)
        if column == '#1':
            tags = tree.item(item, "tags")
            if 'date_separator' in tags: return
            values = list(tree.item(item, "values"))
            values[0] = "☑" if values[0] == "☐" else "☐"
            tree.item(item, values=values)

    def on_double_click(event):
        if tree.identify_column(event.x) == '#1': return
        selection = tree.selection()
        if not selection: return
        item = selection[0]
        tags = tree.item(item, "tags")
        if 'date_separator' in tags: return
        
        if tags and tags[0]:
            detail_link = tags[0]
            status_tag = None
            for tag in tags:
                if tag in ['신청가능', '신청완료', '신청마감', '입장하기', '대기중']:
                    status_tag = tag
                    break
            callbacks['on_action'](detail_link, status_tag)
            tree.selection_remove(item)

    tree.bind('<Button-1>', on_click)
    tree.bind('<Double-1>', on_double_click)
    
    # 태그 색상 설정
    tree.tag_configure('신청가능', background='#d5f4e6', foreground='#2e7d32')
    tree.tag_configure('신청완료', background='#fef9e7', foreground='#f39c12')
    tree.tag_configure('신청마감', background='#fadbd8', foreground='#e74c3c')
    tree.tag_configure('입장하기', background='#d6eaf8', foreground='#3498db')
    tree.tag_configure('대기중', background='#f8f9fa', foreground='#6c757d')
    tree.tag_configure('기타', background='#f4f6f6', foreground='#34495e')
    tree.tag_configure('date_separator', background='#34495e', foreground='white', font=("맑은 고딕", 10, "bold"))

    # 초기 데이터 삽입
    update_data(initial_seminars)
    
    # 중앙 배치 및 표시
    window.update_idletasks()
    x = (window.winfo_screenwidth() // 2) - (window.winfo_width() // 2)
    y = (window.winfo_screenheight() // 2) - (window.winfo_height() // 2)
    window.geometry(f"+{x}+{y}")
    
    # window 객체에 update_data 메서드를 추가하여 외부에서 갱신 가능하게 함
    window.refresh_data = update_data
    
    return window
