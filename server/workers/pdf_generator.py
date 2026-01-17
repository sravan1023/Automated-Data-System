"""
AutoDocs AI - PDF Generator

Converts HTML to PDF using Playwright.
"""
from playwright.sync_api import sync_playwright
from typing import Optional


def generate_pdf(
    html_content: str,
    format: str = "A4",
    landscape: bool = False,
    margin: Optional[dict] = None,
    print_background: bool = True,
) -> bytes:
    """
    Generate PDF from HTML content using Playwright.
    
    Args:
        html_content: Full HTML document string
        format: Paper format (A4, Letter, etc.)
        landscape: Landscape orientation
        margin: Page margins {top, right, bottom, left}
        print_background: Include background colors/images
    
    Returns:
        PDF file bytes
    """
    if margin is None:
        margin = {
            "top": "1cm",
            "right": "1cm",
            "bottom": "1cm",
            "left": "1cm",
        }
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        
        try:
            # Create page
            page = browser.new_page()
            
            # Set content
            page.set_content(
                html_content,
                wait_until="networkidle",
            )
            
            # Generate PDF
            pdf_bytes = page.pdf(
                format=format,
                landscape=landscape,
                margin=margin,
                print_background=print_background,
                prefer_css_page_size=True,
            )
            
            return pdf_bytes
        
        finally:
            browser.close()


def generate_pdf_from_url(
    url: str,
    format: str = "A4",
    wait_for_selector: Optional[str] = None,
) -> bytes:
    """
    Generate PDF from URL.
    
    Useful for rendering hosted content or complex pages.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            
            if wait_for_selector:
                page.wait_for_selector(wait_for_selector)
            
            pdf_bytes = page.pdf(
                format=format,
                print_background=True,
            )
            
            return pdf_bytes
        
        finally:
            browser.close()


def html_to_png(
    html_content: str,
    width: int = 1200,
    height: Optional[int] = None,
) -> bytes:
    """
    Generate PNG screenshot from HTML.
    
    Useful for template previews.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        try:
            page = browser.new_page()
            page.set_viewport_size({"width": width, "height": 800})
            page.set_content(html_content, wait_until="networkidle")
            
            screenshot_options = {
                "type": "png",
                "full_page": True if height is None else False,
            }
            
            if height:
                screenshot_options["clip"] = {
                    "x": 0,
                    "y": 0,
                    "width": width,
                    "height": height,
                }
            
            png_bytes = page.screenshot(**screenshot_options)
            
            return png_bytes
        
        finally:
            browser.close()
