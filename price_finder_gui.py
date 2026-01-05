#!/usr/bin/env python3
"""
상품 최저가 검색 프로그램 (GUI 버전)
- 네이버 쇼핑 API를 통해 상품 검색
- 묶음 상품의 개별 단가 계산
- 단가순 정렬 및 최대 10개 출력
"""

import os
import re
import sys
import json
import webbrowser
import threading
import requests
from pathlib import Path
from dataclasses import dataclass

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# 설정 파일 경로 (exe와 같은 폴더 또는 사용자 홈)
def get_config_path():
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 exe인 경우
        return Path(sys.executable).parent / "config.json"
    else:
        return Path(__file__).parent / "config.json"

CONFIG_PATH = get_config_path()
NAVER_SHOPPING_API_URL = "https://openapi.naver.com/v1/search/shop.json"


def load_config():
    """설정 파일 로드"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"client_id": "", "client_secret": ""}


def save_config(client_id: str, client_secret: str):
    """설정 파일 저장"""
    config = {"client_id": client_id, "client_secret": client_secret}
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f)


@dataclass
class Product:
    """상품 정보를 담는 데이터 클래스"""
    title: str
    price: int
    unit_price: int
    quantity: int
    delivery_fee: str
    link: str
    mall_name: str


def clean_html(text: str) -> str:
    """HTML 태그 제거"""
    return re.sub(r'<[^>]+>', '', text)


def extract_quantity(title: str) -> int:
    """상품명에서 묶음 수량 추출"""
    patterns = [
        r'(\d+)\s*개입',
        r'(\d+)\s*개\s*묶음',
        r'(\d+)\s*개\s*세트',
        r'(\d+)\s*팩',
        r'(\d+)\s*박스',
        r'(\d+)\s*봉',
        r'(\d+)\s*병',
        r'(\d+)\s*캔',
        r'(\d+)\s*통',
        r'(\d+)\s*포',
        r'(\d+)\s*매입',
        r'(\d+)\s*매',
        r'[xX×]\s*(\d+)',
        r'(\d+)\s*[eE][aA]',
        r'(\d+)\s*입',
        r'(\d+)\s*P\b',
        r'(\d+)\s*p\b',
        r'(\d+)\s*개(?!\s*월)',
    ]

    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            qty = int(match.group(1))
            if 1 < qty <= 1000:
                return qty
    return 1


def search_products(query: str, client_id: str, client_secret: str, display: int = 100) -> list[Product]:
    """네이버 쇼핑 API를 통해 상품 검색"""
    if not client_id or not client_secret:
        raise ValueError("API 키가 설정되지 않았습니다.")

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    params = {
        "query": query,
        "display": display,
        "sort": "sim",
    }

    response = requests.get(NAVER_SHOPPING_API_URL, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    products = []
    for item in data.get("items", []):
        title = clean_html(item.get("title", ""))
        price = int(item.get("lprice", 0))

        if price <= 0:
            continue

        quantity = extract_quantity(title)
        unit_price = price // quantity

        product = Product(
            title=title,
            price=price,
            unit_price=unit_price,
            quantity=quantity,
            delivery_fee="상품 페이지 확인",
            link=item.get("link", ""),
            mall_name=item.get("mallName", "")
        )
        products.append(product)

    products.sort(key=lambda p: p.unit_price)
    return products[:10]


def format_price(price: int) -> str:
    """가격을 천단위 쉼표로 포맷"""
    return f"{price:,}원"


class SettingsDialog(tk.Toplevel):
    """API 키 설정 다이얼로그"""
    def __init__(self, parent, client_id="", client_secret=""):
        super().__init__(parent)
        self.title("API Key Settings")
        self.geometry("550x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result = None

        # 안내 문구
        info_frame = ttk.Frame(self, padding="15")
        info_frame.pack(fill=tk.X)

        info_text = (
            "네이버 개발자 센터에서 API 키를 발급받으세요:\n"
            "https://developers.naver.com/apps/#/register?api=search\n\n"
            "1. 네이버 로그인 후 '애플리케이션 등록'\n"
            "2. '검색' API 선택\n"
            "3. Client ID와 Client Secret 복사"
        )
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)

        # 링크 버튼
        link_btn = ttk.Button(info_frame, text="🔗 네이버 개발자 센터 열기",
                              command=lambda: webbrowser.open("https://developers.naver.com/apps/#/register?api=search"))
        link_btn.pack(pady=5)

        # 입력 필드
        input_frame = ttk.Frame(self, padding="15")
        input_frame.pack(fill=tk.X)

        ttk.Label(input_frame, text="Client ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.id_var = tk.StringVar(value=client_id)
        self.id_entry = ttk.Entry(input_frame, textvariable=self.id_var, width=50)
        self.id_entry.grid(row=0, column=1, pady=5, padx=(10, 0))

        ttk.Label(input_frame, text="Client Secret:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.secret_var = tk.StringVar(value=client_secret)
        self.secret_entry = ttk.Entry(input_frame, textvariable=self.secret_var, width=50, show="*")
        self.secret_entry.grid(row=1, column=1, pady=5, padx=(10, 0))

        # 버튼
        btn_frame = ttk.Frame(self, padding="15")
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        save_btn = ttk.Button(btn_frame, text="Save", command=self.save)
        save_btn.pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)

        self.id_entry.focus()

    def save(self):
        client_id = self.id_var.get().strip()
        client_secret = self.secret_var.get().strip()

        if not client_id or not client_secret:
            messagebox.showwarning("알림", "Client ID와 Client Secret을 모두 입력해주세요.")
            return

        self.result = (client_id, client_secret)
        self.destroy()


class PriceFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🛒 상품 최저가 검색기 - MADE BY YEHA")
        self.root.geometry("900x650")
        self.root.minsize(800, 500)

        self.products = []
        self.config = load_config()

        self.setup_ui()

        # API 키가 없으면 설정 창 표시
        if not self.config.get("client_id") or not self.config.get("client_secret"):
            self.root.after(100, self.show_settings)

    def setup_ui(self):
        # 메뉴바
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="설정", menu=settings_menu)
        settings_menu.add_command(label="⚙️ API 키 설정", command=self.show_settings)

        # 상단 검색 영역
        search_frame = ttk.Frame(self.root, padding="10")
        search_frame.pack(fill=tk.X)

        ttk.Label(search_frame, text="상품명:", font=('Arial', 11)).pack(side=tk.LEFT, padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=('Arial', 12), width=40)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        self.search_entry.bind('<Return>', lambda e: self.search())

        self.search_btn = ttk.Button(search_frame, text="🔍 검색", command=self.search)
        self.search_btn.pack(side=tk.LEFT)

        ttk.Button(search_frame, text="⚙️", width=3, command=self.show_settings).pack(side=tk.LEFT, padx=(5, 0))

        # 최저가 표시 영역
        best_frame = ttk.LabelFrame(self.root, text="🏆 최저가 상품", padding="10")
        best_frame.pack(fill=tk.X, padx=10, pady=5)

        self.best_label = ttk.Label(best_frame, text="검색 결과가 여기에 표시됩니다.", font=('Arial', 10), wraplength=850)
        self.best_label.pack(fill=tk.X)

        self.best_link_btn = ttk.Button(best_frame, text="🔗 상품 페이지 열기", command=self.open_best_link, state=tk.DISABLED)
        self.best_link_btn.pack(pady=(10, 0))

        # 결과 목록 영역
        list_frame = ttk.LabelFrame(self.root, text="📋 단가순 상품 목록 (최대 10개)", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview 설정
        columns = ("rank", "title", "unit_price", "qty", "total_price", "mall")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)

        self.tree.heading("rank", text="순위")
        self.tree.heading("title", text="상품명")
        self.tree.heading("unit_price", text="개별 단가")
        self.tree.heading("qty", text="묶음")
        self.tree.heading("total_price", text="총 가격")
        self.tree.heading("mall", text="판매처")

        self.tree.column("rank", width=50, anchor=tk.CENTER)
        self.tree.column("title", width=350)
        self.tree.column("unit_price", width=100, anchor=tk.E)
        self.tree.column("qty", width=60, anchor=tk.CENTER)
        self.tree.column("total_price", width=100, anchor=tk.E)
        self.tree.column("mall", width=120)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<Double-1>', self.on_item_double_click)

        # 상태 표시줄
        self.status_var = tk.StringVar(value="상품명을 입력하고 검색 버튼을 누르세요. (⚙️ 버튼으로 API 키 설정)")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)

        # 검색창에 포커스
        self.search_entry.focus()

    def show_settings(self):
        dialog = SettingsDialog(
            self.root,
            self.config.get("client_id", ""),
            self.config.get("client_secret", "")
        )
        self.root.wait_window(dialog)

        if dialog.result:
            client_id, client_secret = dialog.result
            save_config(client_id, client_secret)
            self.config = {"client_id": client_id, "client_secret": client_secret}
            messagebox.showinfo("완료", "API 키가 저장되었습니다!")
            self.status_var.set("API 키 설정 완료! 상품명을 입력하고 검색하세요.")

    def search(self):
        if not self.config.get("client_id") or not self.config.get("client_secret"):
            messagebox.showwarning("알림", "먼저 API 키를 설정해주세요.")
            self.show_settings()
            return

        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("알림", "상품명을 입력해주세요.")
            return

        self.search_btn.config(state=tk.DISABLED)
        self.status_var.set(f"'{query}' 검색 중...")
        self.root.update()

        thread = threading.Thread(target=self._do_search, args=(query,))
        thread.daemon = True
        thread.start()

    def _do_search(self, query):
        try:
            products = search_products(
                query,
                self.config["client_id"],
                self.config["client_secret"]
            )
            self.root.after(0, lambda: self._update_results(products, query))
        except requests.exceptions.RequestException as e:
            self.root.after(0, lambda: self._show_error(f"네트워크 오류: {e}"))
        except Exception as e:
            self.root.after(0, lambda: self._show_error(f"오류 발생: {e}"))

    def _update_results(self, products, query):
        self.products = products
        self.search_btn.config(state=tk.NORMAL)

        for item in self.tree.get_children():
            self.tree.delete(item)

        if not products:
            self.best_label.config(text="검색 결과가 없습니다.")
            self.best_link_btn.config(state=tk.DISABLED)
            self.status_var.set(f"'{query}' 검색 결과 없음")
            return

        best = products[0]
        best_text = (
            f"상품명: {best.title}\n"
            f"개별 단가: {format_price(best.unit_price)}  |  "
            f"묶음: {best.quantity}개  |  "
            f"총 가격: {format_price(best.price)}  |  "
            f"판매처: {best.mall_name}"
        )
        self.best_label.config(text=best_text)
        self.best_link_btn.config(state=tk.NORMAL)

        for i, product in enumerate(products, 1):
            self.tree.insert("", tk.END, values=(
                i,
                product.title[:50] + "..." if len(product.title) > 50 else product.title,
                format_price(product.unit_price),
                f"{product.quantity}개",
                format_price(product.price),
                product.mall_name
            ))

        self.status_var.set(f"'{query}' 검색 완료 - {len(products)}개 상품 (더블클릭으로 링크 열기)")

    def _show_error(self, message):
        self.search_btn.config(state=tk.NORMAL)
        self.status_var.set("오류 발생")
        messagebox.showerror("오류", message)

    def open_best_link(self):
        if self.products:
            webbrowser.open(self.products[0].link)

    def on_item_double_click(self, event):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            rank = int(item['values'][0]) - 1
            if 0 <= rank < len(self.products):
                webbrowser.open(self.products[rank].link)


def main():
    root = tk.Tk()

    style = ttk.Style()
    style.configure('TButton', padding=5)
    style.configure('TEntry', padding=5)

    app = PriceFinderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
