#!/usr/bin/env python3
"""
상품 최저가 검색 프로그램
- 네이버 쇼핑 API를 통해 상품 검색
- 묶음 상품의 개별 단가 계산
- 단가순 정렬 및 최대 10개 출력
"""

import os
import re
import sys
import requests
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_SHOPPING_API_URL = "https://openapi.naver.com/v1/search/shop.json"


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
    """
    상품명에서 묶음 수량 추출
    예: "상품A 5개입", "상품B x10", "상품C 3팩" 등
    """
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
        r'(\d+)\s*개(?!\s*월)',  # "개월" 제외
    ]

    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            qty = int(match.group(1))
            if 1 < qty <= 1000:  # 합리적인 범위 내의 수량만 인정
                return qty

    return 1


def parse_delivery_fee(product_data: dict) -> str:
    """배송비 정보 파싱"""
    # API 응답에서 배송비 정보 추출
    # 네이버 쇼핑 API는 배송비를 직접 제공하지 않을 수 있음
    # 대부분의 경우 상품 페이지에서 확인 필요
    return "상품 페이지 확인"


def search_products(query: str, display: int = 100) -> list[Product]:
    """
    네이버 쇼핑 API를 통해 상품 검색
    """
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("오류: NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 설정해주세요.")
        print("1. https://developers.naver.com/apps/#/register?api=search 에서 애플리케이션 등록")
        print("2. .env 파일에 API 키 설정")
        sys.exit(1)

    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }

    params = {
        "query": query,
        "display": display,
        "sort": "sim",  # 정확도순으로 검색 후 가격으로 재정렬
    }

    try:
        response = requests.get(NAVER_SHOPPING_API_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"API 요청 오류: {e}")
        sys.exit(1)

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
            delivery_fee=parse_delivery_fee(item),
            link=item.get("link", ""),
            mall_name=item.get("mallName", "")
        )
        products.append(product)

    # 개별 단가순으로 정렬
    products.sort(key=lambda p: p.unit_price)

    return products[:10]  # 최대 10개 반환


def format_price(price: int) -> str:
    """가격을 천단위 쉼표로 포맷"""
    return f"{price:,}원"


def display_results_rich(products: list[Product], query: str):
    """Rich 라이브러리를 사용한 예쁜 출력"""
    console = Console()

    if not products:
        console.print(f"[yellow]'{query}'에 대한 검색 결과가 없습니다.[/yellow]")
        return

    # 최저가 상품 표시
    best = products[0]
    best_info = f"""
[bold green]🏆 최저가 상품[/bold green]

상품명: {best.title}
개별 단가: [bold cyan]{format_price(best.unit_price)}[/bold cyan]
묶음 수량: {best.quantity}개
총 가격: {format_price(best.price)}
배송비: {best.delivery_fee}
판매처: {best.mall_name}
링크: {best.link}
"""
    console.print(Panel(best_info, title=f"'{query}' 검색 결과", border_style="green"))

    # 전체 리스트 테이블
    table = Table(title="📋 단가순 상품 목록 (최대 10개)")
    table.add_column("순위", style="cyan", justify="center", width=4)
    table.add_column("상품명", style="white", max_width=40, overflow="ellipsis")
    table.add_column("개별 단가", style="green", justify="right")
    table.add_column("묶음", justify="center")
    table.add_column("총 가격", justify="right")
    table.add_column("판매처", style="dim", max_width=15, overflow="ellipsis")

    for i, product in enumerate(products, 1):
        table.add_row(
            str(i),
            product.title[:40],
            format_price(product.unit_price),
            f"{product.quantity}개",
            format_price(product.price),
            product.mall_name
        )

    console.print()
    console.print(table)

    # 링크 목록 출력
    console.print("\n[bold]🔗 판매 링크[/bold]")
    for i, product in enumerate(products, 1):
        console.print(f"  {i}. {product.link}")


def display_results_simple(products: list[Product], query: str):
    """기본 텍스트 출력"""
    if not products:
        print(f"'{query}'에 대한 검색 결과가 없습니다.")
        return

    # 최저가 상품 표시
    best = products[0]
    print("=" * 60)
    print(f"🏆 최저가 상품 - '{query}' 검색 결과")
    print("=" * 60)
    print(f"상품명: {best.title}")
    print(f"개별 단가: {format_price(best.unit_price)}")
    print(f"묶음 수량: {best.quantity}개")
    print(f"총 가격: {format_price(best.price)}")
    print(f"배송비: {best.delivery_fee}")
    print(f"판매처: {best.mall_name}")
    print(f"링크: {best.link}")
    print("=" * 60)

    # 전체 리스트
    print("\n📋 단가순 상품 목록 (최대 10개)")
    print("-" * 60)
    print(f"{'순위':^4} | {'개별단가':^10} | {'묶음':^6} | {'총가격':^12} | 상품명")
    print("-" * 60)

    for i, product in enumerate(products, 1):
        title = product.title[:30] + "..." if len(product.title) > 30 else product.title
        print(f"{i:^4} | {format_price(product.unit_price):>10} | {product.quantity:^4}개 | {format_price(product.price):>12} | {title}")

    print("-" * 60)

    # 링크 목록
    print("\n🔗 판매 링크")
    for i, product in enumerate(products, 1):
        print(f"  {i}. {product.link}")


def display_results(products: list[Product], query: str):
    """검색 결과 출력"""
    if RICH_AVAILABLE:
        display_results_rich(products, query)
    else:
        display_results_simple(products, query)


def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        # stdin이 없는 환경 처리
        if sys.stdin is None or not sys.stdin.isatty():
            print("사용법: python price_finder.py [상품명]")
            print("예시: python price_finder.py 신라면")
            sys.exit(1)
        try:
            query = input("검색할 상품명을 입력하세요: ").strip()
        except (EOFError, RuntimeError):
            print("사용법: python price_finder.py [상품명]")
            print("예시: python price_finder.py 신라면")
            sys.exit(1)

    if not query:
        print("상품명을 입력해주세요.")
        sys.exit(1)

    print(f"\n'{query}' 검색 중...\n")
    products = search_products(query)
    display_results(products, query)


if __name__ == "__main__":
    main()
