import scrapy
from bs4 import BeautifulSoup

class BlogSpider(scrapy.Spider):
    name = 'narutospider'
    start_urls = ['https://naruto.fandom.com/wiki/Special:BrowseData/Jutsu?limit=250&offset=0&_cat=Jutsu']

    # Your screenshot shows the data is inside .smw-columnlist-container
    # Fandom blocks Scrapy by default, so we must set a browser-like User-Agent
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    def parse(self, response):
        # Using the structure from your Inspect screenshot:
        # .drilldown-result-body -> .smw-columnlist-container -> .smw-column -> a
        jutsu_links = response.css('.smw-columnlist-container .smw-column a::attr(href)').getall()

        for href in jutsu_links:
            # Follow links to the specific jutsu page
            yield response.follow(href, callback=self.parse_jutsu)

        # Pagination for the 'next 250' results
        next_page = response.css('a.mw-nextlink::attr(href)').get()
        if next_page:
            yield response.follow(next_page, self.parse)

    def parse_jutsu(self, response):
        # 1. Get the Name (from your firstHeading example)
        jutsu_name = response.css("h1#firstHeading::text").get()
        if not jutsu_name:
            jutsu_name = response.css("span.mw-page-title-main::text").get()

        # 2. Get the HTML of the main output area
        content_div = response.css("div.mw-parser-output").get()
        if not content_div:
            return

        soup = BeautifulSoup(content_div, 'html.parser')

        # 3. Get Classification (from your InfoBox screenshot)
        jutsu_type = "Not Classified"
        aside = soup.find('aside', class_='portable-infobox')
        if aside:
            # Finding the row where label is "Classification"
            for data_row in aside.find_all('div', class_='pi-data'):
                label = data_row.find(['h3', 'div'], class_='pi-data-label')
                if label and "Classification" in label.get_text():
                    value = data_row.find('div', class_='pi-data-value')
                    if value:
                        jutsu_type = value.get_text(strip=True)
            
            # Decompose aside so it doesn't clutter the description
            aside.decompose()

        # 4. Get Description (Cleaning up the HTML)
        # Remove unwanted items like scripts, navigation, and tables
        for tag in soup(['script', 'style', 'figure', 'table', 'div']):
            # Keep the main text containers, delete everything else
            if tag.get('class') and 'portable-infobox' in tag.get('class'):
                continue
            tag.decompose()

        # Extract cleaned text
        full_text = soup.get_text(separator=' ', strip=True)
        
        # Clean description by stopping at Trivia or References
        jutsu_description = full_text.split('Trivia')[0].split('References')[0].strip()

        yield {
            'jutsu_name': jutsu_name.strip() if jutsu_name else "N/A",
            'jutsu_type': jutsu_type,
            'jutsu_description': jutsu_description
        }