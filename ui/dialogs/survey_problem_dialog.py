# -*- coding: utf-8 -*-
"""
세미나 문제 관리 팝업 대화상자 (GUI)
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
from modules.survey_problem import SurveyProblemManager

def open_survey_problem_manager(parent_window, gui_logger=None, initial_question=None, initial_category=None):
    """
    세미나 문제 관리 팝업 창을 엽니다.
    
    Args:
        parent_window: 부모 창 (tkinter.Tk)
        gui_logger: 로깅 함수
        initial_question: 초기 문제 텍스트 (있을 경우)
        initial_category: 초기 카테고리 (있을 경우)
    """
    problem_manager = SurveyProblemManager()
    
    # 팝업 창 생성
    popup = tk.Toplevel(parent_window)
    popup.title("📝 세미나 문제 관리")
    popup.geometry("900x600")
    popup.minsize(800, 500)
    popup.grab_set()
    
    # 제목
    title_label = tk.Label(
        popup,
        text="🎯 설문 퀴즈 문제 답안 관리",
        font=("맑은 고딕", 14, "bold"),
        bg='#f0f0f0',
        fg='#2c3e50'
    )
    title_label.pack(pady=(10, 5), padx=10)
    
    # 설명
    desc_label = tk.Label(
        popup,
        text="[퀴즈] 표시가 있는 문제의 답을 입력하세요. (예: 1, 2, O, X 등)",
        font=("맑은 고딕", 10),
        bg='#f0f0f0',
        fg='#7f8c8d'
    )
    desc_label.pack(padx=10)
    
    # 입력 영역 프레임
    input_frame = tk.Frame(popup, bg='#ffffff', relief='solid', borderwidth=1)
    input_frame.pack(fill='x', padx=10, pady=10)
    
    # 문제 입력
    tk.Label(input_frame, text="문제:", font=("맑은 고딕", 10), bg='#ffffff').pack(anchor='w', padx=10, pady=(10, 2))
    
    question_entry = tk.Text(
        input_frame,
        height=3,
        width=80,
        font=("맑은 고딕", 10),
        wrap='word'
    )
    question_entry.pack(padx=10, pady=(0, 10), fill='x', expand=True)
    
    # 정답 번호 및 정답 내용 입력 프레임
    ans_fields_frame = tk.Frame(input_frame, bg='#ffffff')
    ans_fields_frame.pack(anchor='w', fill='x', padx=10, pady=(0, 10))
    
    # 정답 번호
    ans_num_subframe = tk.Frame(ans_fields_frame, bg='#ffffff')
    ans_num_subframe.pack(side='left', padx=(0, 20))
    tk.Label(ans_num_subframe, text="정답 번호 (예: 1, 2, O, X):", font=("맑은 고딕", 10), bg='#ffffff').pack(anchor='w', pady=(0, 2))
    answer_num_entry = tk.Entry(
        ans_num_subframe,
        font=("맑은 고딕", 10),
        width=20
    )
    answer_num_entry.pack(anchor='w')
    
    # 정답 내용
    ans_content_subframe = tk.Frame(ans_fields_frame, bg='#ffffff')
    ans_content_subframe.pack(side='left', fill='x', expand=True)
    tk.Label(ans_content_subframe, text="정답 내용 (예: 정제로 분할 복용 가능):", font=("맑은 고딕", 10), bg='#ffffff').pack(anchor='w', pady=(0, 2))
    answer_content_entry = tk.Entry(
        ans_content_subframe,
        font=("맑은 고딕", 10),
        width=50
    )
    answer_content_entry.pack(anchor='w', fill='x')
    
    # 카테고리 입력
    tk.Label(input_frame, text="카테고리 (예: 제미다파, 글리벤클라마이드):", font=("맑은 고딕", 10), bg='#ffffff').pack(anchor='w', padx=10, pady=(0, 2))
    
    category_entry = tk.Entry(
        input_frame,
        font=("맑은 고딕", 10),
        width=40
    )
    category_entry.pack(anchor='w', padx=10, pady=(0, 10))
    

    # 초기값 설정
    if initial_question:
        question_entry.insert("1.0", initial_question)
    if initial_category:
        category_entry.insert(0, initial_category)
    
    # 버튼 프레임
    button_frame = tk.Frame(input_frame, bg='#ffffff')
    button_frame.pack(fill='x', padx=10, pady=(0, 10))
    
    # 수정 모드를 추적하는 변수
    edit_mode = {"active": False, "original_question": ""}
    
    def clear_inputs():
        """입력 필드를 초기화합니다."""
        question_entry.delete("1.0", "end")
        answer_num_entry.delete(0, "end")
        answer_content_entry.delete(0, "end")
        category_entry.delete(0, "end")

        edit_mode["active"] = False
        edit_mode["original_question"] = ""
        update_button_states()
    
    def add_or_update_quiz():
        """새 문제를 추가하거나 기존 문제를 수정합니다."""
        question = question_entry.get("1.0", "end").strip()
        ans_num = answer_num_entry.get().strip()
        parsed_answer = answer_content_entry.get().strip()
        category = category_entry.get().strip()
        
        if not question or (not ans_num and not parsed_answer):
            messagebox.showwarning("경고", "문제와 정답(번호 또는 내용)을 입력하세요.")
            return
            
        # 만약 정답 번호만 있고 내용은 비어있다면, 번호를 내용으로 채워줌
        if not parsed_answer:
            parsed_answer = ans_num
        elif not ans_num:
            ans_num = ""
            
        # 문제 제목 정규화 후 중복 검사
        normalized_q = problem_manager._normalize_question(question)
        
        display_ans = f"{ans_num}. {parsed_answer}" if ans_num and parsed_answer != ans_num else (parsed_answer or ans_num)
        
        if edit_mode["active"]:
            # 수정 모드
            old_question = edit_mode["original_question"]
            old_normalized_q = problem_manager._normalize_question(old_question)
            
            # 문제를 다른 텍스트로 변경했는데 변경하려는 새로운 문제가 이미 등록되어 있는 경우
            if normalized_q != old_normalized_q and normalized_q in problem_manager.get_all_quizzes():
                messagebox.showwarning("경고", "이미 등록된 문제(중복)입니다.")
                return
                
            problem_manager.delete_quiz(old_question)
            problem_manager.add_quiz(question, parsed_answer, category, answer_num=ans_num)
            messagebox.showinfo("성공", "문제가 수정되었습니다.")
            if gui_logger:
                category_str = f" [{category}]" if category else ""
                gui_logger(f"✏️ 퀴즈 수정: {question[:30]}...{category_str} → {display_ans}")
        else:
            # 추가 모드
            if normalized_q in problem_manager.get_all_quizzes():
                messagebox.showwarning("경고", "이미 등록된 문제(중복)입니다.")
                return
                
            if problem_manager.add_quiz(question, parsed_answer, category, answer_num=ans_num):
                if not initial_question:
                    messagebox.showinfo("성공", "문제가 추가되었습니다.")
                if gui_logger:
                    category_str = f" [{category}]" if category else ""
                    gui_logger(f"✅ 퀴즈 추가: {question[:30]}...{category_str} → {display_ans}")
                
                # 자동으로 열린 창이면 추가 후 파기하고 리턴
                if initial_question:
                    popup.destroy()
                    return
            else:
                messagebox.showerror("오류", "문제 추가에 실패했습니다.")
                return
        
        selection = cat_listbox.curselection()
        current_cat = cat_listbox.get(selection[0]) if selection else "전체"
        clear_inputs()
        refresh_list(current_cat)
    
    # 추가/수정 버튼 (동적으로 텍스트 변경)
    action_button = tk.Button(
        button_frame,
        text="➕ 추가",
        font=("맑은 고딕", 10, "bold"),
        bg='#27ae60',
        fg='white',
        command=add_or_update_quiz,
        padx=20
    )
    action_button.pack(side='left', padx=(0, 5))
    
    # 취소 버튼 (수정 중에만 보임)
    cancel_button = tk.Button(
        button_frame,
        text="✖️ 취소",
        font=("맑은 고딕", 10, "bold"),
        bg='#95a5a6',
        fg='white',
        command=clear_inputs,
        padx=20
    )
    cancel_button.pack(side='left', padx=5)
    cancel_button.pack_forget()  # 처음엔 숨김
    
    # 리스트 영역 상위 프레임 (사이드바 + 리스트)
    content_frame = tk.Frame(popup, bg='#f0f0f0')
    content_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

    # 카테고리 사이드바
    sidebar = tk.Frame(content_frame, width=150, bg='#ffffff', relief='solid', borderwidth=1)
    sidebar.pack(side='left', fill='y', padx=(0, 5))
    sidebar.pack_propagate(False)

    tk.Label(sidebar, text="📁 카테고리", font=("맑은 고딕", 10, "bold"), bg='#ffffff').pack(pady=(10, 5))
    
    cat_listbox = tk.Listbox(sidebar, font=("맑은 고딕", 10), bd=0, highlightthickness=0, selectmode='single', bg='#ffffff')
    cat_listbox.pack(fill='both', expand=True, padx=5, pady=5)
    
    # 리스트 영역 프레임
    list_frame = tk.Frame(content_frame, bg='#ffffff', relief='solid', borderwidth=1)
    list_frame.pack(side='left', fill='both', expand=True)
    
    # 리스트 제목
    list_title = tk.Label(
        list_frame,
        text="📋 등록된 문제 목록 (수정하려면 선택)",
        font=("맑은 고딕", 11, "bold"),
        bg='#ffffff',
        fg='#2c3e50'
    )
    list_title.pack(anchor='w', padx=10, pady=(10, 5))
    
    # 스크롤바와 트리뷰
    tree_frame = tk.Frame(list_frame, bg='#ffffff')
    tree_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
    
    scrollbar = ttk.Scrollbar(tree_frame)
    scrollbar.pack(side='right', fill='y')
    
    # original_q를 보이지 않는 컬럼으로 추가 (순서 조절 및 원본 데이터 유지용)
    tree = ttk.Treeview(
        tree_frame,
        columns=('category', 'question', 'answer_num', 'answer_content', 'original_q'),
        displaycolumns=('category', 'question', 'answer_num', 'answer_content'),
        height=12,
        yscrollcommand=scrollbar.set
    )
    scrollbar.config(command=tree.yview)
    
    tree.column('#0', width=0, stretch='no')
    tree.column('category', anchor='center', width=100)
    tree.column('question', anchor='w', width=450)
    tree.column('answer_num', anchor='center', width=80)
    tree.column('answer_content', anchor='w', width=170)
    tree.column('original_q', width=0, stretch='no')
    
    tree.heading('#0', text='', anchor='w')
    tree.heading('category', text='카테고리 ↕', anchor='center', command=lambda: sort_by_category())
    tree.heading('question', text='문제 (순서 조절: 드래그)', anchor='w')
    tree.heading('answer_num', text='정답 번호', anchor='center')
    tree.heading('answer_content', text='정답 내용', anchor='w')
    
    tree.pack(fill='both', expand=True)

    def on_category_select(event):
        """사이드바 카테고리 선택 시 이벤트"""
        selection = cat_listbox.curselection()
        if selection:
            cat = cat_listbox.get(selection[0])
            refresh_list(cat)

    cat_listbox.bind('<<ListboxSelect>>', on_category_select)
    
    def on_tree_select(event):
        """리스트에서 항목을 선택했을 때 입력 필드에 채웁니다."""
        selected = tree.selection()
        if not selected:
            return
        
        # 선택된 항목의 데이터 가져오기 (인덱스 4에 원본 문제 저장됨)
        item = selected[0]
        item_data = tree.item(item)
        original_question = item_data['values'][4]
        
        # 전체 문제 목록에서 데이터 가져오기
        quiz_data = problem_manager.get_all_quizzes().get(original_question)
        if quiz_data:
            if isinstance(quiz_data, dict):
                answer = quiz_data.get("answer", "")
                category = quiz_data.get("category", "")
                answer_num = quiz_data.get("answer_num", "")
            else:
                answer = quiz_data
                category = ""
                answer_num = ""
            
            # 구형식 호환성 및 입력 필드 분배
            if not answer_num:
                import re
                if str(answer).strip().upper() in ["O", "X"] or str(answer).isdigit():
                    answer_num = answer
                    answer_content = ""
                else:
                    answer_content = answer
            else:
                if answer == answer_num:
                    answer_content = ""
                else:
                    answer_content = answer
            
            # 입력 필드에 채우기
            question_entry.delete("1.0", "end")
            question_entry.insert("1.0", original_question)
            
            answer_num_entry.delete(0, "end")
            answer_num_entry.insert(0, answer_num)
            
            answer_content_entry.delete(0, "end")
            answer_content_entry.insert(0, answer_content)
            
            category_entry.delete(0, "end")
            category_entry.insert(0, category)
            

            
            # 수정 모드 활성화
            edit_mode["active"] = True
            edit_mode["original_question"] = original_question
            
            update_button_states()
    
    def update_button_states():
        """버튼 상태를 업데이트합니다."""
        if edit_mode["active"]:
            action_button.config(text="📝 수정", bg='#3498db')
            cancel_button.pack(side='left', padx=5)
        else:
            action_button.config(text="➕ 추가", bg='#27ae60')
            cancel_button.pack_forget()
    
    # 리스트 선택 이벤트 연결
    tree.bind('<<TreeviewSelect>>', on_tree_select)
    
    def refresh_categories():
        """카테고리 목록을 바에서 새로고침합니다."""
        current_selection = cat_listbox.curselection()
        selected_cat = cat_listbox.get(current_selection[0]) if current_selection else "전체"
        
        cat_listbox.delete(0, "end")
        cat_listbox.insert("end", "전체")
        
        # 유니크 카테고리 추출
        categories = set()
        for quiz_data in problem_manager.get_all_quizzes().values():
            if isinstance(quiz_data, dict):
                cat = quiz_data.get("category", "")
                if cat:
                    categories.add(cat)
        
        for cat in sorted(list(categories)):
            cat_listbox.insert("end", cat)
            
        # 기존 선택 유지
        idx = 0
        for i in range(cat_listbox.size()):
            if cat_listbox.get(i) == selected_cat:
                idx = i
                break
        cat_listbox.select_set(idx)
        cat_listbox.see(idx)

    def refresh_list(selected_category="전체"):
        """목록을 새로고침합니다."""
        for item in tree.get_children():
            tree.delete(item)
        
        quizzes = problem_manager.get_all_quizzes()
        for idx, (question, quiz_data) in enumerate(quizzes.items()):
            # 새로운 형식과 구형식 모두 지원
            if isinstance(quiz_data, dict):
                answer = quiz_data.get("answer", "")
                category = quiz_data.get("category", "")
                answer_num = quiz_data.get("answer_num", "")
            else:
                answer = quiz_data
                category = ""
                answer_num = ""
            
            # 구형식 호환성 파싱
            display_num = answer_num
            display_content = answer
            if not display_num:
                if str(answer).strip().upper() in ["O", "X"] or str(answer).isdigit():
                    display_num = answer
                    display_content = ""
                else:
                    display_content = answer
            else:
                if answer == answer_num:
                    display_content = ""
            
            # 카테고리 필터링
            if selected_category != "전체" and category != selected_category:
                continue
            
            # 표시는 요약본, 실제 데이터는 original_q 컬럼에 유지
            display_question = question[:100] + "..." if len(question) > 100 else question
            tree.insert('', 'end', values=(category, display_question, display_num, display_content, question))
        
        refresh_categories()
    
    def save_order():
        """트리뷰의 현재 순서대로 json 파일을 다시 저장합니다."""
        # 전체 보기일 때만 순서 조절 가능 (다른 카테고리가 섞여있으면 보존이 어려움)
        selection = cat_listbox.curselection()
        if selection and cat_listbox.get(selection[0]) != "전체":
            return
            
        new_answers = {}
        all_quizzes = problem_manager.get_all_quizzes()
        
        for item in tree.get_children():
            original_q = tree.item(item)['values'][4]
            if original_q in all_quizzes:
                new_answers[original_q] = all_quizzes[original_q]
        
        # 순서가 보장되는 딕셔너리로 교체 후 저장
        problem_manager.quiz_answers = new_answers
        problem_manager.save_quizzes()
        if gui_logger:
            gui_logger("↔️ 문제 순서가 변경되어 저장되었습니다.")

    sort_states = {"category": False}

    def sort_by_category():
        """카테고리 열을 기준으로 정렬하고 저장합니다."""
        reverse = sort_states["category"]
        items = [(tree.set(k, 'category'), k) for k in tree.get_children('')]
        items.sort(key=lambda x: x[0].lower(), reverse=reverse)
        for index, (val, k) in enumerate(items):
            tree.move(k, '', index)
        sort_states["category"] = not reverse
        arrow = " ▲" if reverse else " ▼"
        tree.heading('category', text=f'카테고리{arrow}')
        save_order()

    # 드래그 앤 드롭 구현
    def on_drag_start(event):
        item = tree.identify_row(event.y)
        if item:
            tree.drag_item = item

    def on_drag_stop(event):
        target_item = tree.identify_row(event.y)
        source_item = getattr(tree, 'drag_item', None)
        
        if source_item and target_item and source_item != target_item:
            # 타겟 위치 확인 (위에 놓는지 아래에 놓는지)
            target_idx = tree.index(target_item)
            tree.move(source_item, '', target_idx)
            save_order()
        
        tree.drag_item = None

    # 전체 보기일 때만 드래그 앤 드롭 바인딩
    tree.bind("<Button-1>", on_drag_start, add="+")
    tree.bind("<ButtonRelease-1>", on_drag_stop, add="+")
    
    def delete_selected():
        """선택된 문제를 삭제합니다."""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("경고", "삭제할 문제를 선택하세요.")
            return
        
        item = selected[0]
        original_question = tree.item(item)['values'][4]
        
        if messagebox.askyesno("확인", f"다음 문제를 삭제하시겠습니까?\n{original_question[:50]}..."):
            if problem_manager.delete_quiz(original_question):
                messagebox.showinfo("성공", "문제가 삭제되었습니다.")
                selection = cat_listbox.curselection()
                current_cat = cat_listbox.get(selection[0]) if selection else "전체"
                clear_inputs()  # 입력 필드 초기화
                refresh_list(current_cat)
                if gui_logger:
                    gui_logger(f"🗑️ 퀴즈 삭제: {original_question[:30]}...")
            else:
                messagebox.showerror("오류", "문제 삭제에 실패했습니다.")
    
    delete_button = tk.Button(
        button_frame,
        text="🗑️ 삭제",
        font=("맑은 고딕", 10, "bold"),
        bg='#e74c3c',
        fg='white',
        command=delete_selected,
        padx=20
    )
    delete_button.pack(side='left', padx=5)

    # 하단 버튼
    bottom_frame = tk.Frame(popup, bg='#f0f0f0')
    bottom_frame.pack(fill='x', padx=10, pady=(0, 10))
    
    close_button = tk.Button(
        bottom_frame,
        text="닫기",
        font=("맑은 고딕", 10, "bold"),
        bg='#3498db',
        fg='white',
        command=popup.destroy,
        padx=30
    )
    close_button.pack(side='right')
    
    # 초기 목록 로드
    refresh_list()
