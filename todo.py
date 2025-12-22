import sys
import json
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QMenu, QInputDialog, QSystemTrayIcon, QStyle
)
from PyQt6.QtGui import QColor, QPainter, QBrush, QCursor
from PyQt6.QtCore import Qt, QObject, QEvent, QPoint

DATA_FILE = "todos.json"

class BlankAreaFilter(QObject):
    """事件过滤器，用于捕获窗口空白区域右键"""
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                # 如果点击的是列表，则不触发
                if obj.rect().contains(event.position().toPoint()):
                    self.callback(event.globalPosition().toPoint())
                    return True
        return False

class TodoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(300, 400)

        self.todos = self.load()
        self.collapsed = False

        # ---------- 布局 ----------
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(0)

        # ---------- 代办列表 ----------
        self.list = QListWidget()
        self.list.setStyleSheet("""
            QListWidget {
                background: rgba(255,255,255,220);
                border-radius: 12px;
                padding: 6px;
                font-size: 13px;
            }
        """)
        self.layout.addWidget(self.list)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.item_menu)
        self.refresh()

        # ---------- 事件过滤器 ----------
        self.installEventFilter(BlankAreaFilter(self, self.blank_area_menu))

        # ---------- 系统托盘 ----------
        self.tray = QSystemTrayIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView), self)
        tray_menu = QMenu()
        tray_menu.addAction("➕ 添加代办", self.add)
        tray_menu.addSeparator()
        tray_menu.addAction("🖋 修改宽高", self.change_size)
        tray_menu.addAction("✖ 退出", self.exit)
        self.tray.setContextMenu(tray_menu)
        self.tray.show()
        self.tray.activated.connect(lambda r: self.show() if r == QSystemTrayIcon.ActivationReason.Trigger else None)

        self.show()

    # ---------- 数据 ----------
    def load(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.todos, f, ensure_ascii=False, indent=2)

    def refresh(self):
        self.list.clear()
        for t in self.todos:
            item = QListWidgetItem(("✔ " if t["done"] else "○ ") + t["text"])
            # 设置字体颜色
            if t["done"]:
                item.setForeground(QColor("#777777"))  # 已完成灰色
            else:
                item.setForeground(QColor("#000000"))  # 未完成黑色
            self.list.addItem(item)

    # ---------- 拖动 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = e.globalPosition().toPoint()

    # ---------- 双击折叠 ----------
    def mouseDoubleClickEvent(self, e):
        self.list.setVisible(self.collapsed)
        self.collapsed = not self.collapsed

    # ---------- 空白区域右键菜单 ----------
    def blank_area_menu(self, pos: QPoint):
        menu = QMenu()
        menu.addAction("➕ 添加代办", self.add)
        menu.addSeparator()
        menu.addAction("🖋 修改宽高", self.change_size)
        menu.addAction("✖ 退出", self.exit)
        menu.exec(pos)

    # ---------- 代办右键 ----------
    def item_menu(self, pos):
        idx = self.list.currentRow()
        if idx < 0:
            return
        menu = QMenu()
        menu.addAction("✔ 完成 / 取消", lambda: self.toggle(idx))
        menu.addAction("✏ 修改", lambda: self.edit(idx))
        menu.addAction("🗑 删除", lambda: self.delete(idx))
        menu.exec(self.list.mapToGlobal(pos))

    # ---------- 代办操作 ----------
    def add(self):
        text, ok = QInputDialog.getText(self, "添加代办", "内容：")
        if ok and text:
            self.todos.append({"text": text, "done": False})
            self.refresh()

    def edit(self, i):
        text, ok = QInputDialog.getText(self, "修改代办", "内容：", text=self.todos[i]["text"])
        if ok:
            self.todos[i]["text"] = text
            self.refresh()

    def delete(self, i):
        self.todos.pop(i)
        self.refresh()

    def toggle(self, i):
        self.todos[i]["done"] ^= True
        self.refresh()

    # ---------- 托盘操作 ----------
    def toggle_show(self):
        self.setVisible(not self.isVisible())

    def exit(self):
        self.save()
        QApplication.quit()

    # ---------- 修改窗口宽高 ----------
    def change_size(self):
        w, ok1 = QInputDialog.getInt(self, "修改宽度", "输入宽度:", value=self.width(), min=200, max=800)
        if not ok1: return
        h, ok2 = QInputDialog.getInt(self, "修改高度", "输入高度:", value=self.height(), min=200, max=800)
        if not ok2: return
        self.resize(w, h)

    # ---------- 圆角半透明背景 ----------
    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(255, 255, 255, 180)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = TodoWidget()
    sys.exit(app.exec())
