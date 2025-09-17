#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox, font, filedialog
import pandas as pd
import datetime
from enum import Enum
import json
import os
import datetime

class Weekday(Enum):
    """星期枚举类型"""
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7
    
    @classmethod
    def from_name(cls, name):
        """从中文名称获取枚举值"""
        name_map = {
            "周一": cls.MONDAY,
            "周二": cls.TUESDAY,
            "周三": cls.WEDNESDAY,
            "周四": cls.THURSDAY,
            "周五": cls.FRIDAY,
            "周六": cls.SATURDAY,
            "周日": cls.SUNDAY
        }
        return name_map.get(name, cls.MONDAY)
    
    @classmethod
    def from_number(cls, number):
        """从数字获取枚举值"""
        try:
            num = int(number)
            if 1 <= num <= 7:
                return cls(num)
            return cls.MONDAY
        except (ValueError, TypeError):
            return cls.MONDAY
    
    def to_name(self):
        """获取中文名称"""
        name_map = {
            self.MONDAY: "周一",
            self.TUESDAY: "周二",
            self.WEDNESDAY: "周三",
            self.THURSDAY: "周四",
            self.FRIDAY: "周五",
            self.SATURDAY: "周六",
            self.SUNDAY: "周日"
        }
        return name_map.get(self, "周一")
    
    def to_column_index(self):
        """获取在课表中的列索引（1-based）"""
        return self.value


class TimeSelectionDialog:
    """时间选择对话框，允许用户在表格中选择课程时间"""
    def __init__(self, parent, week_range=None, initial_selection=None):
        self.parent = parent
        self.result = []  # 存储选择的时间信息
        self.selected = set()  # 存储已选择的单元格 (week, day, period)
        self.week_range = week_range or [1, 20]  # 默认1-20周
        self.initial_selection = initial_selection.copy() if initial_selection else []  # 保存初始选择
        
        # 如果有初始选择，将其添加到已选择集合中
        if initial_selection:
            for info in initial_selection:
                week = info["week"]
                day = info["day"]
                periods = info["periods"]
                for period in periods:
                    self.selected.add((week, day, period))
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("选择上课时间")
        self.dialog.geometry("800x600")
        
        # 注意：我们不在这里设置grab_set，因为调用者会使用wait_window()来处理模态行为
        
        # 创建主框架
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 提示信息
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(info_frame, text=f"请在表格中选择上课时间（周次范围：{self.week_range[0]}-{self.week_range[1]}周）").pack(side=tk.LEFT)
        
        # 创建内容区域容器（包含表格和按钮）
        content_container = ttk.Frame(main_frame)
        content_container.pack(fill=tk.BOTH, expand=True)
        
        # 使用grid布局来确保按钮始终可见
        content_container.grid_rowconfigure(0, weight=1)  # 表格区域占据剩余空间
        content_container.grid_rowconfigure(1, weight=0)  # 按钮区域固定高度
        content_container.grid_columnconfigure(0, weight=1)  # 让内容水平填充整个容器
        
        # 创建滚动条容器框架
        container_frame = ttk.Frame(content_container)
        container_frame.grid(row=0, column=0, sticky=tk.NSEW)
        
        # 创建主滚动容器
        main_scroll_container = ttk.Frame(container_frame)
        main_scroll_container.pack(fill=tk.BOTH, expand=True)
        
        # 创建水平滚动条
        scrollbar_x = ttk.Scrollbar(main_scroll_container, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建右侧滚动条
        scrollbar_y = ttk.Scrollbar(main_scroll_container, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建画布
        canvas = tk.Canvas(main_scroll_container)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建表格框架（包含周次列和可滚动的内容）
        self.table_frame = ttk.Frame(canvas)
        
        canvas.create_window((0, 0), window=self.table_frame, anchor="nw")
        
        # 在表格框架中创建左侧周次列容器
        self.week_column_frame = ttk.Frame(self.table_frame)
        self.week_column_frame.grid(row=0, column=0, sticky=tk.NSEW)
        
        # 在表格框架中创建右侧内容容器
        self.content_frame = ttk.Frame(self.table_frame)
        self.content_frame.grid(row=0, column=1, sticky=tk.NSEW)
        
        # 配置滚动条和画布的关联
        canvas.configure(yscrollcommand=scrollbar_y.set)
        scrollbar_y.config(command=canvas.yview)
        canvas.configure(xscrollcommand=scrollbar_x.set)
        scrollbar_x.config(command=canvas.xview)

        
        
        # 配置表格框架的列权重
        self.week_column_frame.grid_columnconfigure(0, weight=0)  # 周次列固定宽度
        self.content_frame.grid_columnconfigure(1, weight=1)  # 内容列占据剩余空间
        
        # 绑定鼠标滚轮事件以支持滚轮滚动
        def on_mousewheel(event):
            try:
                # 获取当前滚动位置
                y1 = canvas.yview()[0]
                y2 = canvas.yview()[1]
                
                # Windows系统使用event.delta
                if hasattr(event, 'delta'):
                    # Windows: 向上滚动delta为正，向下为负
                    delta = event.delta
                    # 向上滚动为正，向下为负，需要取反
                    if delta > 0:
                        # 检查是否已经到达顶部
                        if y1 > 0:
                            canvas.yview_scroll(-1, "units")
                    else:
                        # 检查是否已经到达底部
                        if y2 < 1:
                            canvas.yview_scroll(1, "units")
                else:
                    # Linux: Button-4向上，Button-5向下
                    if event.num == 4:
                        # 检查是否已经到达顶部
                        if y1 > 0:
                            canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        # 检查是否已经到达底部
                        if y2 < 1:
                            canvas.yview_scroll(1, "units")
            except Exception as e:
                print(f"滚轮事件处理错误: {e}")  # 调试信息
            return "break"
        
        # 绑定鼠标滚轮事件到所有可能的组件
        # 绑定到对话框本身
        self.dialog.bind("<MouseWheel>", on_mousewheel)
        self.dialog.bind("<Button-4>", on_mousewheel)
        self.dialog.bind("<Button-5>", on_mousewheel)
        
        # 绑定到主框架
        main_frame.bind("<MouseWheel>", on_mousewheel)
        main_frame.bind("<Button-4>", on_mousewheel)
        main_frame.bind("<Button-5>", on_mousewheel)
        
        # 绑定到容器框架
        container_frame.bind("<MouseWheel>", on_mousewheel)
        container_frame.bind("<Button-4>", on_mousewheel)
        container_frame.bind("<Button-5>", on_mousewheel)
        
        # 绑定到canvas
        canvas.bind("<MouseWheel>", on_mousewheel)
        canvas.bind("<Button-4>", on_mousewheel)
        canvas.bind("<Button-5>", on_mousewheel)
        
        # 确保canvas可以获得焦点
        canvas.focus_set()
        
        # 添加点击canvas时设置焦点
        def on_canvas_click(event):
            canvas.focus_set()
        canvas.bind("<Button-1>", on_canvas_click)
        
        # 绑定画布大小变化事件
        def on_configure(event):
            # 计算表格框架的实际大小
            bbox = self.table_frame.bbox("all")
            if bbox:
                # 获取canvas的当前大小
                canvas_width = canvas.winfo_width()
                canvas_height = canvas.winfo_height()
                
                # 计算实际需要的滚动区域
                # 确保滚动区域至少包含所有内容
                scroll_width = max(bbox[2], canvas_width)
                scroll_height = max(bbox[3], canvas_height)
                
                # 设置滚动区域，添加一些边距防止滚动到边界时出现问题
                scrollregion = (0, 0, scroll_width + 10, scroll_height + 10)
                canvas.configure(scrollregion=scrollregion)
                
                # 强制更新滚动条状态
                canvas.update_idletasks()
        
        self.table_frame.bind("<Configure>", on_configure)
        
        # 创建时间选择表格
        self.create_time_table()
        
        # 在表格创建完成后，手动更新滚动区域
        self.dialog.update_idletasks()
        bbox = self.table_frame.bbox("all")
        if bbox:
            # 确保滚动区域包含所有内容，添加额外边距
            scrollregion = (0, 0, bbox[2] + 20, bbox[3] + 20)
            canvas.configure(scrollregion=scrollregion)
            # 强制更新滚动条状态
            canvas.update_idletasks()
        
        # 按钮框架（使用grid布局确保始终可见）
        button_frame = ttk.Frame(content_container)
        button_frame.grid(row=1, column=0, sticky=tk.EW, pady=(10, 0))
        
        ttk.Button(button_frame, text="确认", command=self.confirm).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT, padx=5)
        
    def create_time_table(self):
        """创建时间选择表格"""
        # 星期标题
        days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        periods = ["1/2节", "3/4节", "5/6节", "7/8节", "9/10节"]
        
        # 创建周次标题行（在固定容器中）
        ttk.Label(self.week_column_frame, text="周次", font=("SimHei", 10, "bold"), width=8).grid(
            row=0, column=0, padx=1, pady=1)
        
        # 创建星期标题（每个星期占据5列）
        for col_idx, day in enumerate(days):
            # 合并5列创建星期标题
            ttk.Label(self.content_frame, text=day, font=("SimHei", 10, "bold"), width=40).grid(
                row=0, column=col_idx * 6 + 2, columnspan=5, padx=1, pady=1, sticky=tk.NSEW)
            
            # 在每个星期标题下创建时间段小标题
            for period_idx, period in enumerate(periods):
                ttk.Label(self.content_frame, text=period, font=("SimHei", 9), width=8).grid(
                    row=1, column=col_idx * 6 + period_idx, padx=1, pady=1, sticky=tk.NSEW)
            
            # 在每个星期后面添加竖线分隔符（除了最后一个星期）
            if col_idx < len(days) - 1:
                # 添加竖线分隔符，跨越所有行（标题行+时间段行+所有周次行）
                separator = ttk.Separator(self.content_frame, orient=tk.VERTICAL)
                separator.grid(row=0, column=col_idx * 6 + 5, rowspan=self.week_range[1] - self.week_range[0] + 3, 
                             sticky=tk.NS, padx=(2, 2))
        
        # 创建周次选择行（每行代表一周）
        for week in range(self.week_range[0], self.week_range[1] + 1):
            # 周次标签（在固定容器中）
            ttk.Label(self.week_column_frame, text=f"第{week}周", font=("SimHei", 9)).grid(
                row=week + 1, column=0, padx=1, pady=1, sticky=tk.NSEW)
            
            # 为每个周次创建时间段选择按钮
            for col_idx, day in enumerate(days):
                for period_idx, period in enumerate(periods):
                    # 计算实际节次（用于存储）
                    if period == "1/2节":
                        actual_periods = [1, 2]
                    elif period == "3/4节":
                        actual_periods = [3, 4]
                    elif period == "5/6节":
                        actual_periods = [5, 6]
                    elif period == "7/8节":
                        actual_periods = [7, 8]
                    else:  # "9/10节"
                        actual_periods = [9, 10]
                    
                    # 创建选择按钮，检查是否在初始选择中
                    is_selected = (week, day, actual_periods[0]) in self.selected
                    var = tk.BooleanVar(value=is_selected)
                    cb = ttk.Checkbutton(self.content_frame, variable=var)
                    cb.grid(row=week + 1, column=col_idx * 6 + period_idx, padx=1, pady=1, sticky=tk.NSEW)
                    
                    # 如果是初始选择，确保在selected集合中添加所有相关节次
                    if is_selected:
                        for p in actual_periods:
                            self.selected.add((week, day, p))
                    
                    # 保存按钮信息
                    cb_info = {
                        "var": var,
                        "week": week,
                        "day": day,
                        "periods": actual_periods,
                        "row": week + 1,
                        "col": col_idx * 5 + period_idx + 1
                    }
                    
                    # 绑定事件
                    var.trace_add("write", lambda *args, info=cb_info: self.on_checkbox_change(info))
                    
                    # 存储按钮信息
                    if not hasattr(self, "checkboxes"):
                        self.checkboxes = []
                    self.checkboxes.append(cb_info)
        
        # 确保表格大小合适，调整列宽避免挤占滚动条空间
        for i in range(self.week_range[1] - self.week_range[0] + 2): 
            # 为两个框架设置相同的行高配置，确保垂直对齐
            row_height = 40  # 固定行高
            self.content_frame.grid_rowconfigure(i, weight=0, minsize=row_height)
            self.week_column_frame.grid_rowconfigure(i, weight=0, minsize=row_height)
        
        # 配置周次列容器的列宽
        self.week_column_frame.grid_columnconfigure(0, weight=0, minsize=60)
        
        # 配置可滚动表格的列宽（不包含周次列）
        # 现在是7天×(5时间段+1分隔符) = 42列
        for i in range(42):  # 0-41列（7天×(5时间段+1分隔符)）
            if i % 6 == 5:  # 分隔符列
                self.content_frame.grid_columnconfigure(i, weight=0, minsize=4)  # 分隔符列很窄
            else:  # 时间段列
                self.content_frame.grid_columnconfigure(i, weight=1, minsize=15)
    
    def on_checkbox_change(self, info):
        """当复选框状态改变时的处理"""
        week = info["week"]
        day = info["day"]
        periods = info["periods"]
        
        if info["var"].get():
            # 选中状态
            for p in periods:
                self.selected.add((week, day, p))
        else:
            # 未选中状态
            for p in periods:
                if (week, day, p) in self.selected:
                    self.selected.remove((week, day, p))

    
    def confirm(self):
        """确认选择"""
        # 整理选择的时间信息
        schedule_dict = {}
        
        for week, day, period in self.selected:
            key = (week, day)
            if key not in schedule_dict:
                schedule_dict[key] = {
                    "week": week,
                    "day": day,
                    "periods": []
                }
            schedule_dict[key]["periods"].append(period)
        
        # 转换为列表
        self.result = sorted(schedule_dict.values(), key=lambda x: (x["week"], x["day"]))

        
        # 关闭对话框
        self.dialog.destroy()
    
    def cancel(self):
        """取消选择 - 保留初始选择，只清除本次修改"""
        # 如果有初始选择，恢复为初始选择
        if hasattr(self, 'initial_selection') and self.initial_selection:
            self.result = self.initial_selection.copy()
        else:
            self.result = []
        self.dialog.destroy()

class CourseScheduleApp:
    """课程表管理应用"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("课程表管理系统")
        self.root.geometry("1400x800")
        
        # 设置中文字体
        try:
            self.chinese_font = font.Font(family="Microsoft YaHei", size=10)
            self.title_font = font.Font(family="Microsoft YaHei", size=12, weight="bold")
        except:
            self.chinese_font = font.Font(family="Arial", size=10)
            self.title_font = font.Font(family="Arial", size=12, weight="bold")
        
        # 配置根窗口的字体
        self.root.option_add("*Font", self.chinese_font)
        
        # 初始化数据
        self.elective_courses = []
        self.selected_electives = []  # 修改：使用列表存储已选课程，而不是集合
        self.use_english_fallback = False
        self.week_range = [1, 20]  # 默认周次范围1-20周
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建可拖动的水平分隔面板
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 创建左侧课表框架
        self.schedule_frame = ttk.LabelFrame(self.paned_window, text="课程表", padding="10")
        
        # 创建右侧选修课框架
        self.elective_frame = ttk.LabelFrame(self.paned_window, text="选修课", padding="10")
        
        # 将两个框架添加到PanedWindow中
        self.paned_window.add(self.schedule_frame, weight=2)
        self.paned_window.add(self.elective_frame, weight=1)
        
        
        # 创建界面组件
        self.create_schedule_table()
        
        # 创建底部按钮框架
        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 添加按钮
        ttk.Button(self.button_frame, text="新建课表", command=self.create_new_schedule).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self.button_frame, text="今日课程", command=self.show_today_courses).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self.button_frame, text="添加课程", command=self.show_add_course_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self.button_frame, text="保存课表", command=self.export_schedule_json).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self.button_frame, text="加载课表", command=self.import_schedule_json).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self.button_frame, text="设置周次范围", command=self.set_week_range).pack(side=tk.LEFT, padx=(0, 5))
        
        #
        self.create_elective_list()

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    
    def create_new_schedule(self):
        """新建课表，询问周次起止时间"""
        dialog = tk.Toplevel(self.root)
        dialog.title("新建课表")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="请输入周次范围:").pack(pady=(20, 5))
        
        week_frame = ttk.Frame(dialog)
        week_frame.pack(pady=10)
        
        ttk.Label(week_frame, text="从").pack(side=tk.LEFT)
        start_var = tk.StringVar(value=str(self.week_range[0]))
        start_entry = ttk.Entry(week_frame, textvariable=start_var, width=5)
        start_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(week_frame, text="到").pack(side=tk.LEFT)
        end_var = tk.StringVar(value=str(self.week_range[1]))
        end_entry = ttk.Entry(week_frame, textvariable=end_var, width=5)
        end_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(week_frame, text="周").pack(side=tk.LEFT)
        
        def confirm():
            try:
                start_week = int(start_var.get())
                end_week = int(end_var.get())
                if start_week < 1 or end_week < start_week:
                    messagebox.showerror("错误", "请输入有效的周次范围")
                    return
                self.week_range = [start_week, end_week]
                self.weeks_list = list(range(start_week, end_week + 1))
                self.selected_electives.clear()
                self.update_schedule_display()
                # 更新右侧周次选择下拉框的选项
                self.update_week_combo()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="确定", command=confirm).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
    
    def set_week_range(self):
        """设置周次范围"""
        dialog = tk.Toplevel(self.root)
        dialog.title("设置周次范围")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="请输入周次范围:").pack(pady=(20, 5))
        
        week_frame = ttk.Frame(dialog)
        week_frame.pack(pady=10)
        
        ttk.Label(week_frame, text="从").pack(side=tk.LEFT)
        start_var = tk.StringVar(value=str(self.week_range[0]))
        start_entry = ttk.Entry(week_frame, textvariable=start_var, width=5)
        start_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(week_frame, text="到").pack(side=tk.LEFT)
        end_var = tk.StringVar(value=str(self.week_range[1]))
        end_entry = ttk.Entry(week_frame, textvariable=end_var, width=5)
        end_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(week_frame, text="周").pack(side=tk.LEFT)
        
        def confirm():
            try:
                start_week = int(start_var.get())
                end_week = int(end_var.get())
                if start_week < 1 or end_week < start_week:
                    messagebox.showerror("错误", "请输入有效的周次范围")
                    return
                self.week_range = [start_week, end_week]
                self.update_schedule_display()
                # 更新右侧周次选择下拉框的选项
                self.update_week_combo()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="确定", command=confirm).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
    
    def clear_schedule_display(self):
        """清空课表显示"""
        for item in self.schedule_tree.get_children():
            self.schedule_tree.delete(item)
    
    def create_schedule_table(self):
        """创建课表表格"""
        # 定义星期和节次
        if self.use_english_fallback:
            self.days = [self.get_fallback_text("周一"), self.get_fallback_text("周二"), 
                        self.get_fallback_text("周三"), self.get_fallback_text("周四"), 
                        self.get_fallback_text("周五"), self.get_fallback_text("周六"), 
                        self.get_fallback_text("周日")]
        else:
            self.days = [Weekday.MONDAY.to_name(), Weekday.TUESDAY.to_name(), 
                        Weekday.WEDNESDAY.to_name(), Weekday.THURSDAY.to_name(), 
                        Weekday.FRIDAY.to_name(), Weekday.SATURDAY.to_name(), 
                        Weekday.SUNDAY.to_name()]
        self.periods = [1, 2, 3, 4, 5, 6, 7, 8]  # 假设每天8节课
        
        # 创建Treeview作为课表
        columns = ["period"] + self.days
        self.schedule_tree = ttk.Treeview(self.schedule_frame, columns=columns, show="headings", height=len(self.periods))
        
        # 设置列标题
        period_text = self.get_fallback_text("节次") if self.use_english_fallback else "节次"
        self.schedule_tree.heading("period", text=period_text)
        self.schedule_tree.column("period", width=50, anchor=tk.CENTER)
        
        for day in self.days:
            self.schedule_tree.heading(day, text=day)
            self.schedule_tree.column(day, width=100, anchor=tk.CENTER)
        
        # 插入行（节次）
        for period in self.periods:
            self.schedule_tree.insert("", tk.END, values=[period] + [""]*len(self.days))
        
        # 添加滚动条
        scrollbar_y = ttk.Scrollbar(self.schedule_frame, orient=tk.VERTICAL, command=self.schedule_tree.yview)
        scrollbar_x = ttk.Scrollbar(self.schedule_frame, orient=tk.HORIZONTAL, command=self.schedule_tree.xview)
        self.schedule_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # 布局
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.schedule_tree.pack(fill=tk.BOTH, expand=True)
        
        # 添加双击事件，查看课程详情
        self.schedule_tree.bind("<Double-1>", self.show_course_details)
    
    def create_elective_list(self):
        """创建选修课列表"""
        # 使用现有的elective_frame而不是创建新的框架
        main_frame = self.elective_frame
        
        # 添加周次选择框架
        week_frame = ttk.Frame(main_frame)
        week_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(week_frame, text="选择周次：").pack(side=tk.LEFT, padx=(0, 5))
        
        # 使用动态周次范围（统一使用数字类型）
        self.week_var = tk.StringVar()
        self.weeks_list = [str(i) for i in range(self.week_range[0], self.week_range[1] + 1)]  # 界面显示仍用字符串
        self.week_combo = ttk.Combobox(week_frame, textvariable=self.week_var, values=self.weeks_list, state="readonly", width=10)
        
        # 添加上一周和下一周按钮
        prev_week_btn = ttk.Button(week_frame, text="上一周", command=self.prev_week, width=7)
        prev_week_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.week_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        next_week_btn = ttk.Button(week_frame, text="下一周", command=self.next_week, width=7)
        next_week_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 设置默认值
        if self.weeks_list:
            self.week_combo.set(self.weeks_list[0])
        
        # 绑定选择事件
        self.week_combo.bind('<<ComboboxSelected>>', lambda e: self.filter_courses_by_week())
        
        # 添加刷新按钮
        refresh_btn = ttk.Button(week_frame, text="刷新课程列表", command=self.filter_courses_by_week)
        refresh_btn.pack(side=tk.LEFT)
        
        # 添加说明标签
        info_label = ttk.Label(week_frame, text="（同一门课程只需选择一次，系统会自动安排所有时间）")
        info_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 创建课程列表框架
        # 创建垂直分隔面板用于课程列表和课程详情
        self.vertical_paned = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        self.vertical_paned.pack(fill=tk.BOTH, expand=True)
        
        # 创建课程列表框架
        list_frame = ttk.Frame(self.vertical_paned)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建课程列表
        self.elective_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=20)
        self.elective_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.elective_listbox.yview)
        
        # 创建复选框字典，用于跟踪课程选择状态
        self.course_checkboxes = {}
        
        # 添加课程到列表
        self.update_elective_list()
        
        # 绑定选择事件
        self.elective_listbox.bind('<<ListboxSelect>>', self.on_elective_select)
        
        # 创建按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 添加按钮
        ttk.Button(button_frame, text="添加选中课程", command=self.add_elective_course).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="移除选中课程", command=self.remove_elective_course).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="完全删除课程", command=self.delete_course_completely).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="编辑课程信息", command=self.edit_course).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="清空选择", command=self.clear_elective_selections).pack(side=tk.LEFT, padx=(0, 5))
        
        # 创建课程详情框架
        detail_frame = ttk.LabelFrame(self.vertical_paned, text="课程详情", padding="10")
        
        # 将课程列表和课程详情框架添加到垂直分隔面板中
        self.vertical_paned.add(list_frame, weight=3)
        self.vertical_paned.add(detail_frame, weight=1)
        
        # 创建课程详情文本框
        self.course_detail_text = tk.Text(detail_frame, height=8, width=50, wrap=tk.WORD)
        self.course_detail_text.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        detail_scrollbar = ttk.Scrollbar(self.course_detail_text)
        detail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.course_detail_text.config(yscrollcommand=detail_scrollbar.set)
        detail_scrollbar.config(command=self.course_detail_text.yview)
        
        # 设置文本框为只读
        self.course_detail_text.config(state=tk.DISABLED)
    
    def update_elective_list(self):
        """更新选修课列表显示，确保相同名称的课程只显示一次，并合并所有节次信息"""
        # 清空列表
        self.elective_listbox.delete(0, tk.END)
        self.course_checkboxes.clear()
        
        # 创建一个字典用于合并相同名称的课程
        merged_courses = {}
        
        # 遍历所有课程
        for course in self.elective_courses:
            course_name = course['name']
            
            # 如果是新课程，直接添加
            if course_name not in merged_courses:
                # 创建一个新的合并课程记录
                merged_courses[course_name] = {
                    "id": course["id"],
                    "name": course_name,
                    "schedule_info": [],  # 存储所有时间安排信息
                    "periods": set(),     # 存储所有节次
                    "weeks": set(),       # 存储所有周次
                    "teachers": set(),    # 存储所有教师
                    "locations": set()    # 存储所有地点
                }
            
            # 合并课程信息
            merged_course = merged_courses[course_name]
            
            # 合并时间安排信息
            if "schedule_info" in course:
                merged_course["schedule_info"].extend(course["schedule_info"])
            
            # 合并节次信息
            if "periods" in course:
                for period in course["periods"]:
                    merged_course["periods"].add(period)
            
            # 合并周次信息（统一使用数字类型）
            if "weeks" in course:
                if isinstance(course["weeks"], list):
                    for week in course["weeks"]:
                        merged_course["weeks"].add(int(week))
                elif isinstance(course["weeks"], str):
                    merged_course["weeks"].add(int(course["weeks"]))
            
            # 合并教师信息
            if "teacher" in course and course["teacher"] and course["teacher"] != "未知教师":
                merged_course["teachers"].add(course["teacher"])
            
            # 合并地点信息
            if "location" in course and course["location"] and course["location"] != "未知地点":
                merged_course["locations"].add(course["location"])
        
        # 格式化合并后的课程信息并添加到列表
        for course_name, merged_course in merged_courses.items():
            # 对节次进行排序
            all_periods = sorted(merged_course["periods"])
            
            # 格式化教师和地点信息
            teachers = ", ".join(sorted(merged_course["teachers"])) if merged_course["teachers"] else "未知教师"
            locations = ", ".join(sorted(merged_course["locations"])) if merged_course["locations"] else "未知地点"
            weeks = ", ".join(str(w) for w in sorted(merged_course["weeks"])) if merged_course["weeks"] else "未知周次"
            
            # 创建完整的课程记录
            full_course = {
                "id": merged_course["id"],
                "name": course_name,
                "schedule_info": merged_course["schedule_info"],
                "periods": all_periods,
                "weeks": sorted([int(w) for w in merged_course["weeks"]]),  # 统一使用数字类型
                "teacher": teachers,
                "location": locations
            }
            
            # 创建课程显示文本
            display_text = f"{course_name} - {teachers}"
            
            # 添加到列表框
            self.elective_listbox.insert(tk.END, display_text)
            
            # 存储课程信息
            self.course_checkboxes[display_text] = {
                "course": full_course,
                "selected": False
            }
    

        
    def update_week_combo(self):
        """更新右侧周次选择下拉框的选项"""
        if hasattr(self, 'week_combo') and hasattr(self, 'week_var'):
            # 更新周次列表（界面显示用字符串）
            self.weeks_list = [str(i) for i in range(self.week_range[0], self.week_range[1] + 1)]
            
            # 保存当前选中的周次
            current_week = self.week_var.get()
            
            # 更新下拉框的选项
            self.week_combo['values'] = self.weeks_list
            
            # 如果当前选中的周次不在新范围内，则选择第一个周次
            if current_week not in self.weeks_list:
                if self.weeks_list:
                    self.week_combo.set(self.weeks_list[0])
            else:
                # 保持当前选中的周次
                self.week_combo.set(current_week)
            
            # 刷新课程列表以反映新的周次范围
            self.filter_courses_by_week()
    
    def prev_week(self):
        """切换到上一周"""
        if not hasattr(self, 'weeks_list') or not self.weeks_list:
            return
            
        current_week = self.week_var.get()
        if current_week in self.weeks_list:
            current_index = self.weeks_list.index(current_week)
            if current_index > 0:
                # 不是第一周，可以切换到上一周
                prev_index = current_index - 1
                self.week_combo.set(self.weeks_list[prev_index])
                self.filter_courses_by_week()
                
    def next_week(self):
        """切换到下一周"""
        if not hasattr(self, 'weeks_list') or not self.weeks_list:
            return
            
        current_week = self.week_var.get()
        if current_week in self.weeks_list:
            current_index = self.weeks_list.index(current_week)
            if current_index < len(self.weeks_list) - 1:
                # 不是最后一周，可以切换到下一周
                next_index = current_index + 1
                self.week_combo.set(self.weeks_list[next_index])
                self.filter_courses_by_week()
    
    def on_elective_select(self, event):
        """选修课选择事件"""
        selection = self.elective_listbox.curselection()
        if selection:
            index = selection[0]
            display_text = self.elective_listbox.get(index)
            
            if display_text in self.course_checkboxes:
                course_info = self.course_checkboxes[display_text]
                course = course_info["course"]
                
                # 显示课程详情
                self.show_course_details(course)
    
    def show_course_details(self, course):
        """显示课程详细信息，改进节次显示逻辑"""
        # 启用文本框
        self.course_detail_text.config(state=tk.NORMAL)
        
        # 清空文本框
        self.course_detail_text.delete(1.0, tk.END)
        
        # 添加课程信息
        details = f"课程名称：{course['name']}\n"
        details += f"教师：{course['teacher']}\n"
        details += f"地点：{course['location']}\n"
        details += f"周次：{', '.join(str(w) for w in course['weeks']) if course['weeks'] else '未知'}\n"
        
        # 改进节次显示，展示完整的节次范围
        if "periods" in course and course["periods"]:
            all_periods = sorted(course["periods"])
            # 将连续的节次合并为范围显示
            periods_str = ""
            if all_periods:
                ranges = []
                start = all_periods[0]
                end = start
                
                for i in range(1, len(all_periods)):
                    if all_periods[i] == end + 1:
                        end = all_periods[i]
                    else:
                        if start == end:
                            ranges.append(str(start))
                        else:
                            ranges.append(f"{start}-{end}")
                        start = end = all_periods[i]
                
                # 添加最后一个范围
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                
                periods_str = ", ".join(ranges)
            details += f"所有节次：{periods_str}\n"
        else:
            details += "所有节次：未知\n"
        
        # 添加详细时间安排
        if "schedule_info" in course and course["schedule_info"]:
            details += "\n详细时间安排：\n"
            for schedule in course["schedule_info"]:
                # 改进每个时间安排的节次显示
                if "periods" in schedule and schedule["periods"]:
                    periods = schedule["periods"]
                    if len(periods) == 1:
                        period_text = f"第{periods[0]}节"
                    else:
                        period_text = f"第{min(periods)}-{max(periods)}节"
                else:
                    period_text = "未知节次"
                
                details += f"  {schedule['day']} {period_text} (周次{schedule['week']})\n"
                if "date_range" in schedule and schedule["date_range"]:
                    details += f"    日期范围：{schedule['date_range']}\n"
                if "major" in schedule and schedule["major"]:
                    details += f"    专业：{schedule['major']}\n"
        
        # 插入文本
        self.course_detail_text.insert(1.0, details)
        
        # 禁用文本框
        self.course_detail_text.config(state=tk.DISABLED)
    
    def add_elective_course(self):
        """添加选中的选修课"""
        selection = self.elective_listbox.curselection()
        if selection:
            index = selection[0]
            display_text = self.elective_listbox.get(index)
            
            if display_text in self.course_checkboxes:
                course_info = self.course_checkboxes[display_text]
                course = course_info["course"]
                
                # 检查是否已经选择了该课程
                if course["name"] in [c["name"] for c in self.selected_electives]:
                    messagebox.showwarning("提示", f"您已经选择了课程：{course['name']}")
                    return
                
                # 检查时间冲突
                conflicts = self.check_course_conflict(course)
                
                if conflicts:
                    # 格式化时间段显示
                    def format_periods(periods):
                        if isinstance(periods, list):
                            return '-'.join(str(p) for p in sorted(periods))
                        return str(periods)
                    
                    # 按冲突课程和时间分组显示所有冲突
                    conflict_groups = {}
                    for conflict in conflicts:
                        key = (conflict['conflict_course'], conflict['week'], conflict['day'])
                        if key not in conflict_groups:
                            conflict_groups[key] = []
                        conflict_groups[key].extend(conflict['conflict_periods'])
                    
                    # 构建冲突消息
                    conflict_msg = "⚠️ 重点警告：时间冲突 ⚠️\n\n"
                    conflict_msg += f"课程 {course['name']} 与以下已选课程存在时间冲突：\n\n"
                    
                    for (conflict_course, week, day), conflict_periods in conflict_groups.items():
                        # 去重并排序冲突节次
                        unique_periods = sorted(list(set(conflict_periods)))
                        conflict_msg += f"• 与《{conflict_course}》冲突：\n"
                        conflict_msg += f"  时间：第{week}周 {day}\n"
                        conflict_msg += f"  冲突节次：{format_periods(unique_periods)}节\n\n"
                    
                    conflict_msg += "您仍然可以选择此课程，但请注意时间安排！"
                    messagebox.showerror("时间冲突警告", conflict_msg)
                
                # 添加到已选课程列表（即使有冲突）
                self.selected_electives.append(course)
                
                # 更新课表显示
                self.update_schedule_display()
                # 强制刷新界面
                self.root.update_idletasks()
                
                if conflicts:
                    # 构建成功添加但有冲突的消息
                    conflict_courses = set(conflict['conflict_course'] for conflict in conflicts)
                    conflict_details = []
                    
                    for (conflict_course, week, day), conflict_periods in conflict_groups.items():
                        unique_periods = sorted(list(set(conflict_periods)))
                        conflict_details.append(f"• 与《{conflict_course}》在第{week}周{day}的{format_periods(unique_periods)}节冲突")
                    
                    conflict_msg = "\n\n请注意以下冲突：\n" + "\n".join(conflict_details)
                    messagebox.showinfo("已添加（存在冲突）", f"已添加课程：{course['name']}{conflict_msg}")
                else:
                    messagebox.showinfo("成功", f"已添加课程：{course['name']}")
    
    def remove_elective_course(self):
        """移除选中的选修课（仅从已选列表中移除）"""
        selection = self.elective_listbox.curselection()
        if selection:
            index = selection[0]
            display_text = self.elective_listbox.get(index)
            
            if display_text in self.course_checkboxes:
                course_info = self.course_checkboxes[display_text]
                course = course_info["course"]
                
                # 从已选课程列表中移除
                self.selected_electives = [c for c in self.selected_electives if c["name"] != course["name"]]
                
                # 更新课表显示
                self.update_schedule_display()
                # 强制刷新界面
                self.root.update_idletasks()
                
                messagebox.showinfo("成功", f"已移除课程：{course['name']}")
    
    def delete_course_completely(self):
        """完全删除选中的课程（从所有列表中删除）"""
        selection = self.elective_listbox.curselection()
        if selection:
            index = selection[0]
            display_text = self.elective_listbox.get(index)
            
            if display_text in self.course_checkboxes:
                course_info = self.course_checkboxes[display_text]
                course = course_info["course"]
                
                # 确认删除
                if messagebox.askyesno("确认删除", f"确定要完全删除课程《{course['name']}》吗？\n此操作将从系统中彻底删除该课程的所有信息！"):
                    # 从已选课程列表中移除
                    self.selected_electives = [c for c in self.selected_electives if c["name"] != course["name"]]
                    
                    # 从选修课列表中完全删除所有同名课程
                    self.elective_courses = [c for c in self.elective_courses if c["name"] != course["name"]]
                    
                    # 更新选修课列表显示
                    self.update_elective_list()
                    
                    # 更新课表显示
                    self.update_schedule_display()
                    # 强制刷新界面
                    self.root.update_idletasks()
                    
                    messagebox.showinfo("成功", f"已完全删除课程：{course['name']}")
    
    def clear_elective_selections(self):
        """清空所有选修课选择"""
        if messagebox.askyesno("确认", "确定要清空所有已选课程吗？"):
            self.selected_electives.clear()
            self.update_schedule_display()
            messagebox.showinfo("成功", "已清空所有已选课程")
    
    def edit_course(self):
        """编辑课程信息，支持修改教师、教室和上课时间"""
        # 获取当前选择的课程
        selection = self.elective_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要编辑的课程")
            return
        
        # 获取课程信息
        index = selection[0]
        display_text = self.elective_listbox.get(index)
        
        if display_text in self.course_checkboxes:
            course_info = self.course_checkboxes[display_text]
            course = course_info["course"]
            
            # 创建编辑对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("编辑课程信息")
            dialog.geometry("500x500")
            dialog.resizable(True, True)
            
            # 使对话框成为模态窗口
            dialog.grab_set()
            
            # 创建主容器框架
            main_frame = ttk.Frame(dialog)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 创建滚动条
            canvas = tk.Canvas(main_frame)
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # 创建输入框架
            input_frame = ttk.Frame(scrollable_frame, padding="20")
            input_frame.pack(fill=tk.BOTH, expand=True)
            
            # 课程名称（不可编辑）
            ttk.Label(input_frame, text="课程名称：").grid(row=0, column=0, sticky=tk.W, pady=5)
            course_name_var = tk.StringVar(value=course["name"])
            ttk.Entry(input_frame, textvariable=course_name_var, width=30, state="readonly").grid(row=0, column=1, sticky=tk.W, pady=5)
            
            # 教师姓名
            ttk.Label(input_frame, text="教师姓名：").grid(row=1, column=0, sticky=tk.W, pady=5)
            teacher_var = tk.StringVar(value=course.get("teacher", "未知教师"))
            ttk.Entry(input_frame, textvariable=teacher_var, width=30).grid(row=1, column=1, sticky=tk.W, pady=5)
            
            # 教室地点
            ttk.Label(input_frame, text="教室地点：").grid(row=2, column=0, sticky=tk.W, pady=5)
            location_var = tk.StringVar(value=course.get("location", "未知地点"))
            ttk.Entry(input_frame, textvariable=location_var, width=30).grid(row=2, column=1, sticky=tk.W, pady=5)
            
            # 时间安排选择
            schedule_info = course.get("schedule_info", []).copy()
            time_label_var = tk.StringVar()
            
            # 显示当前时间安排
            ttk.Label(input_frame, text="时间安排：").grid(row=3, column=0, sticky=tk.NW, pady=5)
            time_label = ttk.Label(input_frame, textvariable=time_label_var, wraplength=300, justify=tk.LEFT)
            time_label.grid(row=3, column=1, sticky=tk.W, pady=5)
            
            # 更新时间显示
            def update_time_display():
                if schedule_info:
                    time_text = []
                    for info in schedule_info:
                        # 排序节次
                        sorted_periods = sorted(info['periods'])
                        
                        # 处理连续和非连续的节次范围
                        if len(sorted_periods) > 1 and sorted_periods[-1] - sorted_periods[0] == len(sorted_periods) - 1:
                            # 如果是连续的范围
                            period_text = f"{sorted_periods[0]}-{sorted_periods[-1]}节"
                        else:
                            # 如果是非连续的节次，逐一列出
                            period_ranges = []
                            i = 0
                            while i < len(sorted_periods):
                                start = sorted_periods[i]
                                # 查找连续的范围
                                j = i
                                while j + 1 < len(sorted_periods) and sorted_periods[j + 1] == sorted_periods[j] + 1:
                                    j += 1
                                if j > i:
                                    # 有连续的范围
                                    period_ranges.append(f"{start}-{sorted_periods[j]}")
                                else:
                                    # 单个节次
                                    period_ranges.append(str(start))
                                i = j + 1
                            period_text = f"{','.join(period_ranges)}节"
                        
                        time_text.append(f"第{info['week']}周 {info['day']} {period_text}")
                    time_label_var.set("\n".join(time_text))
                else:
                    time_label_var.set("尚未选择时间")
            
            update_time_display()
            
            # 按钮框架（固定在底部）
            button_frame = ttk.Frame(dialog, padding="10 20 20 20")
            button_frame.pack(side=tk.BOTTOM, fill=tk.X)
            
            def choose_time():
                nonlocal schedule_info
                # 复用添加课程的时间选择对话框
                time_dialog = TimeSelectionDialog(dialog, self.week_range, schedule_info)
                # 等待对话框关闭
                dialog.wait_window(time_dialog.dialog)
                schedule_info = time_dialog.result or []
                update_time_display()
            
            ttk.Button(button_frame, text="修改上课时间", command=choose_time).pack(side=tk.LEFT, padx=5)
            
            # 保存修改按钮
            def save_changes():
                # 获取修改后的信息
                new_teacher = teacher_var.get().strip() or "未知教师"
                new_location = location_var.get().strip() or "未知地点"
                
                if not schedule_info:
                    messagebox.showerror("错误", "请选择上课时间")
                    return
                
                # 收集所有周次和节次
                weeks = {info['week'] for info in schedule_info}
                periods = {p for info in schedule_info for p in info['periods']}
                
                # 创建更新后的课程记录
                updated_course = {
                    "id": course["id"],
                    "name": course['name'],
                    "teacher": new_teacher,
                    "location": new_location,
                    "schedule_info": schedule_info,
                    "weeks": sorted(weeks),
                    "periods": sorted(periods)
                }
                
                # 检查冲突（排除自身）
                # 临时从已选课程中移除当前编辑的课程
                temp_electives = [c for c in self.selected_electives if c["id"] != course["id"]]
                original_electives = self.selected_electives
                self.selected_electives = temp_electives
                
                # 检查冲突
                conflicts = self.check_course_conflict(updated_course)
                
                # 恢复原始已选课程列表
                self.selected_electives = original_electives
                
                # 更新课程信息
                course.update(updated_course)
                
                # 同时更新选修课列表中的课程信息
                for i, elective_course in enumerate(self.elective_courses):
                    if elective_course["id"] == course["id"]:
                        self.elective_courses[i] = updated_course
                        break
                
                for i, elective_course in enumerate(self.selected_electives):
                    if elective_course["id"] == course["id"]:
                        self.selected_electives[i] = updated_course
                        break
                    
                # 更新显示
                self.update_elective_list()
                self.update_schedule_display()
                
                # 显示结果
                if conflicts:
                    messagebox.showinfo("已更新（存在冲突）", f"已更新课程：{course['name']}\n\n请注意时间冲突")
                else:
                    messagebox.showinfo("成功", f"已更新课程：{course['name']}")
                
                # 关闭对话框
                dialog.destroy()
            
            ttk.Button(button_frame, text="保存修改", command=save_changes).pack(side=tk.RIGHT, padx=5)
    
    def check_course_conflict(self, new_course):
        """检查课程时间冲突，返回所有冲突信息列表"""
        if "schedule_info" not in new_course:
            return []  # 返回空列表表示没有冲突
        
        conflicts = []
        
        for schedule in new_course["schedule_info"]:
            day = schedule["day"]
            periods = schedule["periods"]
            week = schedule["week"]
            
            # 检查与已选课程的冲突
            for selected_course in self.selected_electives:
                if "schedule_info" in selected_course:
                    for selected_schedule in selected_course["schedule_info"]:
                        if (selected_schedule["day"] == day and 
                            selected_schedule["week"] == week and
                            any(p in selected_schedule["periods"] for p in periods)):
                            # 计算具体的冲突节次
                            conflicting_periods = [p for p in periods if p in selected_schedule["periods"]]
                            
                            # 添加冲突信息
                            conflicts.append({
                                "conflict_course": selected_course["name"],
                                "new_course": new_course["name"],
                                "day": day,
                                "week": week,
                                "periods": periods,
                                "conflict_periods": conflicting_periods,
                                "selected_periods": selected_schedule["periods"]
                            })
        
        return conflicts  # 返回所有冲突信息列表
    

    
    def reset_selection(self):
        """重置选修课选择"""
        if self.use_english_fallback:
            title = self.get_fallback_text("确认重置")
            message = "Are you sure you want to cancel all selected elective courses?"
        else:
            title = "确认重置"
            message = "确定要取消所有已选的选修课吗？"
        
        if messagebox.askyesno(title, message):
            self.selected_electives.clear()
            self.update_schedule_display()

    def export_schedule_json(self):
        """导出课表为JSON文件，包含全部选修课程信息"""
        try:
            # 确保datas目录存在
            datas_dir = os.path.join(os.path.dirname(__file__), "..", "datas")
            os.makedirs(datas_dir, exist_ok=True)
            
            # 询问用户导出的文件名
            filename = tk.filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="保存课表文件",
                initialdir=datas_dir,
                initialfile=f"course_schedule_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            if not filename:  # 用户取消了选择
                return
            
            # 准备导出的数据 - 只导出选修课程数据
            export_data = {
                "elective_courses": self.elective_courses,
                "week_range": self.week_range,
                "selected_electives": self.selected_electives,
                "timestamp": datetime.datetime.now().isoformat(),
                "export_version": "1.0"
            }
            
            # 保存到JSON文件
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", f"选修课程数据已导出到 {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"导出课表失败：{str(e)}")
    
    def import_schedule_json(self):
        """从JSON文件导入选修课程数据"""
        try:
            # 扫描datas目录中的JSON文件
            datas_dir = os.path.join(os.path.dirname(__file__), "..", "datas")
            os.makedirs(datas_dir, exist_ok=True)
            
            # 获取datas目录中的所有JSON文件
            json_files = []
            if os.path.exists(datas_dir):
                for file in os.listdir(datas_dir):
                    if file.endswith('.json'):
                        json_files.append(file)
            
            # 如果没有找到JSON文件，提示用户
            if not json_files:
                messagebox.showinfo("提示", "datas目录中没有找到JSON文件，请先导出课表数据")
                return
            
            # 创建文件选择对话框
            file_dialog = tk.Toplevel(self.root)
            file_dialog.title("选择要导入的课表文件")
            file_dialog.geometry("500x300")
            file_dialog.resizable(False, False)
            file_dialog.grab_set()
            
            # 创建文件列表框架
            list_frame = ttk.Frame(file_dialog, padding="20")
            list_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(list_frame, text="请选择要导入的文件：").pack(pady=5)
            
            # 创建列表框
            file_listbox = tk.Listbox(list_frame, height=10)
            file_listbox.pack(fill=tk.BOTH, expand=True, pady=10)
            
            # 添加文件到列表框
            for file in sorted(json_files):
                file_listbox.insert(tk.END, file)
            
            # 绑定双击事件
            def on_double_click(event):
                selection = file_listbox.curselection()
                if selection:
                    on_select()
            
            file_listbox.bind("<Double-Button-1>", on_double_click)
            
            # 绑定回车键
            def on_return(event):
                selection = file_listbox.curselection()
                if selection:
                    on_select()
            
            file_listbox.bind("<Return>", on_return)
            
            # 选择按钮框架
            button_frame = ttk.Frame(list_frame)
            button_frame.pack(pady=10)
            
            selected_file = None
            
            def on_select():
                nonlocal selected_file
                selection = file_listbox.curselection()
                if selection:
                    selected_file = json_files[selection[0]]
                    file_dialog.destroy()
            
            def on_cancel():
                file_dialog.destroy()
            
            ttk.Button(button_frame, text="选择", command=on_select).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)
            
            # 等待用户选择
            self.root.wait_window(file_dialog)
            
            if not selected_file:
                return
            
            # 构建完整文件路径
            filename = os.path.join(datas_dir, selected_file)
            
            # 从JSON文件加载
            with open(filename, "r", encoding="utf-8") as f:
                import_data = json.load(f)
            
            # 验证导入数据格式
            if "elective_courses" not in import_data:
                messagebox.showerror("错误", "导入文件格式不正确，缺少选修课程数据")
                return
            
            # 恢复选修课程数据
            self.elective_courses = import_data["elective_courses"]
            self.week_range = import_data.get("week_range", (1, 20))
            self.selected_electives = import_data.get("selected_electives", [])
            
            # 更新显示
            self.update_elective_list()
            self.update_schedule_display()
            self.update_week_combo()
            
            timestamp = import_data.get("timestamp", "未知时间")
            messagebox.showinfo("成功", f"选修课程数据已导入（导出时间：{timestamp}）\n请从课程列表中选择要添加的课程")
        except Exception as e:
            messagebox.showerror("错误", f"导入课表失败：{str(e)}")
    

    
    def show_add_course_dialog(self):
        """显示添加课程的对话框"""
        
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("添加新课程")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        
        # 使对话框成为模态窗口
        dialog.grab_set()
        
        # 创建输入框架
        input_frame = ttk.Frame(dialog, padding="20")
        input_frame.pack(fill=tk.BOTH, expand=True)
        
        # 课程名称
        ttk.Label(input_frame, text="课程名称：").grid(row=0, column=0, sticky=tk.W, pady=5)
        course_name_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=course_name_var, width=30).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 教师姓名
        ttk.Label(input_frame, text="教师姓名：").grid(row=1, column=0, sticky=tk.W, pady=5)
        teacher_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=teacher_var, width=30).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 教室地点
        ttk.Label(input_frame, text="教室地点：").grid(row=2, column=0, sticky=tk.W, pady=5)
        location_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=location_var, width=30).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(dialog, padding="0 20 20 20")
        button_frame.pack(fill=tk.X)
        
        # 选择时间按钮
        schedule_info = []
        time_label_var = tk.StringVar(value="尚未选择时间")
        ttk.Label(button_frame, textvariable=time_label_var).pack(side=tk.LEFT, padx=5)
        
        def choose_time():
            nonlocal schedule_info
            # 将之前的选择作为初始选择传递给对话框
            time_dialog = TimeSelectionDialog(dialog, self.week_range, schedule_info)
            # 等待对话框关闭
            dialog.wait_window(time_dialog.dialog)
            schedule_info = time_dialog.result
            if schedule_info:
                # 格式化时间信息显示
                time_text = []
                for info in schedule_info:
                    # 排序节次
                    sorted_periods = sorted(info['periods'])
                    
                    # 处理连续和非连续的节次范围
                    if len(sorted_periods) > 1 and sorted_periods[-1] - sorted_periods[0] == len(sorted_periods) - 1:
                        # 如果是连续的范围
                        period_text = f"{sorted_periods[0]}-{sorted_periods[-1]}节"
                    else:
                        # 如果是非连续的节次，逐一列出
                        period_ranges = []
                        i = 0
                        while i < len(sorted_periods):
                            start = sorted_periods[i]
                            # 查找连续的范围
                            j = i
                            while j + 1 < len(sorted_periods) and sorted_periods[j + 1] == sorted_periods[j] + 1:
                                j += 1
                            if j > i:
                                # 有连续的范围
                                period_ranges.append(f"{start}-{sorted_periods[j]}")
                            else:
                                # 单个节次
                                period_ranges.append(str(start))
                            i = j + 1
                        period_text = f"{','.join(period_ranges)}节"
                    
                    time_text.append(f"第{info['week']}周 {info['day']} {period_text}")
                time_label_var.set("\n".join(time_text))
        
        ttk.Button(button_frame, text="选择上课时间", command=choose_time).pack(side=tk.RIGHT, padx=5)
        
        # 添加课程按钮
        def add_course():
            # 验证输入
            course_name = course_name_var.get().strip()
            if not course_name:
                messagebox.showerror("错误", "请输入课程名称")
                return
            
            if not schedule_info:
                messagebox.showerror("错误", "请选择上课时间")
                return
            
            # 创建课程记录
            teacher = teacher_var.get().strip() or "未知教师"
            location = location_var.get().strip() or "未知地点"
            
            # 收集所有周次
            weeks = {info['week'] for info in schedule_info}
            periods = {p for info in schedule_info for p in info['periods']}
            
            new_course = {
                "id": max([c.get("id", 0) for c in self.elective_courses] or [0]) + 1,
                "name": course_name,
                "teacher": teacher,
                "location": location,
                "schedule_info": schedule_info,
                "weeks": sorted(weeks),
                "periods": sorted(periods)
            }
            
            # 检查冲突
            conflicts = self.check_course_conflict(new_course)
            
            # 添加到选修课列表和已选课程
            self.elective_courses.append(new_course)
            self.selected_electives.append(new_course)
            
            # 更新显示
            self.update_elective_list()
            self.update_schedule_display()
            
            # 显示结果
            if conflicts:
                messagebox.showinfo("已添加（存在冲突）", f"已添加课程：{course_name}\n\n请注意时间冲突")
            else:
                messagebox.showinfo("成功", f"已添加课程：{course_name}")
            
            # 关闭对话框
            dialog.destroy()
        
        ttk.Button(button_frame, text="添加课程", command=add_course).pack(side=tk.RIGHT, padx=5)
    
    def on_closing(self):
        """窗口关闭事件处理"""
        if messagebox.askyesno("退出", "确定要退出程序吗？"):
            self.root.destroy()
    
    def show_today_courses(self):
        """显示今日课程"""
        # 获取今天是星期几
        today_weekday = datetime.datetime.now().weekday()
        # datetime的weekday()返回0-6，对应周一到周日
        weekday_map = {0: Weekday.MONDAY, 1: Weekday.TUESDAY, 2: Weekday.WEDNESDAY, 
                      3: Weekday.THURSDAY, 4: Weekday.FRIDAY, 5: Weekday.SATURDAY, 6: Weekday.SUNDAY}
        today_weekday_enum = weekday_map.get(today_weekday, Weekday.MONDAY)
        today_name = today_weekday_enum.to_name()
        
        # 获取当前选择的周次（统一使用数字类型）
        selected_week = int(self.week_var.get()) if hasattr(self, 'week_var') else self.week_range[0]
        
        # 收集今日课程
        today_courses = []
        
        # 检查已选选修课
        for course in self.selected_electives:
            if "schedule_info" in course:
                for schedule in course["schedule_info"]:
                    if schedule["day"] == today_name and schedule["week"] == selected_week:
                        today_courses.append({
                            "name": course["name"],
                            "teacher": course["teacher"],
                            "periods": schedule["periods"],
                            "location": course["location"]
                        })
        
        # 按节次排序
        today_courses.sort(key=lambda x: min(x["periods"]) if x["periods"] else 0)
        
        # 显示结果
        if today_courses:
            details = f"{today_name}（周次{selected_week}）的课程：\n\n"
            for course in today_courses:
                periods_str = ", ".join(map(str, course["periods"]))
                details += f"{course['name']} - {course['teacher']}\n"
                details += f"  节次：{periods_str}\n"
                details += f"  地点：{course['location']}\n\n"
        else:
            details = f"{today_name}（周次{selected_week}）没有课程"
        
        messagebox.showinfo("今日课程", details)
    
    def filter_courses_by_week(self):
        """根据选择的周次过滤课程并更新课表"""
        self.update_elective_list()
        self.update_schedule_display()

    def update_schedule_display(self):
        """更新课表显示"""
        # 清空现有课表
        for item in self.schedule_tree.get_children():
            values = list(self.schedule_tree.item(item)['values'])
            # 清空所有课程内容，保留节次
            for i in range(1, len(values)):
                values[i] = ""
            self.schedule_tree.item(item, values=values)
        
        # 获取当前选择的周次（统一使用数字类型）
        selected_week = int(self.week_var.get()) if hasattr(self, 'week_var') else self.week_range[0]
        
        # 添加已选选修课
        for course in self.selected_electives:
            self.add_course_to_schedule(course, selected_week)
        
        # 强制刷新界面
        self.root.update_idletasks()
    
    def add_course_to_schedule(self, course, selected_week):
        """将课程添加到课表，正确显示节次信息"""
        if "schedule_info" in course and course["schedule_info"]:
            # 处理包含详细时间安排的课程
            for schedule in course["schedule_info"]:
                if selected_week == schedule["week"]:
                    day = schedule["day"]
                    periods = schedule["periods"]
                    
                    # 使用Weekday枚举处理星期，统一类型
                    weekday_enum = Weekday.from_name(day)
                    day_num = weekday_enum.to_column_index()
                    
                    # 添加课程到课表
                    if periods:
                        # 对于连续的节次范围，使用范围显示
                        # 如果是单节次
                        if len(periods) == 1:
                            period = periods[0]
                            if 1 <= period <= 10:  # 确保节次在有效范围内
                                # 找到对应的行（节次）
                                for item in self.schedule_tree.get_children():
                                    values = list(self.schedule_tree.item(item)['values'])
                                    if values[0] == period:  # 第0列是节次
                                        current_content = values[day_num]  # 对应的星期列
                                        if current_content:
                                            # 如果已有内容，添加分隔符和新课程
                                            values[day_num] = f"{current_content} | {course['name']}"
                                        else:
                                            values[day_num] = course['name']
                                        self.schedule_tree.item(item, values=values)
                        else:
                            # 对于多节次课程，确保所有节次都被正确显示
                            for period in periods:
                                if 1 <= period <= 10:  # 确保节次在有效范围内
                                    # 找到对应的行（节次）
                                    for item in self.schedule_tree.get_children():
                                        values = list(self.schedule_tree.item(item)['values'])
                                        if values[0] == period:  # 第0列是节次
                                            current_content = values[day_num]  # 对应的星期列
                                            if current_content:
                                                # 如果已有内容，添加分隔符和新课程
                                                values[day_num] = f"{current_content} | {course['name']}"
                                            else:
                                                values[day_num] = course['name']
                                            self.schedule_tree.item(item, values=values)

if __name__ == "__main__":
    root = tk.Tk()
    app = CourseScheduleApp(root)
    root.mainloop()