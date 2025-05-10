"""
Simple Stock Data Scraper using SeleniumBase

This script demonstrates how to scrape stock data from Yahoo Finance
using SeleniumBase in a simple and reliable way.

Usage:
    python simple_stock_scraper.py --symbol AAPL
"""

import argparse
import json
import logging
import os
import time
from datetime import datetime

from seleniumbase import Driver

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SimpleStockScraper:
    """A simple class for scraping stock data using SeleniumBase."""

    def __init__(self, headless=True):
        """
        Initialize the stock scraper.

        Args:
            headless (bool): Whether to run the browser in headless mode
        """
        self.driver = None
        self.headless = headless

        # Directory for saving results
        self.results_dir = "stock_results"
        os.makedirs(self.results_dir, exist_ok=True)

    def _init_selenium(self):
        """Initialize SeleniumBase Driver."""
        if self.driver is None:
            logger.info("Initializing SeleniumBase Driver")
            self.driver = Driver(headless=self.headless)

    def close(self):
        """Close the SeleniumBase Driver if it's open."""
        if self.driver:
            logger.info("Closing SeleniumBase Driver")
            self.driver.quit()
            self.driver = None

    def _save_result(self, result, filename):
        """Save result to a JSON file."""
        filepath = os.path.join(self.results_dir, filename)
        with open(filepath, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Result saved to {filepath}")

    def get_yahoo_finance_data(self, symbol):
        """
        Scrape Yahoo Finance data using SeleniumBase.

        Args:
            symbol (str): The stock symbol to look up

        Returns:
            dict: Stock data or None if an error occurred
        """
        self._init_selenium()

        url = f"https://finance.yahoo.com/quote/{symbol}"
        logger.info(f"Scraping Yahoo Finance data for {symbol}")

        try:
            # Navigate to the page
            logger.info(f"Navigating to {url}")
            self.driver.get(url)

            # Add delay to allow page to load
            time.sleep(3)

            # Extract data
            logger.info("Extracting stock data")

            # Print page title to debug
            page_title = self.driver.title
            logger.info(f"Page title: {page_title}")

            # Check if we're on a consent page
            if "consent" in page_title.lower():
                logger.info("Detected consent page, trying to accept")
                try:
                    # Try to click the consent button
                    self.driver.execute_script("""
                        var buttons = document.querySelectorAll("button");
                        for (var i = 0; i < buttons.length; i++) {
                            if (buttons[i].textContent.includes("Accept") ||
                                buttons[i].textContent.includes("Agree") ||
                                buttons[i].textContent.includes("Consent")) {
                                buttons[i].click();
                                return true;
                            }
                        }
                        return false;
                    """)
                    # Wait for page to load after consent
                    time.sleep(3)
                except Exception as e:
                    logger.warning(f"Error handling consent page: {e}")

            # Use JavaScript to extract data (more reliable than CSS selectors)
            # First, print the HTML to see what we're working with
            html = self.driver.page_source
            logger.info(f"Page HTML length: {len(html)}")

            # Try a more general approach to find the price
            price = self.driver.execute_script("""
                // Try multiple selectors for price
                var selectors = [
                    "[data-test='quote-header-info'] fin-streamer[data-field='regularMarketPrice']",
                    ".quote-header-section span[data-reactid='32']",
                    ".Fw\\\\(b\\\\).Fz\\\\(36px\\\\)",
                    "fin-streamer[data-symbol='AAPL'][data-field='regularMarketPrice']"
                ];

                for (var i = 0; i < selectors.length; i++) {
                    var elements = document.querySelectorAll(selectors[i]);
                    if (elements.length > 0) {
                        return elements[0].textContent;
                    }
                }

                // If all else fails, look for any element that might contain the price
                var allElements = document.querySelectorAll("*");
                for (var i = 0; i < allElements.length; i++) {
                    var text = allElements[i].textContent;
                    if (/^\\$\\d+\\.\\d+$/.test(text)) {
                        return text;
                    }
                }

                return "N/A";
            """)

            change = self.driver.execute_script("""
                // Try multiple selectors for change
                var selectors = [
                    "[data-test='quote-header-info'] fin-streamer[data-field='regularMarketChange']",
                    ".quote-header-section span[data-reactid='33']"
                ];

                for (var i = 0; i < selectors.length; i++) {
                    var elements = document.querySelectorAll(selectors[i]);
                    if (elements.length > 0) {
                        return elements[0].textContent;
                    }
                }

                return "N/A";
            """)

            percent = self.driver.execute_script("""
                // Try multiple selectors for percent change
                var selectors = [
                    "[data-test='quote-header-info'] fin-streamer[data-field='regularMarketChangePercent']",
                    ".quote-header-section span[data-reactid='34']"
                ];

                for (var i = 0; i < selectors.length; i++) {
                    var elements = document.querySelectorAll(selectors[i]);
                    if (elements.length > 0) {
                        return elements[0].textContent;
                    }
                }

                return "N/A";
            """)

            # Additional data
            prev_close = open_price = volume = "N/A"
            try:
                prev_close = self.driver.execute_script("""
                    var elements = document.querySelectorAll("td[data-test='PREV_CLOSE-value']");
                    return elements.length > 0 ? elements[0].textContent : "N/A";
                """)

                open_price = self.driver.execute_script("""
                    var elements = document.querySelectorAll("td[data-test='OPEN-value']");
                    return elements.length > 0 ? elements[0].textContent : "N/A";
                """)

                volume = self.driver.execute_script("""
                    var elements = document.querySelectorAll("td[data-test='TD_VOLUME-value']");
                    return elements.length > 0 ? elements[0].textContent : "N/A";
                """)
            except Exception as e:
                logger.warning(f"Could not extract all additional data: {e}")

            # Take a screenshot
            screenshot_path = os.path.join(self.results_dir, f"{symbol}_screenshot.png")
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")

            # Create result dictionary
            result = {
                "symbol": symbol,
                "price": price,
                "change": change,
                "percent_change": percent,
                "previous_close": prev_close,
                "open": open_price,
                "volume": volume,
                "source": "Yahoo Finance",
                "timestamp": datetime.now().isoformat(),
            }

            # Save result to file
            self._save_result(result, f"{symbol}_yahoo.json")

            return result
        except Exception as e:
            logger.error(f"Error scraping Yahoo Finance: {e}")
            return None


def print_stock_data(data):
    """Print stock data in a formatted way."""
    if not data:
        print("No data available")
        return

    print("\n=== Stock Data ===")
    print(f"Symbol: {data.get('symbol', 'N/A')}")
    print(f"Price: {data.get('price', 'N/A')}")
    print(f"Change: {data.get('change', 'N/A')}")
    print(f"Percent Change: {data.get('percent_change', 'N/A')}")
    print(f"Previous Close: {data.get('previous_close', 'N/A')}")
    print(f"Open: {data.get('open', 'N/A')}")
    print(f"Volume: {data.get('volume', 'N/A')}")
    print(f"Source: {data.get('source', 'N/A')}")
    print(f"Timestamp: {data.get('timestamp', 'N/A')}")


def main():
    """Main function to demonstrate the stock scraper."""
    parser = argparse.ArgumentParser(description="Simple Stock Data Scraper")
    parser.add_argument(
        "--symbol", type=str, default="AAPL", help="Stock symbol to scrape"
    )
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")

    args = parser.parse_args()

    print(f"Starting stock data scraper for symbol: {args.symbol}")
    print(f"Headless mode: {args.headless}")

    # Get scraper instance
    scraper = SimpleStockScraper(headless=args.headless)

    try:
        # Get Yahoo Finance data
        yahoo_data = scraper.get_yahoo_finance_data(args.symbol)
        print_stock_data(yahoo_data)

        print("\nScraping completed successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Always close the scraper to clean up resources
        scraper.close()


if __name__ == "__main__":
    main()
