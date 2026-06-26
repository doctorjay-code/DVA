# -*- coding: utf-8 -*-
import tkinter as tk

class ToolTip:
    """버튼 위에 마우스를 올리면 일정 시간 후 설명이 표시되는 툴팁 클래스"""
    def __init__(self, widget, text, delay=1500):
        self.widget = widget
        self.text = text
        self.delay = delay  # 밀리초 (기본 1.5초)
        self.tooltip_window = None
        self.scheduled_id = None
        
        # 기존 이벤트 핸들러를 보존하면서 툴팁 이벤트 추가
        self.widget.bind('<Enter>', self._on_enter, add='+')
        self.widget.bind('<Leave>', self._on_leave, add='+')
        self.widget.bind('<ButtonPress>', self._on_leave, add='+')
    
    def _on_enter(self, event=None):
        """마우스가 위젯 위에 올라왔을 때 - 지연 후 툴팁 표시 예약"""
        self._cancel_scheduled()
        self.scheduled_id = self.widget.after(self.delay, self._show_tooltip)
    
    def _on_leave(self, event=None):
        """마우스가 위젯에서 벗어났을 때 - 툴팁 숨기기"""
        self._cancel_scheduled()
        self._hide_tooltip()
    
    def _cancel_scheduled(self):
        """예약된 툴팁 표시를 취소합니다."""
        if self.scheduled_id:
            self.widget.after_cancel(self.scheduled_id)
            self.scheduled_id = None
    
    def _show_tooltip(self):
        """툴팁 창을 표시합니다."""
        if self.tooltip_window:
            return
        
        # 위젯의 위치 계산
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        # 툴팁 창 생성
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # 제목 표시줄 없앰
        tw.wm_geometry(f"+{x}+{y}")
        
        # 툴팁 외부 프레임 (테두리 효과)
        outer_frame = tk.Frame(
            tw,
            bg='#34495e',
            padx=1,
            pady=1
        )
        outer_frame.pack()
        
        # 툴팁 내부 프레임
        inner_frame = tk.Frame(
            outer_frame,
            bg='#fefefa',
            padx=10,
            pady=6
        )
        inner_frame.pack()
        
        # 툴팁 텍스트
        label = tk.Label(
            inner_frame,
            text=self.text,
            font=("맑은 고딕", 10),
            bg='#fefefa',
            fg='#2c3e50',
            justify='left',
            wraplength=300
        )
        label.pack()
        
        # 화면 밖으로 나가지 않도록 위치 보정
        tw.update_idletasks()
        screen_width = self.widget.winfo_screenwidth()
        screen_height = self.widget.winfo_screenheight()
        tw_width = tw.winfo_width()
        tw_height = tw.winfo_height()
        
        if x + tw_width > screen_width:
            x = screen_width - tw_width - 10
        if y + tw_height > screen_height:
            y = self.widget.winfo_rooty() - tw_height - 5
        
        tw.wm_geometry(f"+{x}+{y}")
    
    def _hide_tooltip(self):
        """툴팁 창을 숨깁니다."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
