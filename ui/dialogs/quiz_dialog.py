# -*- coding: utf-8 -*-
"""
일반 퀴즈 문제 관리 팝업 대화상자
설문 문제 관리와 동일한 디자인과 기능을 제공합니다.
"""
import tkinter as tk
from modules.quiz_problem import QuizProblemManager

def open_quiz_manager(parent_window, gui_logger=None, initial_question=None, initial_category="일반"):
    """
    일일 퀴즈 문제 관리 팝업 창을 엽니다.
    """
    from tkinter import ttk, messagebox
    import os
    
    problem_manager = QuizProblemManager()
    
    # 팝업 창 생성
    popup = tk.Toplevel(parent_window)
    popup.title("🧠 일일 퀴즈 문제 관리")
    popup.geometry("900x650")
    popup.minsize(850, 600)
    popup.grab_set()
    
    # 제목
    tk.Label(
        popup,
        text="🧠 일일 퀴즈 정답 데이터 관리",
        font=("맑은 고딕", 14, "bold"),
        bg='#f0f0f0',
        fg='#2c3e50'
    ).pack(pady=(10, 5), padx=10)
    
    # 설명
    tk.Label(
        popup,
        text="매일 열리는 오늘의 퀴즈 문제와 정답을 관리합니다.",
        font=("맑은 고딕", 10),
        bg='#f0f0f0',
        fg='#7f8c8d'
    ).pack(padx=10)
    
    # --- 입력 영역 ---
    input_frame = tk.Frame(popup, bg='#ffffff', relief='solid', borderwidth=1)
    input_frame.pack(fill='x', padx=10, pady=10)
    
    tk.Label(input_frame, text="문제:", font=("맑은 고딕", 10), bg='#ffffff').pack(anchor='w', padx=10, pady=(10, 2))
    question_entry = tk.Text(input_frame, height=3, font=("맑은 고딕", 10), wrap='word')
    question_entry.pack(padx=10, pady=(0, 10), fill='x', expand=True)
    
    tk.Label(input_frame, text="정답 (1, 2, 3, O, X 등):", font=("맑은 고딕", 10), bg='#ffffff').pack(anchor='w', padx=10, pady=(0, 2))
    answer_entry = tk.Entry(input_frame, font=("맑은 고딕", 10), width=40)
    answer_entry.pack(anchor='w', padx=10, pady=(0, 10))
    
    tk.Label(input_frame, text="카테고리/상품명:", font=("맑은 고딕", 10), bg='#ffffff').pack(anchor='w', padx=10, pady=(0, 2))
    category_entry = tk.Entry(input_frame, font=("맑은 고딕", 10), width=40)
    category_entry.pack(anchor='w', padx=10, pady=(0, 10))
    
    # 초기값 설정
    if initial_question:
        question_entry.insert("1.0", initial_question)
    if initial_category:
        category_entry.delete(0, tk.END)
        category_entry.insert(0, initial_category)
    else:
        category_entry.insert(0, "일반")
    
    # 버튼 프레임 (입력창 바로 아래)
    btn_frame = tk.Frame(input_frame, bg='#ffffff')
    btn_frame.pack(fill='x', padx=10, pady=(0, 10))
    
    edit_mode = {"active": False, "original_question": ""}
    
    def clear_inputs():
        question_entry.delete("1.0", tk.END)
        answer_entry.delete(0, tk.END)
        category_entry.delete(0, tk.END)
        category_entry.insert(0, "일반")
        edit_mode["active"] = False
        edit_mode["original_question"] = ""
        update_button_states()
    
    def refresh_categories():
        """카테고리 목록 사이드바 새로고침"""
        current_sel = cat_listbox.curselection()
        selected_cat = cat_listbox.get(current_sel[0]) if current_sel else "전체"
        
        cat_listbox.delete(0, tk.END)
        cat_listbox.insert(tk.END, "전체")
        
        cats = set()
        for data in problem_manager.get_all_quizzes().values():
            if isinstance(data, dict):
                cats.add(data.get("category", "일반"))
            else:
                cats.add("일반")
        
        for c in sorted(list(cats)):
            cat_listbox.insert(tk.END, c)
            
        # 기존 선택 유지
        for i in range(cat_listbox.size()):
            if cat_listbox.get(i) == selected_cat:
                cat_listbox.select_set(i)
                break
        else:
            cat_listbox.select_set(0)

    def refresh_list(selected_cat="전체"):
        for item in tree.get_children():
            tree.delete(item)
        
        quizzes = problem_manager.get_all_quizzes()
        for q, data in quizzes.items():
            ans = data.get("answer", "") if isinstance(data, dict) else data
            cat = data.get("category", "일반") if isinstance(data, dict) else "일반"
            ans_num = data.get("answer_num", "") if isinstance(data, dict) else ""
            
            display_answer = ans
            if ans_num and not str(ans).isdigit():
                display_answer = f"{ans_num}. {ans}"
            
            if selected_cat != "전체" and cat != selected_cat:
                continue
            
            display_q = q[:100] + "..." if len(q) > 100 else q
            tree.insert('', tk.END, values=(cat, display_q, display_answer, q))
        
        refresh_categories()

    def add_or_update():
        q = question_entry.get("1.0", tk.END).strip()
        a = answer_entry.get().strip()
        c = category_entry.get().strip()
        
        if not q or not a:
            messagebox.showwarning("경고", "문제와 정답을 모두 입력하세요.")
            return
        
        existing_ans_num = ""
        if edit_mode["active"]:
            old_q = edit_mode["original_question"]
            old_details = problem_manager.get_question_details(old_q)
            if old_details:
                existing_ans_num = old_details.get("answer_num", "")
        
        # 정답 입력 파싱 (예: "1. 낮은 저혈당" -> ans_num="1", parsed_a="낮은 저혈당")
        import re
        match = re.match(r'^(\d+)\.\s*(.*)$', a)
        if match:
            ans_num = match.group(1)
            parsed_a = match.group(2).strip()
            if not parsed_a:
                parsed_a = ans_num
        else:
            parsed_a = a
            ans_num = a if a.isdigit() else existing_ans_num
            
        if edit_mode["active"]:
            problem_manager.delete_quiz(old_q)
            
        if problem_manager.add_quiz(q, parsed_a, c, answer_num=ans_num):
            if not initial_question:
                messagebox.showinfo("성공", "저장되었습니다.")
            if gui_logger:
                gui_logger(f"🧠 일일 퀴즈 저장: {q[:20]}... → {a}")
            
            if initial_question:
                popup.destroy()
                return
                
            clear_inputs()
            refresh_list()
        else:
            messagebox.showerror("오류", "저장에 실패했습니다.")

    def delete_selected():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("경고", "삭제할 항목을 선택하세요.")
            return
        
        orig_q = tree.item(sel[0])['values'][3]
        if messagebox.askyesno("확인", "정말로 삭제하시겠습니까?"):
            if problem_manager.delete_quiz(orig_q):
                refresh_list()
                clear_inputs()

    def update_button_states():
        if edit_mode["active"]:
            add_btn.config(text="📝 수정", bg='#3498db')
            cancel_btn.pack(side='left', padx=5)
        else:
            add_btn.config(text="➕ 추가", bg='#e67e22') # 주황색 테마 유지
            cancel_btn.pack_forget()

    add_btn = tk.Button(btn_frame, text="➕ 추가", bg='#e67e22', fg='white', font=("맑은 고딕", 10, "bold"), command=add_or_update, padx=25)
    add_btn.pack(side='left', padx=(0, 5))
    
    del_btn = tk.Button(btn_frame, text="🗑️ 삭제", bg='#e74c3c', fg='white', font=("맑은 고딕", 10, "bold"), command=delete_selected, padx=25)
    del_btn.pack(side='left', padx=5)
    
    cancel_btn = tk.Button(btn_frame, text="✖️ 취소", bg='#95a5a6', fg='white', font=("맑은 고딕", 10, "bold"), command=clear_inputs, padx=25)
    cancel_btn.pack(side='left', padx=5)
    cancel_btn.pack_forget()

    # --- 리스트 영역 (사이드바 포함) ---
    content_frame = tk.Frame(popup, bg='#f0f0f0')
    content_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
    
    # 사이드바
    sidebar = tk.Frame(content_frame, width=150, bg='#ffffff', relief='solid', borderwidth=1)
    sidebar.pack(side='left', fill='y', padx=(0, 5))
    sidebar.pack_propagate(False)
    
    tk.Label(sidebar, text="📁 카테고리", font=("맑은 고딕", 10, "bold"), bg='#ffffff').pack(pady=(10, 5))
    cat_listbox = tk.Listbox(sidebar, font=("맑은 고딕", 10), bd=0, highlightthickness=0, bg='#ffffff', selectmode='single')
    cat_listbox.pack(fill='both', expand=True, padx=5, pady=5)
    
    # 트리뷰 부모
    list_panel = tk.Frame(content_frame, bg='#ffffff', relief='solid', borderwidth=1)
    list_panel.pack(side='left', fill='both', expand=True)
    
    tk.Label(list_panel, text="📋 등록된 문제 목록 (수정하려면 선택)", font=("맑은 고딕", 11, "bold"), bg='#ffffff', fg='#2c3e50').pack(anchor='w', padx=10, pady=(10, 5))
    
    tree_parent = tk.Frame(list_panel, bg='#ffffff')
    tree_parent.pack(fill='both', expand=True, padx=10, pady=(0, 10))
    
    vsb = ttk.Scrollbar(tree_parent)
    vsb.pack(side='right', fill='y')
    
    tree = ttk.Treeview(tree_parent, columns=('cat', 'q', 'a', 'orig'), displaycolumns=('cat', 'q', 'a'), height=12, yscrollcommand=vsb.set)
    vsb.config(command=tree.yview)
    
    tree.column('#0', width=0, stretch=tk.NO)
    tree.column('cat', anchor='center', width=120)
    tree.column('q', anchor='w', width=450)
    tree.column('a', anchor='center', width=80)
    
    tree.heading('cat', text='상품/카테고리', anchor='center')
    tree.heading('q', text='문제 내용 (드래그하여 순서 변경)', anchor='w')
    tree.heading('a', text='정답', anchor='center')
    tree.pack(fill='both', expand=True)

    # --- 이벤트 바인딩 ---
    def on_tree_click(event):
        sel = tree.selection()
        if not sel: return
        item = tree.item(sel[0])
        orig = item['values'][3]
        data = problem_manager.get_all_quizzes().get(orig)
        if data:
            question_entry.delete("1.0", tk.END)
            question_entry.insert("1.0", orig)
            answer_entry.delete(0, tk.END)
            category_entry.delete(0, tk.END)
            if isinstance(data, dict):
                ans = data.get("answer", "")
                ans_num = data.get("answer_num", "")
                display_answer = ans
                if ans_num and not str(ans).isdigit():
                    display_answer = f"{ans_num}. {ans}"
                answer_entry.insert(0, display_answer)
                category_entry.insert(0, data.get("category", "일반"))
            else:
                answer_entry.insert(0, data)
                category_entry.insert(0, "일반")
            edit_mode["active"] = True
            edit_mode["original_question"] = orig
            update_button_states()

    def on_cat_click(event):
        sel = cat_listbox.curselection()
        if sel:
            refresh_list(cat_listbox.get(sel[0]))

    # 순서 변경 (드래그 앤 드롭)
    def save_order():
        if cat_listbox.get(cat_listbox.curselection()[0]) != "전체": return
        new_db = {}
        all_q = problem_manager.get_all_quizzes()
        for item in tree.get_children():
            orig = tree.item(item)['values'][3]
            if orig in all_q:
                new_db[orig] = all_q[orig]
        problem_manager.quiz_answers = new_db
        problem_manager.save_quizzes()
        if gui_logger: gui_logger("↔️ 퀴즈 순서가 저장되었습니다.")

    def on_drag_start(event):
        item = tree.identify_row(event.y)
        if item: tree.drag_item = item

    def on_drag_stop(event):
        target = tree.identify_row(event.y)
        source = getattr(tree, 'drag_item', None)
        if source and target and source != target:
            idx = tree.index(target)
            tree.move(source, '', idx)
            save_order()
        tree.drag_item = None

    tree.bind('<<TreeviewSelect>>', on_tree_click)
    cat_listbox.bind('<<ListboxSelect>>', on_cat_click)
    tree.bind("<Button-1>", on_drag_start, add="+")
    tree.bind("<ButtonRelease-1>", on_drag_stop, add="+")
    
    # 하단 닫기
    tk.Button(popup, text="닫기", bg='#3498db', fg='white', font=("맑은 고딕", 10, "bold"), command=popup.destroy, padx=40).pack(pady=10)
    
    refresh_list()
